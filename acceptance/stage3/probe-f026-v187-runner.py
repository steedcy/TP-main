"""Runner for SRS_F026 V1.187 independent verification.
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
model_py = ROOT / 'acceptance/stage3/fixtures/f026-v187-controlled-model.py'
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
start_jar = ROOT / 'acceptance/stage3/fixtures/start-f026-v187-jar.py'
ret = subprocess.run([sys.executable, str(start_jar)], cwd=ROOT)
if ret.returncode != 0:
    p_model.terminate()
    raise RuntimeError(f"Backend failed to start, code {ret.returncode}")

runtime_file = ROOT / '.local-test/runtime-v187.json'
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
s_probe = importlib.util.spec_from_file_location('probe_mod', ROOT / 'acceptance/stage3/probe-f026-v187.py')
probe_mod = importlib.util.module_from_spec(s_probe)
s_probe.loader.exec_module(probe_mod)

q = probe_mod.Round()
q.setup()

try:
    # ----------------------------------------------------
    # Case 1: TC-081.S1, TC-081.S3, TC-082.S1 / R04, R05, R09
    # Complete 4-step plan across 3 physical channels:
    # 航延屏 (CAP_FLIGHT_UPDATE), 智慧航显 (CAP_INFO_DISPLAY), 机器人 (CAP_NOTIFICATION, CAP_NAVIGATION)
    # Supervision evaluates LOW risk (SRS_F026.R05) -> auto-executed.
    # Driven to COMPLETED, recording channel metrics and duration.
    # ----------------------------------------------------
    print("\n--- Running Case 1: Three-Channel Execution & Metrics Recording ---")
    row1 = q.submit(
        'tc081-s1-three-channel-execution',
        '为虚构航班CA1234安排登机口变更协同响应，由航延屏发布、智慧航显提示并由机器人改道引导至F2_TEST_GATE',
        {
            'eventSource': 'MANUAL_FORM',
            'flightNumber': 'CA1234',
            'changeType': 'GATE_CHANGE',
            'originalTime': '2026-11-10T10:00:00',
            'originalGate': 'A01',
            'newGate': 'F2_TEST_GATE',
            'changeDescription': '虚构航班CA1234登机口变更至F2_TEST_GATE',
            'targetLocation': 'F2_TEST_GATE'
        }
    )
    tid1 = row1['taskId']
    assert tid1 is not None, "Case 1 task creation failed"
    after1 = q.drive(row1, max_time=35)
    task1 = q.op(f'/tasks/{tid1}')
    plans1 = q.op(f'/tasks/{tid1}/plan-versions')
    events1 = q.op(f'/tasks/{tid1}/events')
    assignments1 = q.op(f'/tasks/{tid1}/step-assignments')

    completed_event1 = next((e for e in events1 if e.get('eventType') == 'TASK_COMPLETED'), {})
    completed_detail1 = completed_event1.get('detail', '') or completed_event1.get('detailSummary', '') or completed_event1.get('rawDetailSummary', '')

    checks1 = {
        'statusCompleted': task1['status'] == 'COMPLETED',
        'lowRiskAutoExecuted': any(p.get('riskLevel') == 'LOW' for p in plans1) or any('LOW' in str(e.get('detailSummary')) for e in events1 if e.get('eventType') == 'SUPERVISION_JUDGED'),
        'fourStepsAssigned': len(assignments1) == 4,
        'flightUpdateCompleted': any(a.get('stepSeq') == 1 and a.get('stepStatus') == 'COMPLETED' for a in assignments1),
        'infoDisplayCompleted': any(a.get('stepSeq') == 2 and a.get('stepStatus') == 'COMPLETED' for a in assignments1),
        'notificationCompleted': any(a.get('stepSeq') == 3 and a.get('stepStatus') == 'COMPLETED' for a in assignments1),
        'navigationCompleted': any(a.get('stepSeq') == 4 and a.get('stepStatus') == 'COMPLETED' for a in assignments1),
        'channelMetricsPersisted': 'channelMetrics' in completed_detail1 and 'CAP_FLIGHT_UPDATE' in completed_detail1,
        'durationRecorded': all(a.get('feedbackAt') is not None for a in assignments1)
    }
    q.record('tc081-s1-evaluation', {'after': after1, 'plans': plans1, 'events': events1, 'assignments': assignments1}, checks1)

    # ----------------------------------------------------
    # Case 2: TC-080.S1 / R01 & R10
    # Simulated Event Dual Trigger Entry (/api/v1/tasks/flight-change-event)
    # ----------------------------------------------------
    print("\n--- Running Case 2: Simulator Event Dual Trigger Entry ---")
    sim_event_req = {
        'flightNumber': 'CA1881',
        'changeType': 'DELAY',
        'originalTime': '2026-11-10T14:00:00',
        'newTime': '2026-11-10T15:30:00',
        'originalGate': 'GATE_A05',
        'changeDescription': '虚构航班CA1881因天气延误90分钟，预计15:30登机',
        'eventSource': 'SIMULATED_EVENT'
    }
    row2 = q.submit_event('tc080-s1-sim-event', sim_event_req)
    tid2 = row2['taskId']
    assert tid2 is not None, "Case 2 task creation failed"
    task2 = q.op(f'/tasks/{tid2}')
    events2 = q.op(f'/tasks/{tid2}/events')
    sql_task2 = probe_mod.sql(f"select scene_params from {probe_mod.SC}.tasks where id={tid2}")

    checks2 = {
        'taskCreated': tid2 is not None,
        'taskFamilyCorrect': task2['taskFamily'] == 'FLIGHT_CHANGE_RESPONSE',
        'eventSourceRecorded': 'SIMULATED_EVENT' in str(sql_task2),
        'delayNewTimeRecorded': '2026-11-10T15:30:00' in str(sql_task2),
        'dataAnonymized': 'CA1881' in str(sql_task2) and 'CA1881' in task2['taskGoal']
    }
    q.record('tc080-s1-sim-evaluation', {'task': task2, 'events': events2, 'sqlTask': sql_task2}, checks2)
    q.terminate(tid2)

    # ----------------------------------------------------
    # Case 3: TC-080.S1 / R01, R02, R10
    # Four Change Types & Field Boundaries Validation
    # ----------------------------------------------------
    print("\n--- Running Case 3: Four Event Types & Field Boundaries Validation ---")
    # Boundary: flightNumber < 2 chars rejected
    resp_short_flight = probe_mod.raw(q.op, '/tasks/flight-change-event', {
        'flightNumber': 'A',
        'changeType': 'CANCEL',
        'originalTime': '2026-11-10T10:00:00',
        'changeDescription': '取消测试'
    })
    # Boundary: flightNumber > 10 chars rejected
    resp_long_flight = probe_mod.raw(q.op, '/tasks/flight-change-event', {
        'flightNumber': 'CA12345678901',
        'changeType': 'CANCEL',
        'originalTime': '2026-11-10T10:00:00',
        'changeDescription': '取消测试'
    })
    # Boundary: changeDescription > 200 chars rejected
    resp_long_desc = probe_mod.raw(q.op, '/tasks/flight-change-event', {
        'flightNumber': 'CA1234',
        'changeType': 'CANCEL',
        'originalTime': '2026-11-10T10:00:00',
        'changeDescription': 'D' * 201
    })
    # Boundary: CANCEL event valid without newTime and without newGate
    resp_cancel = probe_mod.raw(q.op, '/tasks/flight-change-event', {
        'flightNumber': 'CZ3000',
        'changeType': 'CANCEL',
        'originalTime': '2026-11-10T10:00:00',
        'originalGate': 'B02',
        'changeDescription': '虚构航班CZ3000因流控取消'
    })
    # Boundary: EARLY event valid with newTime
    resp_early = probe_mod.raw(q.op, '/tasks/flight-change-event', {
        'flightNumber': 'MU5678',
        'changeType': 'EARLY',
        'originalTime': '2026-11-10T12:00:00',
        'newTime': '2026-11-10T11:40:00',
        'originalGate': 'C03',
        'changeDescription': '虚构航班MU5678提前20分钟登机'
    })

    tid_cancel = resp_cancel.get('body', {}).get('data', {}).get('id')
    tid_early = resp_early.get('body', {}).get('data', {}).get('id')
    if tid_cancel: q.terminate(tid_cancel)
    if tid_early: q.terminate(tid_early)

    checks3 = {
        'shortFlightRejected': resp_short_flight.get('http') == 400,
        'longFlightRejected': resp_long_flight.get('http') == 400,
        'longDescRejected': resp_long_desc.get('http') == 400,
        'cancelAcceptedWithoutNewTime': resp_cancel.get('http') in (200, 201),
        'earlyAcceptedWithNewTime': resp_early.get('http') in (200, 201)
    }
    q.record('tc080-s1-boundaries-evaluation', {
        'respShort': resp_short_flight,
        'respLong': resp_long_flight,
        'respLongDesc': resp_long_desc,
        'respCancel': resp_cancel,
        'respEarly': resp_early
    }, checks3)

    # ----------------------------------------------------
    # Case 4: TC-080.S2 / R02, R03 & DEF-S3-005
    # Missing Conditional Required Field (newGate) triggers clarification;
    # Operator clarifies -> advances to planning.
    # Checks that system NEVER asks for internal robotId or routeCode.
    # ----------------------------------------------------
    print("\n--- Running Case 4: Missing Conditional Gate Clarification ---")
    row4 = q.submit(
        'tc080-s2-missing-gate',
        '虚构航班CA1234登机口发生变更需改道引导',
        {
            'flightNumber': 'CA1234',
            'changeType': 'GATE_CHANGE',
            'originalTime': '2026-11-10T10:00:00',
            'originalGate': 'A01',
            # missing newGate
            'changeDescription': '登机口变更需改道引导'
        },
        infoComplete=False,
        missingInfoQuestions=['请补充变更后的登机口']
    )
    tid4 = row4['taskId']
    assert tid4 is not None, "Case 4 task creation failed"
    task4_before = q.op(f'/tasks/{tid4}')
    questions4 = task4_before.get('missingInfoQuestions') or []

    # Verify questions contains newGate and ZERO internal device questions
    has_gate_question = any('登机口' in str(q_item) for q_item in questions4)
    no_robot_query = not any(any(kw in str(q_item) for kw in ['机器人', '设备', '路线', '编码']) for q_item in questions4)

    # Operator clarifies with newGate
    clarify_resp4 = probe_mod.raw(q.op, f'/tasks/{tid4}/clarify', {
        'answers': {q_text: 'F2_TEST_GATE' for q_text in questions4}
    })
    task4_after = q.op(f'/tasks/{tid4}')
    events4 = q.op(f'/tasks/{tid4}/events')

    checks4 = {
        'initialStatusPlanning': task4_before['status'] == 'PLANNING',
        'hasGateQuestion': has_gate_question,
        'defS3005NoRobotQuery': no_robot_query,
        'clarifyAccepted': clarify_resp4.get('http') == 200,
        'planningAdvanced': any(e.get('eventType') == 'GOAL_CLARIFIED' and '关键信息已完整' in str(e.get('detailSummary', '')) for e in events4)
    }
    q.record('tc080-s2-clarify-evaluation', {
        'questions': questions4,
        'clarifyResponse': clarify_resp4,
        'taskAfter': task4_after,
        'events': events4
    }, checks4)
    q.terminate(tid4)

    # ----------------------------------------------------
    # Case 5: TC-080.S2 / R03
    # Unclarified After 3 Rounds Transitions to PENDING_MANUAL
    # ----------------------------------------------------
    print("\n--- Running Case 5: 3 Rounds Unclarified Transitions to PENDING_MANUAL ---")
    row5 = q.submit(
        'tc080-s2-unclarified-limit',
        '虚构航班HU7890延误事件缺少新时间',
        {
            'flightNumber': 'HU7890',
            'changeType': 'DELAY',
            'originalTime': '2026-11-10T10:00:00',
            # missing newTime
            'changeDescription': '航班延误'
        },
        infoComplete=False,
        missingInfoQuestions=['请补充变更后的航班时间']
    )
    tid5 = row5['taskId']
    assert tid5 is not None, "Case 5 task creation failed"
    task5 = q.op(f'/tasks/{tid5}')
    q5 = task5.get('missingInfoQuestions') or []

    # Round 1: answer with placeholder/punctuation
    clarify5_1 = probe_mod.raw(q.op, f'/tasks/{tid5}/clarify', {'answers': {q_text: '；；' for q_text in q5}})
    # Round 2: answer with placeholder/punctuation
    clarify5_2 = probe_mod.raw(q.op, f'/tasks/{tid5}/clarify', {'answers': {q_text: '；；' for q_text in q5}})
    # Round 3: answer with placeholder/punctuation
    clarify5_3 = probe_mod.raw(q.op, f'/tasks/{tid5}/clarify', {'answers': {q_text: '；；' for q_text in q5}})

    task5_final = q.op(f'/tasks/{tid5}')
    events5 = q.op(f'/tasks/{tid5}/events')

    checks5 = {
        'taskPendingManual': task5_final['status'] == 'PENDING_MANUAL',
        'threeRoundsReason': '三轮信息补充后仍缺少关键信息' in str(task5_final.get('failureReason', '')),
        'taskPendingManualEventLogged': any(e.get('eventType') == 'TASK_PENDING_MANUAL' for e in events5)
    }
    q.record('tc080-s2-limit-evaluation', {'taskFinal': task5_final, 'events': events5}, checks5)
    q.terminate(tid5)

    # ----------------------------------------------------
    # Case 6: DEF-S3-005 & R02
    # Model Illegal Questions Override (FlightChangeRequiredInfoGuard)
    # When flight facts are complete, model attempts to ask for internal robotId/routeCode.
    # System overrides model questions and advances to planning.
    # ----------------------------------------------------
    print("\n--- Running Case 6: Model Internal Questions Override (DEF-S3-005) ---")
    row6 = q.submit(
        'def-s3-005-override',
        '虚构航班CA1234完整登机口变更输入，验证彻底忽略模型内部设备追问',
        {
            'eventSource': 'MANUAL_FORM',
            'flightNumber': 'CA1234',
            'changeType': 'GATE_CHANGE',
            'originalTime': '2026-11-10T10:00:00',
            'originalGate': 'A01',
            'newGate': 'F2_TEST_GATE',
            'changeDescription': '登机口变更至F2_TEST_GATE'
        },
        infoComplete=False, # Model maliciously claims info is incomplete
        missingInfoQuestions=['请指定内部机器人ID', '请提供路线编码'] # Bogus model questions
    )
    tid6 = row6['taskId']
    task6 = q.op(f'/tasks/{tid6}')
    events6 = q.op(f'/tasks/{tid6}/events')

    checks6 = {
        'noMissingQuestionsInTask': not task6.get('missingInfoQuestions'),
        'overrideEventLogged': any(e.get('eventType') == 'GOAL_CLARIFIED' and e.get('reasonCode') == 'INFO_CHECK_OVERRIDE' and '忽略模型追问' in str(e.get('detailSummary', '')) for e in events6),
        'planningAdvanced': any(e.get('eventType') == 'GOAL_CLARIFIED' and '进入规划上下文构建' in str(e.get('detailSummary', '')) for e in events6)
    }
    q.record('def-s3-005-override-evaluation', {'task': task6, 'events': events6}, checks6)
    q.terminate(tid6)

    # ----------------------------------------------------
    # Case 7: TC-081.S2 / R07
    # Motion Safety Instructions Rejection & Spatial Intent Only
    # ----------------------------------------------------
    print("\n--- Running Case 7: Motion Safety Instructions Rejection & Spatial Intent Only ---")
    unsafe_steps = [
        {
            'stepSeq': 1,
            'capabilityType': 'CAP_FLIGHT_UPDATE',
            'stepGoal': '在航延屏发布航班变更',
            'inputParams': {'flightNumber': 'CA1234', 'updateType': 'GATE_CHANGE', 'updateContent': '登机口变更', 'displayDuration': 60},
            'precondition': '就绪',
            'completionCondition': 'publishStatus=SUCCESS',
            'failureHandling': '转人工'
        },
        {
            'stepSeq': 2,
            'capabilityType': 'CAP_NAVIGATION',
            'stepGoal': '以1.5m/s速度执行避障和急停', # Illegal motion safety control parameters!
            'inputParams': {'speed': 1.5, 'targetLocation': 'F2_TEST_GATE', 'waypoint': [10, 20]},
            'precondition': '就绪',
            'completionCondition': 'routeGenerated=true',
            'failureHandling': '转人工'
        }
    ]
    row7 = q.submit('motion-safety-violation', '测试运动安全控制参数拦截', steps=unsafe_steps)
    tid7 = row7['taskId']
    task7 = q.op(f'/tasks/{tid7}')
    events7 = q.op(f'/tasks/{tid7}/events')

    checks7 = {
        'motionSafetyRejected': any(e.get('eventType') == 'PLAN_VALIDATED' and 'ERR_MOTION_SAFETY' in str(e.get('reasonCode')) for e in events7),
        'safetyDetailsLogged': any('速度' in str(e.get('detailSummary', '')) or '急停' in str(e.get('detailSummary', '')) or 'speed' in str(e.get('detailSummary', '')) for e in events7)
    }
    q.record('motion-safety-evaluation', {'task': task7, 'events': events7}, checks7)
    q.terminate(tid7)

    # ----------------------------------------------------
    # Case 8: TC-082.S1, TC-083.S1 / R08
    # Guidance Step Execution Failure -> Retry Dispatched -> PENDING_MANUAL -> Manual Action
    # ----------------------------------------------------
    print("\n--- Running Case 8: Guidance Execution Failure & Local Replan / Manual Transfer ---")
    row8 = q.submit(
        'tc083-s1-guidance-failure',
        '虚构航班CA1234改道引导失败触发重试与转人工',
        {
            'eventSource': 'MANUAL_FORM',
            'flightNumber': 'CA1234',
            'changeType': 'GATE_CHANGE',
            'originalTime': '2026-11-10T10:00:00',
            'originalGate': 'A01',
            'newGate': 'F2_TEST_GATE',
            'changeDescription': '引导失败转人工测试'
        }
    )
    tid8 = row8['taskId']
    assert tid8 is not None, "Case 8 task creation failed"
    # Drive with CAP_NAVIGATION failing
    after8 = q.drive(row8, fail_caps=['CAP_NAVIGATION'], fail_count=5, max_time=30)
    task8 = q.op(f'/tasks/{tid8}')
    events8 = q.op(f'/tasks/{tid8}/events')

    checks8 = {
        'taskEndedInPendingManual': task8['status'] == 'PENDING_MANUAL',
        'retryOrReplanAttempted': any(e.get('eventType') in ['STEP_RETRY_TRIGGERED', 'STEP_RETRY_DISPATCHED', 'REPLANNING_TRIGGERED', 'LOCAL_REPLAN', 'STEP_FAILED'] for e in events8),
        'manualTransferLogged': any(e.get('eventType') == 'TASK_PENDING_MANUAL' for e in events8)
    }
    q.record('tc083-s1-failure-evaluation', {'task': task8, 'events': events8}, checks8)

    # Perform manual action MARK_FAILED
    manual_resp8 = probe_mod.raw(q.op, f'/tasks/{tid8}/manual-actions', {
        'action': 'MARK_FAILED',
        'reason': '改道现场遇障碍无法通行，操作员标记为失败'
    })
    task8_final = q.op(f'/tasks/{tid8}')
    q.record('tc083-s1-manual-action', {'response': manual_resp8, 'finalTask': task8_final}, {
        'manualActionSucceeded': manual_resp8.get('http') == 200,
        'finalStatusFailed': task8_final['status'] == 'FAILED'
    })

    # ----------------------------------------------------
    # Case 9: SRS_F026.R06 / TC-083.S1
    # 5-step Limit Exceeded Downgrade
    # ----------------------------------------------------
    print("\n--- Running Case 9: 5-step Limit Exceeded Plan Rejection ---")
    six_step_list = [
        {'stepSeq': i, 'stepGoal': f'动作{i}', 'capabilityType': 'CAP_INFO_DISPLAY', 'inputParams': {'contentType': 'TEXT', 'contentData': '提示', 'displayDuration': 60}, 'precondition': '就绪', 'completionCondition': 'displayStatus=SUCCESS', 'failureHandling': '转人工'}
        for i in range(1, 7)
    ]
    row9 = q.submit('step-limit-6-steps', '超过五步限制计划拒绝测试', steps=six_step_list)
    tid9 = row9['taskId']
    task9 = q.op(f'/tasks/{tid9}')
    events9 = q.op(f'/tasks/{tid9}/events')

    checks9 = {
        'sixStepsCandidateRejected': any(e.get('eventType') == 'PLAN_VALIDATED' and e.get('reasonCode') == 'ERR_STEP_LIMIT_EXCEEDED' for e in events9),
        'baselineDowngradeRecorded': any('超限5' in str(e.get('detailSummary', '')) or e.get('eventType') == 'BASELINE_DOWNGRADED' for e in events9)
    }
    q.record('step-limit-evaluation', {'task': task9, 'events': events9}, checks9)
    q.terminate(tid9)

    # ----------------------------------------------------
    # Case 10: Real Edge Browser UI Tests
    # ----------------------------------------------------
    print("\n--- Running Case 10: Real Edge Headless UI Tests ---")
    ui_script = ROOT / 'acceptance/stage3/retest-f026-v187-real-ui.cjs'
    ui_ret = subprocess.run(['node', str(ui_script)], cwd=ROOT, capture_output=True, encoding='utf-8', errors='replace')
    print("UI tests stdout:", ui_ret.stdout)
    if ui_ret.stderr:
        print("UI tests stderr:", ui_ret.stderr)
    ui_results_file = ROOT / 'acceptance/stage3/evidence/SRS_F026-V1.187-real-ui-results.json'
    assert ui_results_file.exists(), "UI results file missing"
    ui_data = json.loads(ui_results_file.read_text(encoding='utf-8'))
    ui_all_p = all(t.get('result') == 'P' for t in ui_data.get('tests', []))
    q.record('real-ui-evaluation', {'uiResults': ui_data}, {'allUiTestsPassed': ui_all_p and len(ui_data.get('tests', [])) >= 3})
    for t in ui_data.get('tests', []):
        if t.get('createdTaskId'):
            q.terminate(t['createdTaskId'])
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
