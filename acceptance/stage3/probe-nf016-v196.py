"""SRS_NF016 V1.196 independent live probe (GPT retest, V2.4).

Isolation: backend jar on 127.0.0.1:18131, dedicated schema tip_gpt_nf016_v196_20261111, Redis db 11,
PostgreSQL reached ONLY through a local TCP proxy (127.0.0.1:15516) owned by this script. The database
"outage" for TC-002.S4 is closing that proxy; recovery is reopening it. Shared PostgreSQL, ports
8080/5173/8091-8096 and other worktrees are never touched.

Covers: SRS_NF016.R01; TC-002.S1~S4 (live); audit read-only tamper resistance with forged/real admin
identities (PUT/DELETE/PATCH, method override), SHA-256 fingerprints of audit tables before/after,
long-input audit completeness (no truncation, structure intact), credential-free audit details.
Credentials come from env (TIP_ADMIN_PASSWORD etc.) with local demo-fixture defaults; never written to evidence.
"""
import base64, hashlib, importlib.util, json, os, re, socket, subprocess, sys, threading, time
import urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
R = Path(__file__).resolve().parents[2]
old = R.parent / 'tip'
L = R / '.local-test'; L.mkdir(exist_ok=True)
E = R / 'acceptance/stage3/evidence'; E.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location('db', old / 'scripts/isolated-reset-db.py')
db = importlib.util.module_from_spec(spec); spec.loader.exec_module(db)

SHA = 'b57c66f580cd74581c890b5739796a746fd2ad5c'; TAG = 'V1.196'
SC = 'tip_gpt_nf016_v196_20261111'; PORT = 18131; PROXY_PORT = 15516; REDIS_DB = '11'
assert PORT not in {8080, 5173, *range(8091, 8097)} and SC != 'public'
BASE = f'http://127.0.0.1:{PORT}/api/v1'
STAMP = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
OUT = E / f'SRS_NF016-V1.196-protocol-db-evidence-{STAMP}.json'
ADMIN_PW = os.environ.get('TIP_ADMIN_PASSWORD', 'cares0126')
CFG_PW = os.environ.get('TIP_CONFIG_PASSWORD', '12345678')
OP_PW = os.environ.get('TIP_OPERATOR_PASSWORD', '12345678')
TEST_PW = 'Nf016#Pass2026'; WRONG_PW = 'Wrong#Pass9999'
SECRETS = [ADMIN_PW, CFG_PW, OP_PW, TEST_PW, WRONG_PW]


# ---------------------------------------------------------------- infrastructure
class Proxy:
    def __init__(self, host, port, listen):
        self.target, self.listen, self.srv, self.conns, self.run = (host, port), listen, None, [], False

    def start(self):
        self.srv = socket.socket(); self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(('127.0.0.1', self.listen)); self.srv.listen(64); self.run = True
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self):
        while self.run:
            try:
                c, _ = self.srv.accept(); u = socket.create_connection(self.target, timeout=5)
            except OSError:
                break
            self.conns += [c, u]
            for a, b in ((c, u), (u, c)):
                threading.Thread(target=self._pipe, args=(a, b), daemon=True).start()

    @staticmethod
    def _pipe(a, b):
        try:
            while (d := a.recv(65536)):
                b.sendall(d)
        except OSError:
            pass
        for s in (a, b):
            try: s.close()
            except OSError: pass

    def stop(self):
        self.run = False
        for s in [self.srv, *self.conns]:
            try: s.close()
            except OSError: pass
        self.conns = []


def sql(q):
    full = f'SET search_path TO {SC}, public;\n' + q.strip().rstrip(';') + ';\n'
    r = subprocess.run(db.common + ['-d', db.shared, '-At'], input=full, capture_output=True,
                       env=dict(db.variables, PGCLIENTENCODING='UTF8'), encoding='utf-8', errors='replace')
    if r.returncode:
        raise RuntimeError('psql failed: ' + r.stderr.strip()[-300:])
    return '\n'.join(x for x in r.stdout.strip().splitlines() if x.strip() and x.strip() != 'SET')


def http(method, path, data=None, token=None, headers=None, raw_body=None, timeout=30):
    url = path if path.startswith('http') else BASE + path
    h = {'Content-Type': 'application/json'}
    if token: h['Authorization'] = f'Bearer {token}'
    if headers: h.update(headers)
    body = raw_body if raw_body is not None else (json.dumps(data, ensure_ascii=False).encode() if data is not None else None)
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            txt = r.read().decode('utf-8', 'replace'); hdr = dict(r.headers)
            return r.status, (json.loads(txt) if txt.strip() else {}), hdr
    except urllib.error.HTTPError as ex:
        txt = ex.read().decode('utf-8', 'replace'); hdr = dict(ex.headers)
        try: js = json.loads(txt)
        except Exception: js = {'raw': txt[:300]}
        return ex.code, js, hdr


def login(u, p):
    s, b, _ = http('POST', '/auth/login', {'username': u, 'password': p})
    tok = (b.get('data') or {}).get('token') if s == 200 and b.get('code') == 200 else None
    return s, b, tok


def fp(table, max_id=None):
    where = f'WHERE id <= {int(max_id)}' if max_id is not None else ''
    row = sql(f"SELECT coalesce(encode(sha256(convert_to(string_agg(t::text, E'\\n' ORDER BY id), 'UTF8')),'hex'),'EMPTY'), "
              f"count(*), coalesce(max(id),0) FROM {table} t {where}")
    h, c, m = row.split('|')
    return {'sha256': h, 'rows': int(c), 'maxId': int(m)}


def user_state(name):
    r = sql(f"SELECT status, failed_login_attempts, coalesce(locked_at::text,'') FROM users WHERE username='{name}'")
    s, n, la = r.split('|')
    return {'status': s, 'failedLoginAttempts': int(n), 'lockedAtSet': bool(la)}


CHECKS = []
def check(cid, desc, ok, **obs):
    CHECKS.append({'id': cid, 'desc': desc, 'result': 'P' if ok else 'F', **obs})
    print(('PASS ' if ok else 'FAIL ') + cid + ' ' + desc)
    return ok


def kill_tree(p):
    subprocess.run(['taskkill', '/PID', str(p.pid), '/T', '/F'], capture_output=True)


def start_backend():
    db.sql(db.shared, f'CREATE SCHEMA IF NOT EXISTS {SC}')
    for port in (PORT,):  # PROXY_PORT is already bound by our own proxy (bind would have failed if busy)
        with socket.socket() as s:
            assert s.connect_ex(('127.0.0.1', port)) != 0, f'port {port} busy'
    env = db.variables.copy()
    env.update(
        SPRING_DATASOURCE_URL=f"jdbc:postgresql://127.0.0.1:{PROXY_PORT}/{db.shared}?currentSchema={SC}&ApplicationName=GPT_NF016_V196",
        SPRING_FLYWAY_SCHEMAS=SC, SERVER_ADDRESS='127.0.0.1', SERVER_PORT=str(PORT),
        SPRING_DATA_REDIS_DATABASE=REDIS_DB, SPRING_DATASOURCE_HIKARI_CONNECTION_TIMEOUT='3000',
        SPRING_DATASOURCE_HIKARI_MINIMUM_IDLE='1', SPRING_DATASOURCE_HIKARI_MAXIMUM_POOL_SIZE='5',
        PLANNING_MODEL_PROVIDER='external', PLANNING_MODEL_ENDPOINT='http://127.0.0.1:18117',
        PLANNING_MODEL_API_KEY='local-fixture')
    log = (L / 'backend-nf016-v196.log').open('wb', buffering=0)
    p = subprocess.Popen(['java', '-Xms32m', '-Xmx384m', '-XX:+UseSerialGC', '-jar',
                          str(R / 'backend/target/airport-ai-app-1.0.0.jar')], cwd=R, env=env, stdout=log,
                         stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008)
    (L / 'runtime-nf016-v196.json').write_text(json.dumps({'pid': p.pid, 'port': PORT, 'schema': SC, 'proxy': PROXY_PORT}))
    for _ in range(180):
        if p.poll() is not None: raise SystemExit(f'backend exited {p.returncode}')
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/actuator/health', timeout=2) as r:
                if r.status == 200:
                    # Seed preset accounts from GPT's own isolated baseline schema (never touches public)
                    sql("UPDATE users u SET password_hash = s.password_hash, status='ACTIVE', failed_login_attempts=0, "
                        "locked_at=NULL, locked_reason=NULL FROM tip_gpt_f006_v118_20261030.users s "
                        "WHERE u.username='admin' AND s.username='admin';\n"
                        "INSERT INTO users (username, password_hash, real_name, role, contact, status, failed_login_attempts) "
                        "SELECT username, password_hash, real_name, role, contact, 'ACTIVE', 0 "
                        "FROM tip_gpt_f006_v118_20261030.users WHERE username IN ('set','oprator') "
                        "ON CONFLICT (username) DO UPDATE SET password_hash=EXCLUDED.password_hash, "
                        "status='ACTIVE', failed_login_attempts=0, locked_at=NULL, locked_reason=NULL;")
                    return p
        except Exception:
            time.sleep(1)
    kill_tree(p); raise SystemExit('backend start timeout')


def no_secret(text):
    return not any(s in (text or '') for s in SECRETS)


# ---------------------------------------------------------------- tests
def run():
    ev = {'requirement': 'SRS_NF016', 'rule': 'SRS_NF016.R01', 'productSha': SHA, 'productTag': TAG,
          'schema': SC, 'backendPort': PORT, 'dbProxyPort': PROXY_PORT, 'redisDb': REDIS_DB,
          'observedAtUtc': STAMP, 'tester': 'GPT (ai/gpt-test, tip-gpt-f013)', 'checks': CHECKS}

    s, b, admin = login('admin', ADMIN_PW); _, _, cfg = login('set', CFG_PW); _, _, op = login('oprator', OP_PW)
    assert admin and cfg and op, 'preset logins failed'
    admin_id = int(sql("SELECT id FROM users WHERE username='admin'"))

    # ---------- fixtures: accounts A/B/C (C inactive)
    ts = STAMP[-7:-1]
    A, B, C = f'nf016a{ts}', f'nf016b{ts}', f'nf016c{ts}'
    ids = {}
    for n in (A, B, C):
        st, bd, _ = http('POST', '/users', {'username': n, 'password': TEST_PW, 'realName': '审计复测', 'role': 'OPERATOR',
                                             'contact': 'nf016@example.test'}, admin)
        assert st == 200, (n, st, bd); ids[n] = bd['data']['id']
    st, bd, _ = http('POST', f'/users/{ids[C]}/status', {'status': 'INACTIVE'}, admin); assert st == 200, bd
    log0 = int(sql('SELECT coalesce(max(id),0) FROM operation_logs'))
    ev['fixtures'] = {'accounts': {'A': A, 'B': B, 'C_inactive': C}, 'operationLogMaxIdBeforeTc002': log0}

    # ---------- TC-002.S1
    unk = login(f'nf016nobody{ts}', WRONG_PW); ina = login(C, TEST_PW); bw = login(B, WRONG_PW)
    msgs = [x[1].get('message') for x in (unk, ina, bw)]
    s1 = {'responses': [{'case': c, 'http': x[0], 'code': x[1].get('code'), 'message': x[1].get('message'), 'token': bool(x[2])}
                        for c, x in zip(('unknown', 'inactive', 'B_wrong'), (unk, ina, bw))],
          'A': user_state(A), 'B': user_state(B)}
    logs = sql(f"SELECT username, operation_type, operation_result FROM operation_logs WHERE id > {log0} AND operation_type='LOGIN' ORDER BY id")
    s1['loginFailedRows'] = logs.splitlines()
    check('TC-002.S1', '不存在/停用/B错密统一“账号或密码错误”、无会话、留痕且不污染A计数',
          all(m == '账号或密码错误' for m in msgs) and not any(x[2] for x in (unk, ina, bw))
          and s1['A']['failedLoginAttempts'] == 0 and s1['B']['failedLoginAttempts'] == 1
          and all(f'{u}|LOGIN|FAILED' in logs for u in (f'nf016nobody{ts}', C, B)), **s1)

    # ---------- TC-002.S2
    seq = []
    for i in range(1, 4):
        r = login(A, WRONG_PW); seq.append({'attempt': i, 'http': r[0], 'code': r[1].get('code'), 'message': r[1].get('message'),
                                           'token': bool(r[2]), 'state': user_state(A)})
    lc = login(A, TEST_PW)
    seq.append({'attempt': 'correct-while-locked', 'http': lc[0], 'code': lc[1].get('code'), 'message': lc[1].get('message'),
                'token': bool(lc[2]), 'state': user_state(A)})
    check('TC-002.S2', '前2次未锁定，第3次锁定；锁定期间正确密码仍统一失败且无会话',
          seq[0]['state']['status'] == 'ACTIVE' and seq[0]['state']['failedLoginAttempts'] == 1
          and seq[1]['state']['status'] == 'ACTIVE' and seq[1]['state']['failedLoginAttempts'] == 2
          and seq[2]['state']['status'] == 'LOCKED' and seq[2]['state']['lockedAtSet']
          and all(x['message'] == '账号或密码错误' and not x['token'] for x in seq) and seq[3]['state']['status'] == 'LOCKED',
          sequence=seq)

    # ---------- TC-002.S3 (+ non-admin cannot unlock)
    nu_op = http('POST', f'/users/{ids[A]}/unlock', None, op)[0]; nu_cfg = http('POST', f'/users/{ids[A]}/unlock', None, cfg)[0]
    still_locked = user_state(A)['status'] == 'LOCKED'
    un = http('POST', f'/users/{ids[A]}/unlock', None, admin)
    after_unlock = user_state(A)
    w2 = [login(A, WRONG_PW) for _ in range(2)]; after_w2 = user_state(A)
    ok_login = login(A, TEST_PW); after_ok = user_state(A)
    w1 = login(A, WRONG_PW); after_w1 = user_state(A)
    trail = sql(f"SELECT id, username, operation_type, operation_target, operation_result, created_at, coalesce(source_ip,''), "
                f"coalesce(detail::text,'') FROM operation_logs WHERE id > {log0} AND (username='{A}' OR operation_target='{A}') ORDER BY id").splitlines()
    rows = [dict(zip(['id', 'username', 'type', 'target', 'result', 'createdAt', 'sourceIp', 'detail'], r.split('|', 7))) for r in trail]
    types = [(r['type'], r['result']) for r in rows]
    lock_rows = [r for r in rows if r['type'] == 'ACCOUNT_LOCKED']
    unlock_rows = [r for r in rows if r['type'] == 'MANUAL_HANDLING']
    trail_ok = (types.count(('LOGIN', 'FAILED')) == 7 and len(lock_rows) == 1 and len(unlock_rows) == 1
                and ('LOGIN', 'SUCCESS') in types and unlock_rows[0]['username'] == 'admin' and unlock_rows[0]['target'] == A
                and all(r['createdAt'] and r['result'] for r in rows) and all(no_secret(r['detail']) for r in rows))
    ld = json.loads(lock_rows[0]['detail']) if lock_rows else {}; ud = json.loads(unlock_rows[0]['detail']) if unlock_rows else {}
    check('TC-002.S3', '仅系统管理员可解锁；解锁清零，2错后正确登录再清零，后续1错不锁；失败/锁定/解锁全程留痕且无密码原值',
          nu_op == 403 and nu_cfg == 403 and still_locked and un[0] == 200
          and after_unlock == {'status': 'ACTIVE', 'failedLoginAttempts': 0, 'lockedAtSet': False}
          and after_w2['failedLoginAttempts'] == 2 and after_w2['status'] == 'ACTIVE' and ok_login[2]
          and after_ok['failedLoginAttempts'] == 0 and after_w1 == {'status': 'ACTIVE', 'failedLoginAttempts': 1, 'lockedAtSet': False}
          and trail_ok and ld.get('action') == 'LOCK' and ld.get('after', {}).get('status') == 'LOCKED'
          and ud.get('action') == 'UNLOCK' and ud.get('before', {}).get('status') == 'LOCKED' and ud.get('after', {}).get('status') == 'ACTIVE',
          nonAdminUnlockHttp={'operator': nu_op, 'configAdmin': nu_cfg}, adminUnlockHttp=un[0],
          states={'afterUnlock': after_unlock, 'after2Wrong': after_w2, 'afterCorrect': after_ok, 'after1Wrong': after_w1},
          correctLoginTokenIssued=bool(ok_login[2]), trailTypes=types, lockDetail=ld, unlockDetail=ud,
          trailRowsWithoutPasswordValue=all(no_secret(r['detail']) for r in rows))

    # ---------- task + event fixture for event read-only checks
    # Ensure at least one ENABLED+ONLINE device agent exists so POST /tasks creates a task and GOAL_SUBMITTED event
    sql(f"INSERT INTO devices (device_code, device_name, device_type_code, is_simulator, area_code, position_x, position_y, "
        f"access_endpoint, access_credential_ref, device_status, connection_test_status) "
        f"VALUES ('NF016_AGT_DEV_{ts}', 'NF016在线夹具设备', 'MOBILE_ROBOT', FALSE, 'F2_TEST', 10, 20, "
        f"'http://127.0.0.1:18099/agt', 'cred-fixture', 'ACTIVE', 'PASSED') ON CONFLICT DO NOTHING")
    fx_dev_id = int(sql(f"SELECT id FROM devices WHERE device_code='NF016_AGT_DEV_{ts}'"))
    sql(f"INSERT INTO device_agents (agent_code, device_id, agent_status, online_status, work_status) "
        f"VALUES ('AGT_NF016_{ts}', {fx_dev_id}, 'ENABLED', 'ONLINE', 'IDLE') ON CONFLICT DO NOTHING")
    fx_agent_id = int(sql(f"SELECT id FROM device_agents WHERE agent_code='AGT_NF016_{ts}'"))
    sql(f"INSERT INTO device_events (device_agent_id, event_type, trigger, detail_summary) "
        f"VALUES ({fx_agent_id}, 'AGENT_REGISTERED', 'SYSTEM', 'NF016设备事件只读指纹夹具')")
    st, bd, _ = http('POST', '/tasks', {'taskGoal': 'NF016审计复测：引导旅客前往二号登机口'}, op)
    task_id = int(sql('SELECT coalesce(max(id),0) FROM tasks') or 0) or None
    ev_row = sql(f'SELECT id FROM task_events WHERE task_id={int(task_id)} ORDER BY id LIMIT 1') if task_id else ''
    event_id = int(ev_row) if ev_row else None
    ev['taskEventFixture'] = {'submitHttp': st, 'taskId': task_id, 'eventId': event_id, 'deviceAgentId': fx_agent_id}

    # ---------- read-only visibility on GET /operation-logs/{id}
    admin_log = int(sql("SELECT max(id) FROM operation_logs WHERE username='admin'"))
    op_log = int(sql("SELECT max(id) FROM operation_logs WHERE username='oprator'"))
    pre_ad = int(sql("SELECT count(*) FROM operation_logs WHERE operation_type='ACCESS_DENIED' AND username='oprator'"))
    g_admin_any = http('GET', f'/operation-logs/{op_log}', None, admin)[0]
    g_op_own = http('GET', f'/operation-logs/{op_log}', None, op)[0]
    g_op_other = http('GET', f'/operation-logs/{admin_log}', None, op)
    g_missing = http('GET', '/operation-logs/999999999', None, admin)[0]
    post_ad = int(sql("SELECT count(*) FROM operation_logs WHERE operation_type='ACCESS_DENIED' AND username='oprator'"))
    check('NF016.READ-VISIBILITY', '单条审计只读查询：管理员可查任意、非管理员仅本人、越权403并留ACCESS_DENIED、不存在404',
          g_admin_any == 200 and g_op_own == 200 and g_op_other[0] == 403 and g_op_other[1].get('code') == 2003
          and g_missing == 404 and post_ad == pre_ad + 1,
          adminGetOther=g_admin_any, operatorGetOwn=g_op_own, operatorGetOther=g_op_other[0], missing=g_missing,
          accessDeniedRowsAdded=post_ad - pre_ad)

    # ---------- tamper attempts + SHA-256 fingerprints
    tables = ['operation_logs', 'task_events', 'device_events']
    before_full = {t: fp(t) for t in tables}
    target_row_before = sql(f'SELECT t::text FROM operation_logs t WHERE id={admin_log}')
    forged_jwt = '.'.join(base64.urlsafe_b64encode(json.dumps(x).encode()).decode().rstrip('=') for x in (
        {'alg': 'none', 'typ': 'JWT'}, {'sub': 'admin', 'role': 'SYSTEM_ADMIN', 'roles': ['ROLE_SYSTEM_ADMIN']})) + '.'
    spoof = {'X-Role': 'SYSTEM_ADMIN', 'X-User-Role': 'ROLE_SYSTEM_ADMIN', 'X-Forwarded-User': 'admin',
             'X-Auth-User': 'admin', 'X-Username': 'admin', 'X-User-Id': str(admin_id)}
    identities = {
        'realAdminToken': {'token': admin, 'headers': {}},
        'operatorTokenWithSpoofedAdminHeaders': {'token': op, 'headers': spoof},
        'forgedAlgNoneAdminJwt': {'token': forged_jwt, 'headers': spoof},
        'forgedRandomBearer': {'token': hashlib.sha256(b'nf016-forged').hexdigest()[:32], 'headers': spoof},
        'tamperedAdminToken': {'token': admin[:-6] + ('abcdef' if not admin.endswith('abcdef') else '123456'), 'headers': {}},
        'noTokenSpoofedHeadersAndCookie': {'token': None, 'headers': {**spoof, 'Cookie': 'role=SYSTEM_ADMIN; user=admin'}},
    }
    tamper_body = {'id': admin_log, 'username': 'hacker', 'operationType': 'LOGIN', 'operationResult': 'SUCCESS',
                   'operationTarget': 'tampered', 'detail': {'tampered': True}}
    paths = ['/operation-logs', f'/operation-logs/{admin_log}', '/operation-logs/999999999']
    if task_id and event_id:
        paths += [f'/tasks/{task_id}/events', f'/tasks/{task_id}/events/{event_id}']
    attempts = []
    for iname, ident in identities.items():
        for path in paths:
            for m in ('PUT', 'DELETE', 'PATCH'):
                st, bd, hd = http(m, path, tamper_body, ident['token'], ident['headers'])
                allow = hd.get('Allow') or hd.get('allow') or ''
                attempts.append({'identity': iname, 'method': m, 'path': path, 'http': st, 'code': bd.get('code'),
                                 'message': bd.get('message'), 'allow': allow})
    # method-override variants with real admin token
    for path in [f'/operation-logs/{admin_log}'] + ([f'/tasks/{task_id}/events/{event_id}'] if event_id else []):
        st, bd, hd = http('POST', path, tamper_body, admin, {'X-HTTP-Method-Override': 'DELETE', 'X-Method-Override': 'PUT'})
        attempts.append({'identity': 'realAdminToken', 'method': 'POST+X-HTTP-Method-Override', 'path': path, 'http': st,
                         'code': bd.get('code'), 'message': bd.get('message'), 'allow': hd.get('Allow') or ''})
        st, bd, hd = http('POST', path + '?_method=DELETE', None, admin, {'Content-Type': 'application/x-www-form-urlencoded'},
                          raw_body=b'_method=DELETE')
        attempts.append({'identity': 'realAdminToken', 'method': 'POST _method=DELETE', 'path': path, 'http': st,
                         'code': bd.get('code'), 'message': bd.get('message'), 'allow': hd.get('Allow') or ''})
    authenticated = {'realAdminToken', 'operatorTokenWithSpoofedAdminHeaders'}
    def blocked(a):
        if a['identity'] in authenticated:
            allow_set = {x.strip().upper() for x in a['allow'].split(',') if x.strip()}
            return a['http'] == 405 and a['code'] == 3004 and 'GET' in allow_set and not ({'PUT', 'DELETE', 'PATCH', 'POST'} & allow_set) \
                and '记录不可修改或删除' in (a['message'] or '')
        return a['http'] == 401
    bad = [a for a in attempts if not blocked(a)]
    after_full = {t: fp(t) for t in tables}
    after_prefix = {t: fp(t, before_full[t]['maxId']) for t in tables}
    target_row_after = sql(f'SELECT t::text FROM operation_logs t WHERE id={admin_log}')
    status_hist = {}
    for a in attempts: status_hist[f"{a['identity']}:{a['http']}"] = status_hist.get(f"{a['identity']}:{a['http']}", 0) + 1
    check('NF016.TAMPER-HTTP', '真实/伪造管理员身份对审计与事件接口PUT/DELETE/PATCH及方法覆盖全部拦截（已认证405+Allow:GET，伪造/无凭据401）',
          not bad and len(attempts) > 0, attemptCount=len(attempts), statusHistogram=status_hist, nonBlocked=bad,
          sampleAttempts=attempts[:6])
    check('NF016.TAMPER-FINGERPRINT', '越权写请求前后审计表SHA-256指纹（既有行前缀）不变，目标记录逐字节不变',
          all(after_prefix[t]['sha256'] == before_full[t]['sha256'] and after_prefix[t]['rows'] == before_full[t]['rows'] for t in tables)
          and target_row_after == target_row_before,
          before=before_full, afterSamePrefix=after_prefix, afterFull=after_full,
          fullTableUnchanged={t: after_full[t] == before_full[t] for t in tables},
          targetRowSha256Before=hashlib.sha256(target_row_before.encode()).hexdigest(),
          targetRowSha256After=hashlib.sha256(target_row_after.encode()).hexdigest())
    ev['tamperAttempts'] = attempts

    # ---------- static: mappers expose no UPDATE/DELETE on audit tables
    mp = R / 'backend/src/main/resources/mapper'
    static = {}
    for f in ('OperationLogMapper.xml', 'TaskEventMapper.xml', 'DeviceEventMapper.xml'):
        p = mp / f
        txt = p.read_text(encoding='utf-8') if p.exists() else ''
        static[f] = {'exists': p.exists(), 'update': len(re.findall(r'<update\b|\bUPDATE\s+\w*_?(operation_logs|task_events|device_events)', txt, re.I)),
                     'delete': len(re.findall(r'<delete\b|\bDELETE\s+FROM\s+(operation_logs|task_events|device_events)', txt, re.I))}
    java_hits = []
    for jp in (R / 'backend/src/main/java').rglob('*.java'):
        t = jp.read_text(encoding='utf-8', errors='replace')
        for m in re.finditer(r'(UPDATE|DELETE\s+FROM)\s+(operation_logs|task_events|device_events)\b', t, re.I):
            java_hits.append(f'{jp.name}:{m.group(0)}')
    check('NF016.STATIC-APPEND-ONLY', '审计/事件Mapper无UPDATE/DELETE语句（仅insert+select）',
          all(v['update'] == 0 and v['delete'] == 0 for v in static.values() if v['exists']) and not java_hits,
          mappers=static, javaSqlHits=java_hits)

    # ---------- long-input audit completeness
    lid0 = int(sql('SELECT coalesce(max(id),0) FROM operation_logs'))
    seg = urllib.parse.quote('审计留痕超长入参完整性校验') + '-'
    longseg = (seg + 'NFabcdefghijklmnopqrstuvwxyz-') * 1
    while len(longseg) < 6000: longseg += seg + 'Zz' * 40
    longseg = longseg[:6000].rstrip('%0123456789ABCDEF') + 'END'
    uri = f'/api/v1/users/{longseg}'
    st_l1, bd_l1, _ = http('GET', f'http://127.0.0.1:{PORT}{uri}', None, op)
    row = sql(f"SELECT id, length(operation_target), octet_length(operation_target), encode(sha256(convert_to(operation_target,'UTF8')),'hex'), "
              f"detail::text FROM operation_logs WHERE id > {lid0} AND operation_type='ACCESS_DENIED' AND username='oprator' ORDER BY id DESC LIMIT 1")
    rid, ln, oln, h, det = row.split('|', 4) if row else ('', '0', '0', '', '{}')
    dj = json.loads(det or '{}')
    l1 = {'http': st_l1, 'code': bd_l1.get('code'), 'uriLength': len(uri), 'storedLength': int(ln), 'storedOctets': int(oln),
          'uriSha256': hashlib.sha256(uri.encode()).hexdigest(), 'storedSha256': h, 'detailKeys': sorted(dj.keys()),
          'detailTargetLength': len(dj.get('target', '')), 'detailTargetEqual': dj.get('target') == uri, 'logId': rid}
    check('NF016.LONG-L1', f'{len(uri)}字符越权请求URI写入ACCESS_DENIED：operation_target与detail.target完整无截断、哈希一致、结构完整',
          st_l1 == 403 and int(ln) == len(uri) and h == l1['uriSha256'] and dj.get('target') == uri
          and set(dj.keys()) >= {'operationType', 'target', 'result'} and dj.get('result') == 'FAILED', **l1)

    # L2: create device with boundary-length (64 UTF-16) CJK + emoji name + 200-char remark + 240-char endpoint + 128-char credentialRef,
    # AND create task definition with 64-unit name + 500-unit goalTemplate + 12KB completionCondition (after seeding enabled capabilities)
    def mk_name(n_units):
        base = f'审计长设备名{ts}✈🛫'
        while len(base.encode('utf-16-le')) // 2 < n_units: base += '航'
        return base
    name64 = mk_name(64); name65 = name64 + '站'
    assert len(name64.encode('utf-16-le')) // 2 == 64
    dev_code = f'NF016_DEV_{ts}'
    long_ep = 'http://127.0.0.1:18099/adapter/' + ('segment-nf016-audit-check/' * 8)[:208]
    raw_cred = 'SecretCred#' + ('K9vL2mP8qR4tW6xY' * 7) + 'END'
    raw_cred = raw_cred[:128]
    SECRETS.append(raw_cred)
    remark200 = ('审计备注完整性校验' * 25)[:200]
    body = {'deviceCode': dev_code, 'deviceName': name64, 'deviceTypeCode': 'MOBILE_ROBOT', 'isSimulator': False,
            'areaCode': 'F2_TEST', 'positionX': 12.5, 'positionY': 28.0, 'accessEndpoint': long_ep,
            'accessCredentialRef': raw_cred, 'statusReportInterval': 15, 'remark': remark200}
    lid1 = int(sql('SELECT coalesce(max(id),0) FROM operation_logs'))
    st_bad, bd_bad, _ = http('POST', '/devices', {**body, 'deviceCode': dev_code + '_BAD', 'deviceName': name65}, cfg)
    st_ok, bd_ok, _ = http('POST', '/devices', body, cfg)
    dev_id = (bd_ok.get('data') or {}).get('id')
    # Also create task definition with 64-unit name & 500-unit goalTemplate after enabling CAP_ESCORT on this device
    if dev_id:
        sql(f"INSERT INTO device_capabilities (device_id, capability_code, capability_name, capability_type, "
            f"input_params, output_params, capability_status, test_passed) VALUES ({int(dev_id)}, 'CAP_NF016_ESCORT', "
            f"'审计复测能力', 'CAP_ESCORT', '[]'::json, '[]'::json, 'ENABLED', TRUE) ON CONFLICT DO NOTHING")
    td_name64 = ('审计任务族' + ts + '🛃🛫' + ('航' * 60))
    while len(td_name64.encode('utf-16-le')) // 2 > 64: td_name64 = td_name64[:-1]
    assert len(td_name64.encode('utf-16-le')) // 2 == 64
    goal500 = ''
    while len((goal500 + '审计目标模板完整性校验🛄').encode('utf-16-le')) // 2 <= 500:
        goal500 += '审计目标模板完整性校验🛄'
    while len(goal500.encode('utf-16-le')) // 2 < 500: goal500 += '验'
    st_td, bd_td, _ = http('POST', '/task-definitions', {
        'taskName': td_name64, 'goalTemplate': goal500,
        'sceneParams': [{'name': 'assistanceType', 'type': 'String', 'required': True, 'range': '轮椅/视障'}],
        'availableCapabilityTypes': ['CAP_ESCORT'],
        'constraintDescription': '约束' * 250,
        'completionCondition': '完成条件-' + ('长字段完整性校验-' * 900)
    }, cfg)
    rows2 = sql(f"SELECT operation_type, operation_target, detail::text FROM operation_logs WHERE id > {lid1} AND username='set' ORDER BY id").splitlines()
    dc = [r.split('|', 2) for r in rows2 if r.startswith('DEVICE_CREATE|')]
    tdc = [r.split('|', 2) for r in rows2 if r.startswith('TASK_DEFINITION_CREATE|')]
    stored_target = dc[0][1] if dc else ''
    dj2 = json.loads(dc[0][2]) if dc else {}
    td_target = tdc[0][1] if tdc else ''
    td_dj = json.loads(tdc[0][2]) if tdc else {}
    masked_cred = dj2.get('accessCredentialRef', '')
    check('NF016.LONG-L2', '边界长度(64 UTF-16)中文+Emoji设备名/任务名、239字符端点、128位凭据脱敏与12KB完成条件写入DEVICE_CREATE/TASK_DEFINITION_CREATE：无截断无乱码；65位无效边界被拒且不留成功记录',
          st_bad == 400 and st_ok == 200 and st_td == 200 and len(dc) == 1 and len(tdc) == 1
          and stored_target == dev_code and dj2.get('deviceName') == name64 and '\ufffd' not in dj2.get('deviceName', '')
          and dj2.get('accessEndpoint') == long_ep and dj2.get('deviceTypeCode') == 'MOBILE_ROBOT'
          and raw_cred not in dc[0][2] and masked_cred != raw_cred and bool(masked_cred)
          and td_target == td_name64 and td_dj.get('target') == td_name64 and '\ufffd' not in td_target,
          invalid65Http=st_bad, invalid65Code=bd_bad.get('code'), valid64DeviceHttp=st_ok, valid64TaskDefHttp=st_td,
          storedTargetEqual=stored_target == dev_code,
          deviceNameEqual=dj2.get('deviceName') == name64, deviceNameCodePoints=len(dj2.get('deviceName', '')),
          taskDefNameEqual=td_target == td_name64, taskDefNameCodePoints=len(td_target),
          endpointLength=len(dj2.get('accessEndpoint', '')), endpointEqual=dj2.get('accessEndpoint') == long_ep,
          credentialMasked=raw_cred not in (dc[0][2] if dc else '') and bool(masked_cred),
          replacementChar=('\ufffd' in dj2.get('deviceName', '')) or ('\ufffd' in td_target),
          detailKeys=sorted(dj2.keys()), auditRowsBySet=[r.split('|', 1)[0] for r in rows2])

    # L3: max-length (32 UTF-16) unknown username with emoji in LOGIN FAILED
    uname32 = f'审计{ts}🛂'
    while len(uname32.encode('utf-16-le')) // 2 < 32: uname32 += '客'
    lid2 = int(sql('SELECT coalesce(max(id),0) FROM operation_logs'))
    r32 = login(uname32, WRONG_PW); r33 = login(uname32 + 'X', WRONG_PW)
    rows3 = sql(f"SELECT username, operation_target, detail::text FROM operation_logs WHERE id > {lid2} AND operation_type='LOGIN' ORDER BY id").splitlines()
    parts = rows3[0].split('|', 2) if rows3 else ['', '', '{}']
    dj3 = json.loads(parts[2] or '{}')
    check('NF016.LONG-L3', '最大长度(32 UTF-16)含Emoji账号登录失败留痕：username/target/detail逐字一致；33位无效边界400且不留痕',
          r32[1].get('message') == '账号或密码错误' and len(rows3) == 1 and parts[0] == uname32 and parts[1] == uname32
          and dj3.get('target') == uname32 and r33[0] == 400 and no_secret(parts[2]),
          http32=r32[0], http33=r33[0], rows=len(rows3), usernameEqual=parts[0] == uname32, targetEqual=parts[1] == uname32,
          detailKeys=sorted(dj3.keys()))

    # ---------- global: no credential values in any audit detail
    alld = sql("SELECT coalesce(detail::text,'') || ' ' || coalesce(operation_target,'') FROM operation_logs")
    check('NF016.NO-CREDENTIAL', '全量operation_logs detail/target不含任何测试口令原值', no_secret(alld),
          inspectedRows=int(sql('SELECT count(*) FROM operation_logs')))
    return ev


def db_fault(ev, proxy):
    # TC-002.S4 database outage via proxy close, then recovery
    pre = login('oprator', OP_PW)
    proxy.stop(); time.sleep(1)
    t0 = time.time(); f = login('oprator', OP_PW); dt = round(time.time() - t0, 2)
    proxy.start()
    rec = None
    for _ in range(30):
        rec = login('oprator', OP_PW)
        if rec[2]: break
        time.sleep(1)
    check('TC-002.S4-DB', '数据库不可达时登录提示“系统繁忙，请稍后重试”且不建立会话；恢复后可正常登录',
          bool(pre[2]) and f[1].get('message') == '系统繁忙，请稍后重试' and not f[2] and bool(rec and rec[2]),
          beforeFaultLogin=bool(pre[2]), faultHttp=f[0], faultCode=f[1].get('code'), faultMessage=f[1].get('message'),
          faultTokenIssued=bool(f[2]), faultLatencySec=dt, recoveredLogin=bool(rec and rec[2]))


if __name__ == '__main__':
    proxy = Proxy(db.variables.get('DB_HOST', 'localhost'), int(db.variables.get('DB_PORT', '5432')), PROXY_PORT)
    proxy.start()
    p = start_backend()
    ev = {}
    try:
        ev = run()
        db_fault(ev, proxy)
    finally:
        kill_tree(p); proxy.stop()
        ev['checks'] = CHECKS
        ev['summary'] = {'P': sum(c['result'] == 'P' for c in CHECKS), 'F': sum(c['result'] == 'F' for c in CHECKS)}
        OUT.write_text(json.dumps(ev, ensure_ascii=False, indent=2), encoding='utf-8')
        print('evidence', OUT.relative_to(R), ev['summary'])
