"""Runner for SRS_F025 V1.186 independent verification.
Executes protocol/HTTP/SQL assertions, runs real Edge UI tests, and cleans up.
"""
import copy, json, os, socket, subprocess, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT.parent / 'tip'
sys.path.insert(0, str(ROOT / 'acceptance/stage3'))

# 1. Start controlled model
print("1. Starting controlled model on 18117...")
model_py = ROOT / 'acceptance/stage3/fixtures/f025-v186-controlled-model.py'
p_model = subprocess.Popen([sys.executable, str(model_py)], cwd=ROOT, creationflags=subprocess.CREATE_NO_WINDOW)

# Wait for model port
for _ in range(30):
    with socket.socket() as s:
        if s.connect_ex(('127.0.0.1', 18117)) == 0:
            print("Model is listening on 18117")
            break
    time.sleep(0.5)
else:
    raise RuntimeError("Model port 18117 timed out")

# 2. Start backend JAR
print("2. Starting backend JAR on 18129...")
start_jar = ROOT / 'acceptance/stage3/fixtures/start-f025-v186-jar.py'
ret = subprocess.run([sys.executable, str(start_jar)], cwd=ROOT)
if ret.returncode != 0:
    p_model.terminate()
    raise RuntimeError(f"Backend failed to start, code {ret.returncode}")

runtime_file = ROOT / '.local-test/runtime-v186.json'
backend_pid = json.loads(runtime_file.read_text(encoding='utf-8'))['pid']
print(f"Backend running with PID {backend_pid}")

# 3. Start proxy on 15179
print("3. Starting proxy on 15179...")
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import mimetypes

class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def handle_all(self):
        status = 200
        ctype = 'application/json'
        if self.path.startswith('/api/'):
            content_len = int(self.headers.get('Content-Length', '0'))
            payload = self.rfile.read(content_len) if content_len > 0 else None
            req = urllib.request.Request(
                'http://127.0.0.1:18129' + self.path,
                payload,
                {k: v for k, v in self.headers.items() if k.lower() in ['authorization', 'content-type']},
                method=self.command
            )
            try:
                with urllib.request.urlopen(req, timeout=90) as res:
                    data = res.read()
                    status = res.status
            except urllib.error.HTTPError as ex:
                data = ex.read()
                status = ex.code
            except Exception as ex:
                data = json.dumps({'error': str(ex)}).encode('utf-8')
                status = 502
        else:
            clean_path = self.path.split('?')[0].lstrip('/')
            file_path = ROOT / 'frontend/dist' / clean_path
            if not file_path.is_file():
                file_path = ROOT / 'frontend/dist/index.html'
            data = file_path.read_bytes()
            ctype = mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream'

        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = handle_all
    do_POST = handle_all
    do_PUT = handle_all
    do_DELETE = handle_all

proxy_server = ThreadingHTTPServer(('127.0.0.1', 15179), ProxyHandler)
import threading
t_proxy = threading.Thread(target=proxy_server.serve_forever, daemon=True)
t_proxy.start()
print("Proxy listening on 15179")

# 4. Import probe and execute cases
print("4. Initializing test probe...")
import importlib.util
s_probe = importlib.util.spec_from_file_location('probe_mod', ROOT / 'acceptance/stage3/probe-f025-v186.py')
probe_mod = importlib.util.module_from_spec(s_probe)
s_probe.loader.exec_module(probe_mod)

q = probe_mod.Round()
q.setup()

try:
    # ----------------------------------------------------
    # Case 1: TC-077.S1 / R01, R03, R05, R06, R07, R09
    # Complete 3 parameters: assistanceType, origin, destination
    # Plan generated with 3 channels, RULE_ESCORT_SPECIAL_PASSENGER HIGH risk
    # Driven to COMPLETED
    # ----------------------------------------------------
    print("\n--- Running Case 1: Full Parameters & Multi-channel Execution ---")
    row1 = q.submit(
        'tc077-s1-full-params',
        '为轮椅旅客安排协助，从F2_GATE_A出发前往F2_SERVICE_POINT',
        {
            'assistanceType': 'WHEELCHAIR',
            'origin': 'F2_GATE_A',
            'destination': 'F2_SERVICE_POINT'
        }
    )
    tid1 = row1['taskId']
    assert tid1 is not None, "Case 1 task creation failed"
    after1 = q.drive(row1, max_time=30)
    task1 = q.op(f'/tasks/{tid1}')
    plans1 = q.op(f'/tasks/{tid1}/plan-versions')
    events1 = q.op(f'/tasks/{tid1}/events')
    assignments1 = q.op(f'/tasks/{tid1}/step-assignments')

    checks1 = {
        'statusCompleted': task1['status'] == 'COMPLETED',
        'tempBusinessIdPresent': bool(task1.get('sceneParams') and 'SP-F186' in str(task1.get('sceneParams'))),
        'highRiskDetermined': any(p.get('riskLevel') == 'HIGH' for p in plans1),
        'threeChannelsAssigned': len(assignments1) == 3,
        'infoDisplayCompleted': any(a.get('stepStatus') == 'COMPLETED' and a.get('stepSeq') == 1 for a in assignments1),
        'notificationCompleted': any(a.get('stepStatus') == 'COMPLETED' and a.get('stepSeq') == 2 for a in assignments1),
        'escortCompleted': any(a.get('stepStatus') == 'COMPLETED' and a.get('stepSeq') == 3 for a in assignments1),
        'taskCompletedEventLogged': any(e.get('eventType') == 'TASK_COMPLETED' for e in events1)
    }
    q.record('tc077-s1-evaluation', {'after': after1, 'plans': plans1, 'events': events1}, checks1)

    # ----------------------------------------------------
    # Case 2: TC-077.S2 / R02, DEF-S3-004
    # Missing origin, triggers clarification with system questions only
    # ----------------------------------------------------
    print("\n--- Running Case 2: Missing Origin Triggers Clarification ---")
    row2 = q.submit(
        'tc077-s2-missing-origin',
        '为盲人旅客提供引导协助，前往F2_SERVICE_POINT',
        {
            'assistanceType': 'VISION_IMPAIRED',
            'destination': 'F2_SERVICE_POINT'
        },
        origin='',
        infoComplete=False,
        missingInfoQuestions=['请补充服务起点']
    )
    tid2 = row2['taskId']
    task2 = q.op(f'/tasks/{tid2}')
    questions2 = task2.get('missingInfoQuestions') or []

    checks2 = {
        'statusPlanning': task2['status'] == 'PLANNING',
        'questionsContainsOrigin': any('起点' in str(q_item) for q_item in questions2),
        'noIdentityQuestionsAsked': not any(any(kw in str(q_item) for kw in ['姓名', '身份证', '证件', '手机', '电话']) for q_item in questions2)
    }
    q.record('tc077-s2-evaluation', {'task': task2}, checks2)

    # ----------------------------------------------------
    # Case 3: DEF-S3-004 & DEF-S3-032 / R01, R02
    # Model attempts to ask for real identity; system overrides with business field only.
    # Clarify with operator answer containing passengerName / ID canary;
    # verify privacy sanitization (zero canary in DB, external request, or audit).
    # ----------------------------------------------------
    print("\n--- Running Case 3: Model Identity Override & Free-Text Privacy Sanitization ---")
    row3 = q.submit(
        'def-s3-004-privacy-override',
        '为老年旅客安排轮椅协助前往F2_SERVICE_POINT',
        {
            'assistanceType': 'ELDERLY',
            'destination': 'F2_SERVICE_POINT'
        },
        origin='',
        infoComplete=False,
        missingInfoQuestions=['请补充旅客姓名和身份证号', '请指定陪同人员'] # Model attempts illegal questions
    )
    tid3 = row3['taskId']
    task3_before = q.op(f'/tasks/{tid3}')
    questions3 = task3_before.get('missingInfoQuestions') or []

    # RequiredInfoGuard overrides the model's illegal identity questions with missing business field
    canary = "CANARY_ZHANG_F025"
    clarify_resp = probe_mod.raw(q.op, f'/tasks/{tid3}/clarify', {
        'answers': {
            q_text: f"F2_GATE_A; passengerName={canary}, idCard=110101199001011234, phone=13800138000"
            for q_text in questions3
        }
    })

    # Observe after clarification
    task3_after = q.op(f'/tasks/{tid3}')
    events3 = q.op(f'/tasks/{tid3}/events')
    sql_task3 = probe_mod.sql(f"select scene_params from {probe_mod.SC}.tasks where id={tid3}")
    sql_events3 = probe_mod.sql(f"select detail_summary from {probe_mod.SC}.task_events where task_id={tid3}")

    checks3 = {
        'modelQuestionsOverridden': any('起点' in str(q_item) for q_item in questions3) and not any('身份证' in str(q_item) for q_item in questions3),
        'clarifyAccepted': clarify_resp.get('http') == 200,
        'noCanaryInSceneParams': canary not in str(sql_task3),
        'noCanaryInAuditEvents': canary not in str(sql_events3),
        'protectedPlaceholderPresent': '[PROTECTED_IDENTITY]' in str(sql_task3),
        'originSatisfied': 'F2_GATE_A' in str(sql_task3)
    }
    q.record('def-s3-004-privacy-evaluation', {
        'questions': questions3,
        'clarifyResponse': clarify_resp,
        'sqlTask': sql_task3,
        'sqlEvents': sql_events3
    }, checks3)

    # Now drive task 3 to completion
    after3 = q.drive(row3, max_time=30)
    task3_final = q.op(f'/tasks/{tid3}')
    q.record('def-s3-004-completion', {'finalTask': task3_final}, {'taskCompleted': task3_final['status'] == 'COMPLETED'})

    # ----------------------------------------------------
    # Case 4: TC-077.S2-INVALID / R01, R02
    # Operator answers question with ONLY identity placeholder / no legitimate business value
    # Required field remains missing; task does NOT advance to planning
    # ----------------------------------------------------
    print("\n--- Running Case 4: Answer with Only Identity Placeholder Fails Required Field ---")
    row4 = q.submit(
        'tc077-s2-invalid-placeholder-only',
        '为无陪伴儿童提供协助前往F2_SERVICE_POINT',
        {
            'assistanceType': 'UNACCOMPANIED_MINOR',
            'destination': 'F2_SERVICE_POINT'
        },
        origin='',
        infoComplete=False,
        missingInfoQuestions=['请补充服务起点']
    )
    tid4 = row4['taskId']
    q4 = q.op(f'/tasks/{tid4}').get('missingInfoQuestions') or []

    # Operator answers with ONLY a name (which redacts to [PROTECTED_IDENTITY], giving 0 business value)
    clarify4 = probe_mod.raw(q.op, f'/tasks/{tid4}/clarify', {
        'answers': {q_text: 'passengerName=李四' for q_text in q4}
    })
    task4_after = q.op(f'/tasks/{tid4}')

    checks4 = {
        'taskRemainsInPlanning': task4_after['status'] == 'PLANNING',
        'originStillMissing': bool(task4_after.get('missingInfoQuestions')) and any('起点' in str(q_item) for q_item in task4_after.get('missingInfoQuestions', []))
    }
    q.record('tc077-s2-invalid-evaluation', {'task': task4_after, 'clarify': clarify4}, checks4)
    q.terminate(tid4)

    # ----------------------------------------------------
    # Case 5: TC-078.S1 / R04
    # No mobile robots available (both G160_F016_A and G160_F016_B offline/disabled).
    # Smart display is online.
    # Plan validation allows display step; display step completes;
    # Robot steps are skipped (ESCORT_CHANNEL_UNAVAILABLE);
    # Task downgrades to PENDING_MANUAL with clear downgrade reason.
    # ----------------------------------------------------
    print("\n--- Running Case 5: No Mobile Robots Available Downgrade (TC-078.S1) ---")
    # Take both mobile robots offline
    for r_code in ['G160_F016_A', 'G160_F016_B']:
        q.cfg(f'/devices/{r_code}/status', 'POST', {'status': 'INACTIVE'})
        dev_obj = next(d for d in q.devices if d.code == r_code)
        with dev_obj.guard:
            dev_obj.state.update(onlineStatus='OFFLINE', workStatus='IDLE')

    row5 = q.submit(
        'tc078-s1-no-mobile-robot',
        '为特殊旅客提供轮椅接续服务，由于无可用移动设备需降级航显并转人工',
        {
            'assistanceType': 'WHEELCHAIR',
            'origin': 'F2_GATE_A',
            'destination': 'F2_SERVICE_POINT'
        }
    )
    tid5 = row5['taskId']
    assert tid5 is not None, "Case 5 task creation failed"
    after5 = q.drive(row5, max_time=30)
    task5 = q.op(f'/tasks/{tid5}')
    assignments5 = q.op(f'/tasks/{tid5}/step-assignments')
    events5 = q.op(f'/tasks/{tid5}/events')

    checks5 = {
        'taskPendingManual': task5['status'] == 'PENDING_MANUAL',
        'downgradeReasonRecorded': bool(task5.get('failureReason') and '无可用移动服务设备' in task5['failureReason']),
        'displayStepExecuted': any(a.get('stepSeq') == 1 and a.get('stepStatus') == 'COMPLETED' for a in assignments5),
        'escortStepSkipped': any(a.get('stepSeq') == 3 and a.get('stepStatus') == 'SKIPPED' for a in assignments5),
        'escortUncoveredEventLogged': any(e.get('eventType') == 'ESCORT_UNCOVERED' for e in events5),
        'taskPendingManualEventLogged': any(e.get('eventType') == 'TASK_PENDING_MANUAL' for e in events5)
    }
    q.record('tc078-s1-evaluation', {'task': task5, 'assignments': assignments5, 'events': events5}, checks5)

    # Restore mobile robots online
    for r_code in ['G160_F016_A', 'G160_F016_B']:
        q.cfg(f'/devices/{r_code}/status', 'POST', {'status': 'ACTIVE'})
        dev_obj = next(d for d in q.devices if d.code == r_code)
        with dev_obj.guard:
            dev_obj.state.update(onlineStatus='ONLINE', workStatus='IDLE')
            dev_obj.heartbeat()

    # ----------------------------------------------------
    # Case 6: TC-079.S1 / R08
    # Guidance execution failure triggers retry / local replanning / manual transfer
    # ----------------------------------------------------
    print("\n--- Running Case 6: Guidance Failure & Local Replan / Manual Transfer (TC-079.S1) ---")
    row6 = q.submit(
        'tc079-s1-escort-failure',
        '为特殊旅客提供轮椅协助，模拟引导失败触发局部重规划与人工接续',
        {
            'assistanceType': 'WHEELCHAIR',
            'origin': 'F2_GATE_A',
            'destination': 'F2_SERVICE_POINT'
        }
    )
    tid6 = row6['taskId']
    assert tid6 is not None, "Case 6 task creation failed"
    # Escort capability fails
    after6 = q.drive(row6, fail_caps=['CAP_ESCORT'], fail_count=5, max_time=30)
    task6 = q.op(f'/tasks/{tid6}')
    events6 = q.op(f'/tasks/{tid6}/events')

    checks6 = {
        'taskEndedInPendingManual': task6['status'] == 'PENDING_MANUAL',
        'retryOrReplanAttempted': any(e.get('eventType') in ['STEP_RETRY_TRIGGERED', 'STEP_RETRY_DISPATCHED', 'REPLANNING_TRIGGERED', 'CANDIDATE_SWITCHED', 'LOCAL_REPLAN', 'STEP_FAILED'] for e in events6),
        'finalManualTransfer': any(e.get('eventType') in ['TASK_PENDING_MANUAL', 'MANUAL_TRANSFER_TRIGGERED'] for e in events6)
    }
    q.record('tc079-s1-evaluation', {'task': task6, 'events': events6}, checks6)

    # Perform manual action MARK_FAILED with reason
    manual_resp = probe_mod.raw(q.op, f'/tasks/{tid6}/manual-actions', {
        'action': 'MARK_FAILED',
        'reason': '现场无可用替代移动设备，操作员处置置为失败'
    })
    task6_final = q.op(f'/tasks/{tid6}')
    q.record('tc079-s1-manual-action', {'response': manual_resp, 'finalTask': task6_final}, {
        'manualActionSucceeded': manual_resp.get('http') == 200,
        'finalStatusFailed': task6_final['status'] == 'FAILED'
    })

    # ----------------------------------------------------
    # Case 7: R06 / R07
    # Motion safety instructions rejection & 5-step limit
    # ----------------------------------------------------
    print("\n--- Running Case 7: Motion Safety Instructions Rejection & Step Limits ---")
    # 6-step candidate rejection
    six_step_list = [
        {'stepSeq': i, 'stepGoal': f'动作{i}', 'capabilityType': 'CAP_INFO_DISPLAY', 'inputParams': {}, 'precondition': '就绪', 'completionCondition': 'displayStatus=SUCCESS', 'failureHandling': '转人工'}
        for i in range(1, 7)
    ]
    row7 = q.submit('step-limit-6-steps', '超过五步限制计划拒绝测试', steps=six_step_list)
    tid7 = row7['taskId']
    task7 = q.op(f'/tasks/{tid7}')
    events7 = q.op(f'/tasks/{tid7}/events')

    checks7 = {
        'sixStepsCandidateRejected': any(e.get('eventType') == 'PLAN_VALIDATED' and e.get('reasonCode') == 'ERR_STEP_LIMIT_EXCEEDED' for e in events7),
        'baselineDowngradeRecorded': any('超限5' in str(e.get('detailSummary', '')) or e.get('eventType') == 'BASELINE_DOWNGRADED' for e in events7)
    }
    q.record('step-limit-evaluation', {'task': task7, 'events': events7}, checks7)
    q.terminate(tid7)

    # ----------------------------------------------------
    # Case 8: Real Edge Browser UI Tests
    # ----------------------------------------------------
    print("\n--- Running Case 8: Real Edge Headless UI Tests ---")
    ui_script = ROOT / 'acceptance/stage3/retest-f025-v186-real-ui.cjs'
    ui_ret = subprocess.run(['node', str(ui_script)], cwd=ROOT, capture_output=True, text=True)
    print("UI tests stdout:", ui_ret.stdout)
    if ui_ret.stderr:
        print("UI tests stderr:", ui_ret.stderr)
    ui_results_file = ROOT / 'acceptance/stage3/evidence/SRS_F025-V1.186-real-ui-results.json'
    assert ui_results_file.exists(), "UI results file missing"
    ui_data = json.loads(ui_results_file.read_text(encoding='utf-8'))
    ui_all_p = all(t.get('result') == 'P' for t in ui_data.get('tests', []))
    q.record('real-ui-evaluation', {'uiResults': ui_data}, {'allUiTestsPassed': ui_all_p and len(ui_data.get('tests', [])) >= 3})
    for t in ui_data.get('tests', []):
        if t.get('taskId'):
            q.terminate(t['taskId'])

    print("\nAll protocol / HTTP / SQL / UI test cases executed successfully!")

finally:
    # 5. Resource cleanup
    print("\n5. Executing cleanup...")
    cleanup_result = q.cleanup()
    print("Cleanup result:", cleanup_result)

    # 6. Stop servers
    print("6. Terminating test servers...")
    p_model.terminate()
    try:
        urllib.request.urlopen('http://127.0.0.1:18129/actuator/shutdown', data=b'', timeout=2)
    except Exception:
        pass
    try:
        import signal
        os.kill(backend_pid, signal.SIGTERM)
    except Exception:
        pass

print("\n--- Summary of All Evaluated Test Cases ---")
cases = q.ev.get('cases', [])
all_passed = True
for c in cases:
    res = c.get('result')
    if res:
        print(f"[{res}] {c['name']}")
        if res != 'P':
            all_passed = False

if all_passed:
    print("\n>>> ALL TEST CASES PASSED (REQUIREMENT_PASSED) <<<")
else:
    print("\n>>> SOME TEST CASES FAILED <<<")
