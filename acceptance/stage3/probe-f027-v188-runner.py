"""Runner for SRS_F027 V1.188 independent verification.
Executes protocol/HTTP/SQL assertions, runs real Edge UI tests, and cleans up.
"""
import copy, hashlib, json, os, socket, subprocess, sys, threading, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT.parent / 'tip'
sys.path.insert(0, str(ROOT / 'acceptance/stage3'))

# 1. Start controlled model
print("1. Starting controlled model on 18117...")
model_py = ROOT / 'acceptance/stage3/fixtures/f027-v188-controlled-model.py'
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
start_jar = ROOT / 'acceptance/stage3/fixtures/start-f027-v188-jar.py'
ret = subprocess.run([sys.executable, str(start_jar)], cwd=ROOT)
if ret.returncode != 0:
    p_model.terminate()
    raise RuntimeError(f"Backend failed to start, code {ret.returncode}")

runtime_file = ROOT / '.local-test/runtime-v188.json'
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
                    status = res.status
                    ctype = res.headers.get('Content-Type', 'application/json')
                    body = res.read()
            except urllib.error.HTTPError as ex:
                status = ex.code
                ctype = ex.headers.get('Content-Type', 'application/json')
                body = ex.read()
            except Exception as ex:
                status = 502
                body = json.dumps({'error': str(ex)}).encode('utf-8')
        else:
            p = self.path.split('?')[0].lstrip('/')
            f = ROOT / 'frontend/dist' / p
            if f.is_dir() or not f.exists():
                f = ROOT / 'frontend/dist/index.html'
            if f.exists():
                status = 200
                ctype = mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
                body = f.read_bytes()
            else:
                status = 404
                body = b'Not found'
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self): self.handle_all()
    def do_POST(self): self.handle_all()
    def do_PUT(self): self.handle_all()
    def do_DELETE(self): self.handle_all()

proxy_server = ThreadingHTTPServer(('127.0.0.1', 15179), ProxyHandler)
t_proxy = threading.Thread(target=proxy_server.serve_forever, daemon=True)
t_proxy.start()
print("Proxy listening on 15179")

# 4. Initialize test probe
print("4. Initializing test probe...")
import importlib.util
s = importlib.util.spec_from_file_location('pmod', ROOT / 'acceptance/stage3/probe-f027-v188.py')
pmod = importlib.util.module_from_spec(s)
s.loader.exec_module(pmod)
round_f027 = pmod.Round()
print("Round F027 loaded successfully")
round_f027.setup()

try:
    # --- Case 1: Execute Multi-Version Task with Local Replanning ---
    print("\n--- Running Case 1: Multi-Version Task with Local Replanning ---")
    goal = "请为虚构测试旅客P-F027在F2_TEST_GATE提供协助指引至F2_ZONE_A，包含局部重规划与版本追溯验证"
    t1_row = round_f027.submit(
        'tc084-trace-multiversion',
        goal,
        fail_caps=['CAP_NOTIFICATION'],
        fail_count=4
    )
    t1_id = t1_row['taskId']
    obs1 = round_f027.drive(t1_row, fail_caps=['CAP_NOTIFICATION'], fail_count=4, max_time=60)
    t1_final = round_f027.op(f'/tasks/{t1_id}')
    t1_code = t1_final.get('taskCode')

    # --- Case 2: Evaluate Trace Full Lifecycle & Plan Step Details (DEF-S3-008, R01, TC-084.S1) ---
    print("\n--- Running Case 2: Plan Version Step Details Table & Full Lifecycle Trace (DEF-S3-008) ---")
    plan_versions_resp = pmod.raw(round_f027.op, f'/tasks/{t1_id}/plan-versions', method='GET')
    plan_versions = plan_versions_resp.get('body', {}).get('data', [])

    has_multi_versions = len(plan_versions) >= 2
    version_step_tables_complete = True
    for pv in plan_versions:
        steps = pv.get('planSteps', [])
        if not steps or len(steps) == 0:
            version_step_tables_complete = False
            break
        for st in steps:
            if not st.get('stepSeq') or not st.get('stepGoal') or not st.get('capabilityType'):
                version_step_tables_complete = False
                break

    # Verify causal chain in events
    events_resp = pmod.raw(round_f027.op, f'/tasks/{t1_id}/events', method='GET')
    events = events_resp.get('body', {}).get('data', [])
    event_types = [e.get('eventType') for e in events]

    has_goal_submitted = 'GOAL_SUBMITTED' in event_types
    has_context_snapshot = 'CONTEXT_SNAPSHOT_GENERATED' in event_types
    has_plan_generated = 'PLAN_GENERATED' in event_types
    has_supervision = 'SUPERVISION_JUDGED' in event_types
    has_dispatch = 'STEP_DISPATCHED' in event_types
    has_feedback = 'EXECUTION_FEEDBACK_RECEIVED' in event_types
    has_completed = 'TASK_COMPLETED' in event_types or t1_final.get('status') == 'COMPLETED'

    round_f027.record('tc084-s1-trace-evaluation', {
        'taskId': t1_id,
        'planVersionCount': len(plan_versions),
        'versionStepTablesComplete': version_step_tables_complete,
        'eventCount': len(events),
        'causalEvents': event_types
    }, {
        'hasMultiVersions': has_multi_versions,
        'versionStepTablesComplete': version_step_tables_complete,
        'hasGoalSubmitted': has_goal_submitted,
        'hasContextSnapshot': has_context_snapshot,
        'hasPlanGenerated': has_plan_generated,
        'hasSupervision': has_supervision,
        'hasDispatch': has_dispatch,
        'hasFeedback': has_feedback,
        'hasCompleted': has_completed
    })

    # --- Case 3: Evaluate Event Fields and Reason Code Completeness (DEF-S3-057, R02, TC-084.S2) ---
    print("\n--- Running Case 3: Event Fields and Reason Codes Completeness (DEF-S3-057) ---")
    all_events_valid = True
    zero_null_reason_codes = True
    invalid_event_sample = []

    for ev in events:
        eid = ev.get('id')
        etype = ev.get('eventType')
        occurred = ev.get('occurredAt')
        trig = ev.get('trigger')
        rcode = ev.get('reasonCode')
        detail = ev.get('detailSummary')

        if not etype or not occurred or not trig or not detail:
            all_events_valid = False
            invalid_event_sample.append({'id': eid, 'reason': 'missing_core_fields', 'event': ev})

        if rcode is None or str(rcode).strip() == '' or str(rcode).strip().lower() == 'null':
            zero_null_reason_codes = False
            invalid_event_sample.append({'id': eid, 'reason': 'null_or_empty_reason_code', 'event': ev})

    round_f027.record('tc084-s2-event-fields-evaluation', {
        'taskId': t1_id,
        'totalEvents': len(events),
        'zeroNullReasonCodes': zero_null_reason_codes,
        'sampleReasonCodes': [{'type': e.get('eventType'), 'code': e.get('reasonCode')} for e in events[:8]],
        'invalidSample': invalid_event_sample
    }, {
        'hasAdequateEvents': len(events) >= 10,
        'allEventsValid': all_events_valid,
        'zeroNullReasonCodes': zero_null_reason_codes
    })

    # --- Case 4: Event Immutability (SRS_F027.R03) ---
    print("\n--- Running Case 4: Event Immutability Protection (R03) ---")
    db_events_before = pmod.rows(f"select id, task_id, event_type, reason_code, detail_summary from {pmod.SC}.task_events where task_id={t1_id} order by id")
    hash_before = hashlib.sha256(json.dumps(db_events_before, sort_keys=True).encode('utf-8')).hexdigest()

    first_event_id = db_events_before[0]['id']
    put_resp = pmod.raw(round_f027.op, f'/tasks/{t1_id}/events/{first_event_id}', {'detailSummary': 'tampered_summary'}, method='PUT')
    del_resp = pmod.raw(round_f027.op, f'/tasks/{t1_id}/events/{first_event_id}', method='DELETE')

    db_events_after = pmod.rows(f"select id, task_id, event_type, reason_code, detail_summary from {pmod.SC}.task_events where task_id={t1_id} order by id")
    hash_after = hashlib.sha256(json.dumps(db_events_after, sort_keys=True).encode('utf-8')).hexdigest()

    put_rejected = put_resp.get('http') in (403, 404, 405, 500)
    del_rejected = del_resp.get('http') in (403, 404, 405, 500)
    data_unchanged = (len(db_events_before) == len(db_events_after)) and (hash_before == hash_after)

    round_f027.record('tc084-s2-immutability-evaluation', {
        'taskId': t1_id,
        'eventId': first_event_id,
        'putHttp': put_resp.get('http'),
        'delHttp': del_resp.get('http'),
        'hashBefore': hash_before,
        'hashAfter': hash_after,
        'dataUnchanged': data_unchanged
    }, {
        'putRejected': put_rejected,
        'delRejected': del_rejected,
        'dataUnchanged': data_unchanged
    })

    # --- Case 5: Plan Version & Context Snapshot Retention (SRS_F027.R04, R05) ---
    print("\n--- Running Case 5: Plan Version & Context Snapshot Retention (R04, R05) ---")
    snapshots_resp = pmod.raw(round_f027.op, f'/tasks/{t1_id}/context-snapshots', method='GET')
    snapshots = snapshots_resp.get('body', {}).get('data', [])

    db_snapshots = pmod.rows(f"select id, snapshot_code, task_id from {pmod.SC}.context_snapshots where task_id={t1_id}")
    db_plan_versions = pmod.rows(f"select id, version_no, source, structure_check_result from {pmod.SC}.plan_versions where task_id={t1_id} order by version_no")

    has_retained_versions = len(db_plan_versions) >= 2
    has_context_snapshots = (len(snapshots) > 0) or (len(db_snapshots) > 0)

    round_f027.record('tc084-s2-retention-evaluation', {
        'taskId': t1_id,
        'dbPlanVersionCount': len(db_plan_versions),
        'dbPlanVersions': db_plan_versions,
        'contextSnapshotCount': len(snapshots) or len(db_snapshots)
    }, {
        'hasRetainedVersions': has_retained_versions,
        'hasContextSnapshots': has_context_snapshots
    })

    # --- Case 6: Privacy and Credential Sanitization (SRS_F027.R06) ---
    print("\n--- Running Case 6: Privacy and Credential Sanitization (R06) ---")
    all_trace_text = json.dumps({
        'events': events,
        'planVersions': plan_versions,
        'snapshots': snapshots,
        'task': t1_final
    }, ensure_ascii=False)

    canary_leaked = ('CANARY' in all_trace_text) or ('13800138000' in all_trace_text) or ('1101011990' in all_trace_text)
    credentials_leaked = ('$2a$' in all_trace_text) or ('password_hash' in all_trace_text) or ('jwt_secret' in all_trace_text)
    privacy_protected = (not canary_leaked) and (not credentials_leaked)

    round_f027.record('tc084-s2-privacy-evaluation', {
        'taskId': t1_id,
        'canaryLeaked': canary_leaked,
        'credentialsLeaked': credentials_leaked,
        'privacyProtected': privacy_protected
    }, {
        'privacyProtected': privacy_protected
    })

    # --- Case 7: Absence of Export & Evaluation Report Endpoints (SRS_F027.R07, TC-084.S3) ---
    print("\n--- Running Case 7: Absence of Export & Evaluation Report Endpoints (R07, TC-084.S3) ---")
    export_task_resp = pmod.raw(round_f027.op, f'/tasks/{t1_id}/export', method='GET')
    export_all_resp = pmod.raw(round_f027.op, '/tasks/export', method='GET')
    report_eval_resp = pmod.raw(round_f027.op, '/reports/evaluation', method='GET')

    no_export_endpoints = (
        export_task_resp.get('http') == 404 and
        export_all_resp.get('http') in (400, 404, 405, 500) and
        report_eval_resp.get('http') == 404
    )

    round_f027.record('tc084-s3-no-export-evaluation', {
        'taskId': t1_id,
        'exportTaskHttp': export_task_resp.get('http'),
        'exportAllHttp': export_all_resp.get('http'),
        'reportEvalHttp': report_eval_resp.get('http')
    }, {
        'noExportEndpoints': no_export_endpoints
    })

    # --- Case 8: Role-based Access Control on Trace Query (SRS_F027.R08) ---
    print("\n--- Running Case 8: Role-Based Access Control on Trace Query (R08) ---")
    admin_resp = pmod.raw(round_f027.admin, f'/tasks/{t1_id}/events', method='GET')
    operator_resp = pmod.raw(round_f027.op, f'/tasks/{t1_id}/events', method='GET')
    config_resp = pmod.raw(round_f027.cfg, f'/tasks/{t1_id}/events', method='GET')

    admin_ok = admin_resp.get('http') == 200
    operator_ok = operator_resp.get('http') == 200
    config_denied = config_resp.get('http') == 403

    # Check denial log in operation_logs
    denial_logs = pmod.rows(f"select id, username, operation_type, operation_target, operation_result from {pmod.SC}.operation_logs where username='set' and operation_type='ACCESS_DENIED' order by id desc limit 5")
    has_denial_log = len(denial_logs) > 0

    round_f027.record('tc084-s2-permissions-evaluation', {
        'taskId': t1_id,
        'adminHttp': admin_resp.get('http'),
        'operatorHttp': operator_resp.get('http'),
        'configAdminHttp': config_resp.get('http'),
        'denialLogs': denial_logs
    }, {
        'adminOk': admin_ok,
        'operatorOk': operator_ok,
        'configDenied': config_denied,
        'hasDenialLog': has_denial_log
    })

    # --- Case 9: Empty Query & Missing Events Section (TC-084.S3, NT-S3-007 closed) ---
    print("\n--- Running Case 9: Empty Query and Non-Existent Task Handling (TC-084.S3) ---")
    non_existent_resp = pmod.raw(round_f027.op, '/tasks/999999/events', method='GET')
    empty_handled_cleanly = non_existent_resp.get('http') in (200, 404)
    # Check that it doesn't crash or fabricate
    fabricated_data = False
    if non_existent_resp.get('http') == 200:
        data = non_existent_resp.get('body', {}).get('data', [])
        fabricated_data = len(data) > 0

    round_f027.record('tc084-s3-empty-state-evaluation', {
        'nonExistentHttp': non_existent_resp.get('http'),
        'fabricatedData': fabricated_data
    }, {
        'emptyHandledCleanly': empty_handled_cleanly,
        'noFabrication': not fabricated_data
    })

    # --- Case 10: Real Edge Headless UI Tests ---
    print("\n--- Running Case 10: Real Edge Headless UI Tests ---")
    ui_script = ROOT / 'acceptance/stage3/retest-f027-v188-real-ui.cjs'
    ui_env = os.environ.copy()
    ui_env['TARGET_TASK_ID'] = str(t1_id)
    ui_env['TARGET_TASK_CODE'] = str(t1_code)

    ui_ret = subprocess.run(['node', str(ui_script)], cwd=ROOT, env=ui_env, capture_output=True, encoding='utf-8', errors='replace')
    print("UI tests stdout:", ui_ret.stdout)
    if ui_ret.stderr:
        print("UI tests stderr:", ui_ret.stderr)

    ui_results_file = ROOT / 'acceptance/stage3/evidence/SRS_F027-V1.188-real-ui-results.json'
    ui_results = {}
    if ui_results_file.exists():
        ui_results = json.loads(ui_results_file.read_text(encoding='utf-8'))

    ui_all_p = all(t.get('result') == 'P' for t in ui_results.get('tests', [])) if ui_results.get('tests') else False

    round_f027.record('real-ui-evaluation', {
        'uiExitCode': ui_ret.returncode,
        'uiResults': ui_results
    }, {
        'uiProcessSuccess': ui_ret.returncode == 0,
        'allUiTestsPassed': ui_all_p
    })

    print("\nAll protocol / HTTP / SQL / UI test cases executed successfully!")

finally:
    # 5. Cleanup
    print("\n5. Executing cleanup...")
    clean_row = round_f027.cleanup()
    print("Cleanup result:", clean_row)

    # 6. Terminate servers
    print("6. Terminating test servers...")
    proxy_server.shutdown()
    p_model.terminate()

    try:
        subprocess.run(['taskkill', '/F', '/PID', str(backend_pid)], capture_output=True)
    except Exception:
        pass

# Summary output
print("\n--- Summary of All Evaluated Test Cases ---")
all_p = True
for c in round_f027.ev['cases']:
    res = c.get('result', 'INFO')
    print(f"[{res}] {c['name']}")
    if res == 'F':
        all_p = False

if all_p:
    print("\n>>> ALL TEST CASES PASSED (REQUIREMENT_PASSED) <<<")
else:
    print("\n>>> SOME TEST CASES FAILED <<<")
