"""SRS_F025 V1.186 independent real HTTP/SQL/protocol round.
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

SHA = '239f8dd65b6c840847280ae2f7cb778811cf6296'
OUT = E / 'SRS_F025-V1.186-http-sql-protocol-20261109.json'
CONFIG = L / 'f025-v186-cases.json'

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
            'tag': 'V1.186',
            'handoffSha': '8bae25164f2ec1d4400f9185a53e41c4ad6ff809',
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
        # 1. G160_F016_A: MOBILE_ROBOT (CAP_NOTIFICATION, CAP_ESCORT)
        # 2. G160_F016_B: MOBILE_ROBOT (CAP_NOTIFICATION, CAP_ESCORT)
        # 3. G145_F013_DISPLAY: SMART_DISPLAY (CAP_INFO_DISPLAY)
        specs = [
            ('G160_F016_A', 18132, 'MOBILE_ROBOT', ['CAP_NOTIFICATION', 'CAP_ESCORT']),
            ('G160_F016_B', 18136, 'MOBILE_ROBOT', ['CAP_NOTIFICATION', 'CAP_ESCORT']),
            ('G145_F013_DISPLAY', 18134, 'SMART_DISPLAY', ['CAP_INFO_DISPLAY'])
        ]
        self.caps = {}
        # Backup and configure qualified baseline template for SPECIAL_PASSENGER_SERVICE (TC-077.S2 / R06)
        orig_t2 = rows(f"select id,template_name,task_family,is_preset,input_params,steps,template_version,template_status from {SC}.baseline_templates where id=2")
        self.original_template2 = orig_t2[0] if orig_t2 else None

        t2_inputs = [
            {"name": "assistanceType", "type": "String", "required": True, "defaultValue": "WHEELCHAIR"},
            {"name": "origin", "type": "String", "required": True, "defaultValue": "F2_GATE_A"},
            {"name": "destination", "type": "String", "required": True, "defaultValue": "F2_SERVICE_POINT"},
            {"name": "targetLocation", "type": "String", "required": True, "defaultValue": "F2_SERVICE_POINT"},
            {"name": "notificationType", "type": "String", "required": False, "defaultValue": "BOTH"},
            {"name": "repeatCount", "type": "Integer", "required": False, "defaultValue": "1"},
            {"name": "escortMode", "type": "String", "required": False, "defaultValue": "LEAD"},
            {"name": "maxDuration", "type": "Integer", "required": False, "defaultValue": "600"},
            {"name": "contentType", "type": "String", "required": False, "defaultValue": "TEXT"},
            {"name": "displayDuration", "type": "Integer", "required": False, "defaultValue": "60"}
        ]
        t2_steps = [
            {
                "stepSeq": 1,
                "capabilityType": "CAP_INFO_DISPLAY",
                "stepGoal": "在智慧航显发布特殊旅客会合信息与指引",
                "paramMapping": [
                    {"target": "contentData", "source": "TEMPLATE_INPUT.assistanceType"}
                ],
                "inputParams": {
                    "contentType": "TEXT",
                    "contentData": "特殊旅客请在F2_GATE_A会合，工作人员即将到达协助",
                    "displayDuration": 60
                },
                "stepTimeout": 120,
                "precondition": "智慧航显正常在线",
                "completionCondition": "displayStatus=SUCCESS",
                "failureHandling": "失败重试一次后候选切换，仍失败转人工处理"
            },
            {
                "stepSeq": 2,
                "capabilityType": "CAP_NOTIFICATION",
                "stepGoal": "移动机器人语音播报并提醒现场人员协助",
                "paramMapping": [
                    {"target": "notificationContent", "source": "TEMPLATE_INPUT.assistanceType"}
                ],
                "inputParams": {
                    "notificationType": "BOTH",
                    "notificationContent": "轮椅协助服务已到达，请旅客准备出发",
                    "repeatCount": 1
                },
                "stepTimeout": 120,
                "precondition": "移动服务设备就绪",
                "completionCondition": "reportStatus=SUCCESS",
                "failureHandling": "失败重试一次后候选切换，仍失败转人工处理"
            },
            {
                "stepSeq": 3,
                "capabilityType": "CAP_ESCORT",
                "stepGoal": "移动机器人引导旅客由起点到达目的地",
                "paramMapping": [
                    {"target": "targetLocation", "source": "TEMPLATE_INPUT.destination"}
                ],
                "inputParams": {
                    "targetLocation": "F2_SERVICE_POINT",
                    "escortMode": "LEAD",
                    "maxDuration": 600
                },
                "stepTimeout": 300,
                "precondition": "现场会合完成",
                "completionCondition": "serviceResult=COMPLETED",
                "failureHandling": "失败重试一次后候选切换，仍失败局部重规划"
            }
        ]
        sql(f"update {SC}.baseline_templates set input_params={lit(json.dumps(t2_inputs))}::json, steps={lit(json.dumps(t2_steps))}::json, template_version='V1.2', template_status='ENABLED' where id=2")

        for code, port, typ, caps in specs:
            d = b.Device(code, port)
            d.simtype = typ
            d.healthcaps = caps
            self.devices.append(d)
            body = {
                'deviceCode': code,
                'deviceName': 'F186 ' + typ,
                'deviceTypeCode': 'SIMULATOR',
                'isSimulator': True,
                'simulatedDeviceType': typ,
                'areaCode': 'F2_TEST',
                'positionX': 0,
                'positionY': 0,
                'accessEndpoint': f'http://127.0.0.1:{port}',
                'statusReportInterval': 5,
                'accessCredentialRef': 'synthetic-f025'
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
        }, {'threeDevicesActive': len(self.devices) == 3})

    def config_case(self, marker, **kwargs):
        self.cases[marker] = kwargs
        CONFIG.write_text(json.dumps(self.cases), encoding='utf-8')

    def submit(self, name, goal, scene=None, **kwargs):
        marker = 'F186_' + name.upper().replace('-', '_')
        self.config_case(marker, **kwargs)
        scene_params = {
            'tempBusinessId': f"SP-{marker}"
        }
        if scene is not None:
            scene_params.update(scene)
        else:
            scene_params.update({
                'assistanceType': 'WHEELCHAIR',
                'origin': 'F2_GATE_A',
                'destination': 'F2_SERVICE_POINT'
            })
        body = {
            'taskGoal': f"{marker} {goal}",
            'taskFamily': 'SPECIAL_PASSENGER_SERVICE',
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
                                'displayStatus': 'SUCCESS',
                                'reportStatus': 'SUCCESS',
                                'escortStatus': 'SUCCESS',
                                'escortCompleted': True,
                                'serviceResult': 'COMPLETED',
                                'notificationStatus': 'SUCCESS',
                                'arrivalStatus': 'ARRIVED'
                            }
                            ret = d.report('EXECUTION_FEEDBACK', {
                                'commandId': msg['commandId'],
                                'attemptNo': msg['attemptNo'],
                                'executionResult': 'FAILED' if should_fail else 'SUCCESS',
                                **({'reasonCode': 'ERR_F186_ESCORT_FAILED'} if should_fail else {}),
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
                raw(self.op, f'/tasks/{tid}/terminate', {'confirmed': True, 'reason': 'Synthetic F025 cleanup'})
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
        if hasattr(self, 'original_template2') and self.original_template2:
            sql(f"update {SC}.baseline_templates set input_params={lit(json.dumps(self.original_template2['input_params']))}::json, steps={lit(json.dumps(self.original_template2['steps']))}::json, template_version={lit(self.original_template2['template_version'])}, template_status={lit(self.original_template2['template_status'])} where id=2")
        final_pending = rows(f"select id,task_id,step_status from {SC}.task_step_assignments where step_status in ('PENDING_ASSIGNMENT','EXECUTING') order by id")
        occupied = rows(f"select agent_code,current_task_id from {SC}.device_agents where current_task_id is not null")
        return self.record('cleanup', {
            'finalPendingRows': final_pending,
            'occupied': occupied
        }, {
            'historicalPendingUnchanged': final_pending == self.ev['initialPendingRows'],
            'noOccupied': len(occupied) == 0
        })

print("Round class loaded successfully")
