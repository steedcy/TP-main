"""SRS_F026 V1.187 independent real HTTP/SQL/protocol round.
GPT-owned schema tip_gpt_f006_v118_20261030 / Redis DB 10.
Synthetic model and protocol devices, production packaged JAR on 18129, proxy on 15179.
"""
import copy, importlib.util, json, mimetypes, os, socket, subprocess, sys, threading, time, traceback, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

R = Path(__file__).resolve().parents[2]
old = R.parent / 'tip'
L = R / '.local-test'
E = R / 'acceptance/stage3/evidence'
L.mkdir(exist_ok=True)
E.mkdir(parents=True, exist_ok=True)

def mod(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

b = mod('b', R / 'acceptance/stage3/probe-f022-v179-base.py')
d_mod = mod('db', old / 'scripts/isolated-reset-db.py')
SC = 'tip_gpt_f006_v118_20261030'

def sql(query):
    result = subprocess.run(
        d_mod.common + ['-d', d_mod.shared, '-At'],
        input=query + ';\n',
        env=dict(d_mod.variables, PGCLIENTENCODING='UTF8'),
        encoding='utf-8',
        errors='replace',
        capture_output=True,
        check=True
    )
    return result.stdout.strip()

import re, base64

def rows(q):
    out = sql("select replace(encode(convert_to(row_to_json(gpt_row)::text,'UTF8'),'base64'),E'\\n','') from (" + re.sub(r'select row_to_json\((\w+)\)::text', r'select \1.*', q) + ") gpt_row")
    return [json.loads(base64.b64decode(x)) for x in out.splitlines() if x.strip()]

lit = b.lit
now = b.now

SHA = '8a130d72805c744ae66548911f874dbf5dab9273'
OUT = E / 'SRS_F026-V1.187-http-sql-protocol-20261109.json'
CONFIG = L / 'f026-v187-cases.json'

def raw(api, path, body=None, method='POST'):
    req = urllib.request.Request(
        b.l.BASE + path,
        json.dumps(body).encode('utf-8') if body is not None else None,
        {'Content-Type': 'application/json', **({'Authorization': 'Bearer ' + api.token} if api else {})},
        method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return {'http': r.status, 'body': json.load(r)}
    except urllib.error.HTTPError as ex:
        try:
            return {'http': ex.code, 'body': json.load(ex)}
        except Exception:
            return {'http': ex.code, 'body': {'error': str(ex)}}

class Round:
    def __init__(self):
        b.l.BASE = 'http://127.0.0.1:18129/api/v1'
        self.cfg = b.l.API('配置管理员')
        self.op = b.l.API('运行操作员')
        self.devices = []
        self.tasks = []
        self.cases = {}
        self.original = {}
        self.ev = {
            'productSha': SHA,
            'tag': 'V1.187',
            'handoffSha': '765fd938f3ad61a5b48ad0a7cf49ea4cf81c81dc',
            'baseline': 'V2.4',
            'startedAt': now(),
            'schema': SC,
            'redisDb': 10,
            'cases': [],
            'diagnostics': []
        }
        self.save()

    def save(self):
        self.ev.update(taskIds=self.tasks)
        OUT.write_text(json.dumps(self.ev, ensure_ascii=False, indent=2), encoding='utf-8')

    def record(self, name, values, checks=None):
        row = {'name': name, 'at': now(), **values}
        if checks is not None:
            row.update(checks=checks, result='P' if all(checks.values()) else 'F')
        self.ev['cases'].append(row)
        self.save()
        print(f"[{row.get('result', 'INFO')}] {name} (taskId={row.get('taskId')})", flush=True)
        return row

    def observe(self, tid):
        o = b.p.observe(self.op, tid)
        for k, t in [('commandRows', 'device_commands'), ('exceptions', 'task_exceptions')]:
            o[k] = rows(f'select * from {SC}.{t} where task_id={tid} order by id')
        o['transport'] = {d.code: copy.deepcopy(d.messages_for(o['task']['taskCode'])) for d in self.devices}
        return o

    def setup(self):
        max_t = rows(f"select coalesce(max(id), 0) as max_id from {SC}.tasks")
        self.initial_max_task_id = int(max_t[0]['max_id']) if max_t else 0
        self.ev['initialPendingRows'] = rows(f"select id,task_id,step_status from {SC}.task_step_assignments where step_status in ('PENDING_ASSIGNMENT','EXECUTING') order by id")
        self.ev['initialOccupied'] = rows(f'select agent_code,current_task_id from {SC}.device_agents where current_task_id is not null')
        assert not self.ev['initialOccupied'], 'schema actively occupied'

        # Synthetic test devices:
        # Six standard simulator devices (2 per capability for backup candidate availability)
        specs = [
            ('G175_F022_FLIGHT', 18132, 'FLIGHT_DELAY_BOARD', ['CAP_FLIGHT_UPDATE']),
            ('G151_F014_FLIGHT', 18133, 'FLIGHT_DELAY_BOARD', ['CAP_FLIGHT_UPDATE']),
            ('G145_F013_DISPLAY', 18134, 'SMART_DISPLAY', ['CAP_INFO_DISPLAY']),
            ('G120_NEW', 18135, 'SMART_DISPLAY', ['CAP_INFO_DISPLAY']),
            ('G160_F016_A', 18136, 'MOBILE_ROBOT', ['CAP_NOTIFICATION', 'CAP_NAVIGATION']),
            ('G160_F016_B', 18137, 'MOBILE_ROBOT', ['CAP_NOTIFICATION', 'CAP_NAVIGATION'])
        ]
        self.caps = {}

        # Backup and configure qualified baseline template for FLIGHT_CHANGE_RESPONSE (id=3)
        orig_t3 = rows(f"select id,template_name,task_family,is_preset,input_params,steps,template_version,template_status from {SC}.baseline_templates where id=3")
        self.original_template3 = orig_t3[0] if orig_t3 else None

        t3_inputs = [
            {"name": "flightNumber", "type": "String", "required": True, "defaultValue": "TEST1022"},
            {"name": "updateType", "type": "String", "required": True, "defaultValue": "GATE_CHANGE"},
            {"name": "updateContent", "type": "String", "required": True, "defaultValue": "测试航班登机口变更至F2_TEST_GATE"},
            {"name": "displayDuration", "type": "Integer", "required": True, "defaultValue": "60"},
            {"name": "targetLocation", "type": "String", "required": True, "defaultValue": "F2_TEST_GATE"},
            {"name": "routePreference", "type": "String", "required": True, "defaultValue": "BARRIER_FREE"},
            {"name": "displayContent", "type": "String", "required": True, "defaultValue": "虚构航班登机口及无障碍路径提示，请前往F2_TEST_GATE。"},
            {"name": "contentType", "type": "String", "required": True, "defaultValue": "TEXT"},
            {"name": "notificationType", "type": "String", "required": True, "defaultValue": "BOTH"},
            {"name": "notificationContent", "type": "String", "required": True, "defaultValue": "虚构航班登机口已变更，请改道至新登机口。"},
            {"name": "repeatCount", "type": "Integer", "required": True, "defaultValue": "1"}
        ]
        t3_steps = [
            {
                "stepSeq": 1,
                "capabilityType": "CAP_FLIGHT_UPDATE",
                "stepGoal": "在航延屏发布航班变更信息",
                "paramMapping": [
                    {"target": "flightNumber", "source": "TEMPLATE_INPUT.flightNumber"},
                    {"target": "updateType", "source": "TEMPLATE_INPUT.updateType"},
                    {"target": "updateContent", "source": "TEMPLATE_INPUT.updateContent"},
                    {"target": "displayDuration", "source": "TEMPLATE_INPUT.displayDuration"}
                ],
                "inputParams": {
                    "flightNumber": "TEST1022",
                    "updateType": "GATE_CHANGE",
                    "updateContent": "测试航班登机口变更至F2_TEST_GATE",
                    "displayDuration": 60
                },
                "stepTimeout": 60,
                "precondition": "航延屏在线可用",
                "completionCondition": "publishStatus=SUCCESS",
                "failureHandling": "失败重试一次后候选切换，仍失败转人工处理"
            },
            {
                "stepSeq": 2,
                "capabilityType": "CAP_INFO_DISPLAY",
                "stepGoal": "在智慧航显发布航班登机口变更与路径指引",
                "paramMapping": [
                    {"target": "contentType", "source": "TEMPLATE_INPUT.contentType"},
                    {"target": "contentData", "source": "TEMPLATE_INPUT.displayContent"},
                    {"target": "displayDuration", "source": "TEMPLATE_INPUT.displayDuration"}
                ],
                "inputParams": {
                    "contentType": "TEXT",
                    "contentData": "虚构航班登机口及无障碍路径提示，请前往F2_TEST_GATE。",
                    "displayDuration": 60
                },
                "stepTimeout": 60,
                "precondition": "智慧航显正常在线",
                "completionCondition": "displayStatus=SUCCESS",
                "failureHandling": "失败重试一次后候选切换，仍失败转人工处理"
            },
            {
                "stepSeq": 3,
                "capabilityType": "CAP_NOTIFICATION",
                "stepGoal": "移动机器人进行现场广播通知与提醒",
                "paramMapping": [
                    {"target": "notificationType", "source": "TEMPLATE_INPUT.notificationType"},
                    {"target": "notificationContent", "source": "TEMPLATE_INPUT.notificationContent"},
                    {"target": "repeatCount", "source": "TEMPLATE_INPUT.repeatCount"}
                ],
                "inputParams": {
                    "notificationType": "BOTH",
                    "notificationContent": "虚构航班登机口已变更，请改道至新登机口。",
                    "repeatCount": 1
                },
                "stepTimeout": 60,
                "precondition": "移动服务设备就绪",
                "completionCondition": "notificationStatus=SUCCESS",
                "failureHandling": "失败重试一次后候选切换，仍失败转人工处理"
            },
            {
                "stepSeq": 4,
                "capabilityType": "CAP_NAVIGATION",
                "stepGoal": "移动机器人改道空间意图引导",
                "paramMapping": [
                    {"target": "targetLocation", "source": "TEMPLATE_INPUT.targetLocation"},
                    {"target": "routePreference", "source": "TEMPLATE_INPUT.routePreference"}
                ],
                "inputParams": {
                    "targetLocation": "F2_TEST_GATE",
                    "routePreference": "BARRIER_FREE"
                },
                "stepTimeout": 60,
                "precondition": "移动服务设备就绪",
                "completionCondition": "routeGenerated=true",
                "failureHandling": "失败重试一次后候选切换，仍失败局部重规划"
            }
        ]
        sql(f"update {SC}.baseline_templates set input_params={lit(json.dumps(t3_inputs))}::json, steps={lit(json.dumps(t3_steps))}::json, template_version='V1.2', template_status='ENABLED' where id=3")

        for code, port, typ, caps in specs:
            d = b.Device(code, port)
            d.simtype = typ
            d.healthcaps = caps
            self.devices.append(d)
            body = {
                'deviceCode': code,
                'deviceName': 'F187 ' + typ,
                'deviceTypeCode': 'SIMULATOR',
                'isSimulator': True,
                'simulatedDeviceType': typ,
                'areaCode': 'F2_TEST',
                'positionX': 0,
                'positionY': 0,
                'accessEndpoint': f'http://127.0.0.1:{port}',
                'statusReportInterval': 5,
                'accessCredentialRef': 'synthetic-f026'
            }
            if sql(f"select count(*) from {SC}.devices where device_code={lit(code)}") == '0':
                self.cfg('/devices', 'POST', body)
            old_dev = self.cfg('/devices/' + code)
            if code not in self.original:
                self.original[code] = {
                    'body': {k: old_dev.get(k) for k in ['deviceName', 'areaCode', 'positionX', 'positionY', 'accessEndpoint', 'statusReportInterval', 'remark']},
                    'capabilities': self.cfg('/devices/' + code + '/capabilities')
                }
            self.cfg('/devices/' + code, 'PUT', {k: v for k, v in body.items() if k in self.original[code]['body']})
            d.token = self.cfg(f'/devices/{code}/device-token/rotate', 'POST')['accessToken']
            self.cfg(f'/devices/{code}/connection-test', 'POST')
            self.cfg(f'/devices/{code}/status', 'POST', {'status': 'ACTIVE'})
            self.cfg(f'/devices/{code}/connection-test', 'POST')
            d.agent = next(a['agentId'] for a in self.cfg('/device-agents?page=1&size=100')['content'] if a['deviceCode'] == code)
            d.heartbeat()
            for cap in caps:
                self.cfg(f'/devices/{code}/capabilities/{cap}/test', 'POST')
                self.cfg(f'/devices/{code}/capabilities/{cap}/status', 'POST', {'status': 'ENABLED'})
            self.caps.update({c['capabilityType']: c for c in self.cfg('/devices/' + code + '/capabilities') if c['capabilityType'] in caps})
            threading.Thread(target=d.loop, daemon=True).start()

        self.record('resources-ready', {
            'capabilities': self.caps,
            'health': b.l.request('http://127.0.0.1:18129/actuator/health')
        }, {'sixDevicesActive': len(self.devices) == 6})

    def config_case(self, marker, **kwargs):
        self.cases[marker] = kwargs
        CONFIG.write_text(json.dumps(self.cases, ensure_ascii=False, indent=2), encoding='utf-8')

    def submit(self, name, goal, scene=None, **kwargs):
        marker = 'F187_' + name.upper().replace('-', '_')
        self.config_case(marker, **kwargs)
        if scene is not None:
            scene_params = dict(scene)
        else:
            scene_params = {
                'eventSource': 'MANUAL_FORM',
                'flightNumber': 'CA1234',
                'changeType': 'GATE_CHANGE',
                'originalTime': '2026-11-10T10:00:00',
                'newGate': 'F2_TEST_GATE',
                'changeDescription': '虚构航班CA1234登机口变更至F2_TEST_GATE',
                'updateType': 'GATE_CHANGE',
                'updateContent': '虚构航班CA1234登机口变更至F2_TEST_GATE',
                'displayDuration': 60,
                'targetLocation': 'F2_TEST_GATE'
            }
        body = {
            'taskGoal': f"{marker} {goal}",
            'taskFamily': 'FLIGHT_CHANGE_RESPONSE',
            'sceneParams': scene_params
        }
        resp = raw(self.op, '/tasks', body)
        tid = None
        if resp.get('http') in (200, 201):
            tid = resp.get('body', {}).get('data', {}).get('id')
        if tid is None:
            tid_str = sql(f"select id from {SC}.tasks where task_goal={lit(body['taskGoal'])} order by id desc limit 1")
            if tid_str:
                tid = int(tid_str)
        if tid is not None:
            self.tasks.append(tid)
        return self.record(name, {'taskId': tid, 'request': body, 'response': resp})

    def submit_event(self, name, event_body, **kwargs):
        marker = 'F187_EVT_' + name.upper().replace('-', '_')
        self.config_case(marker, **kwargs)
        # Note: flightChangeEvent creates a taskGoal containing request fields.
        resp = raw(self.op, '/tasks/flight-change-event', event_body)
        tid = None
        if resp.get('http') in (200, 201):
            tid = resp.get('body', {}).get('data', {}).get('id')
        if tid is None and resp.get('http') in (200, 201):
            tid_str = sql(f"select id from {SC}.tasks where task_family='FLIGHT_CHANGE_RESPONSE' order by id desc limit 1")
            if tid_str:
                tid = int(tid_str)
        if tid is not None:
            self.tasks.append(tid)
        return self.record(name, {'taskId': tid, 'request': event_body, 'response': resp})

    def drive(self, row, fail_caps=None, fail_count=0, max_time=35):
        tid = row['taskId']
        if tid is None:
            return None
        code = self.op(f'/tasks/{tid}')['taskCode']
        seen = set()
        actions = []
        end = time.monotonic() + max_time
        remaining_failures = fail_count

        while time.monotonic() < end:
            t = self.op(f'/tasks/{tid}')
            status = t['status']
            if status in ['COMPLETED', 'FAILED', 'PENDING_MANUAL', 'MANUAL_TERMINATED']:
                break
            did = False
            for d in self.devices:
                for envelope in list(d.messages_for(code)):
                    msg = envelope['message']
                    key = (msg['commandId'], msg['commandType'], msg.get('attemptNo'))
                    if key in seen or msg['commandType'] not in ['TASK_ACCEPT', 'EXECUTE_CAPABILITY']:
                        continue
                    seen.add(key)
                    did = True
                    with d.guard:
                        if msg['commandType'] == 'TASK_ACCEPT':
                            d.state['workStatus'] = 'BUSY'
                            ret = d.report('TASK_RESPONSE', {'commandId': msg['commandId'], 'accepted': True})
                        else:
                            cap = msg.get('capabilityType')
                            should_fail = (fail_caps and cap in fail_caps and remaining_failures > 0)
                            if should_fail:
                                remaining_failures -= 1
                            output = {
                                'publishStatus': 'SUCCESS',
                                'publishTime': now(),
                                'displayStatus': 'SUCCESS',
                                'notificationStatus': 'SUCCESS',
                                'actualRepeatCount': 1,
                                'routeGenerated': True,
                                'arrivalStatus': 'ARRIVED',
                                'actualDistance': 10,
                                'actualDuration': 10
                            }
                            ret = d.report('EXECUTION_FEEDBACK', {
                                'commandId': msg['commandId'],
                                'attemptNo': msg['attemptNo'],
                                'executionResult': 'FAILED' if should_fail else 'SUCCESS',
                                **({'reasonCode': 'ERR_F187_CHANNEL_FAILED'} if should_fail else {}),
                                'outputParams': {} if should_fail else output
                            })
                            d.state['workStatus'] = 'IDLE'
                    actions.append({'deviceCode': d.code, 'message': msg, 'response': ret})
                    row['actions'] = actions
                    self.save()
                    time.sleep(0.15)
            if not did:
                time.sleep(0.2)

        row['after'] = self.observe(tid)
        self.save()
        return row['after']

    def terminate(self, tid):
        try:
            status = self.op(f'/tasks/{tid}')['status']
            if status not in ['COMPLETED', 'FAILED', 'MANUAL_TERMINATED']:
                raw(self.op, f'/tasks/{tid}/terminate', {'confirmed': True, 'reason': 'Synthetic F026 cleanup'})
        except Exception:
            pass
        for d in self.devices:
            with d.guard:
                d.state.update(onlineStatus='ONLINE', workStatus='IDLE')
                d.heartbeat()

    def cleanup(self):
        new_tasks = [int(r['id']) for r in rows(f"select id from {SC}.tasks where id > {self.initial_max_task_id}")]
        all_tasks = sorted(set(self.tasks) | set(new_tasks))
        for tid in all_tasks:
            self.terminate(tid)
        sql(f"update {SC}.task_step_assignments set step_status='SKIPPED' where task_id > {self.initial_max_task_id} and step_status in ('PENDING_ASSIGNMENT','EXECUTING')")
        for d in self.devices:
            d.paused = True
            d.stop = True
            try:
                self.cfg(f'/devices/{d.code}/status', 'POST', {'status': 'INACTIVE'})
                self.cfg('/devices/' + d.code, 'PUT', self.original[d.code]['body'])
                for c in self.original[d.code]['capabilities']:
                    sql(f"update {SC}.device_capabilities set capability_status={lit(c['capabilityStatus'])} where device_id=(select id from {SC}.devices where device_code={lit(d.code)}) and capability_code={lit(c['capabilityCode'])}")
            except Exception:
                pass
        if hasattr(self, 'original_template3') and self.original_template3:
            sql(f"update {SC}.baseline_templates set input_params={lit(json.dumps(self.original_template3['input_params']))}::json, steps={lit(json.dumps(self.original_template3['steps']))}::json, template_version={lit(self.original_template3['template_version'])}, template_status={lit(self.original_template3['template_status'])} where id=3")
        final_pending = rows(f"select id,task_id,step_status from {SC}.task_step_assignments where step_status in ('PENDING_ASSIGNMENT','EXECUTING') order by id")
        occupied = rows(f"select agent_code,current_task_id from {SC}.device_agents where current_task_id is not null")
        return self.record('cleanup', {
            'finalPendingRows': final_pending,
            'occupied': occupied
        }, {
            'historicalPendingUnchanged': final_pending == self.ev['initialPendingRows'],
            'noOccupied': len(occupied) == 0
        })

print("Round F026 loaded successfully")
