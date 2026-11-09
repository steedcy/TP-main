"""SRS_F028 V1.189 independent real HTTP/SQL/protocol probe.
GPT-owned schema tip_gpt_f006_v118_20261030 / Redis DB 10.
Port: 18129, Proxy: 15179.
Evaluates SRS_F028.R01~R08 and TC-085.S1~S2, verifying DEF-S3-009 complete closure.
"""
import copy, hashlib, importlib.util, json, os, re, subprocess, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

R = Path(__file__).resolve().parents[2]
old = R.parent / 'tip'
L = R / '.local-test'
E = R / 'acceptance/stage3/evidence'
L.mkdir(exist_ok=True)
E.mkdir(parents=True, exist_ok=True)

d_mod = importlib.util.module_from_spec(
    importlib.util.spec_from_file_location('db', old / 'scripts/isolated-reset-db.py')
)
d_mod.__spec__.loader.exec_module(d_mod)
SC = 'tip_gpt_f006_v118_20261030'
BASE_URL = 'http://127.0.0.1:18129/api/v1'
SHA = '14e75c6bf1b0ef226d9cba4ba422ffb7ceab1f3a'
OUT = E / 'SRS_F028-V1.189-http-sql-protocol-20261110.json'

def sql(query):
    result = subprocess.run(
        d_mod.common + ['-d', d_mod.shared, '-At'],
        input=query + ';\n',
        env=dict(d_mod.variables, PGCLIENTENCODING='UTF8'),
        encoding='utf-8',
        errors='replace',
        capture_output=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"psql failed ({result.returncode}): {result.stderr.strip()}")
    return result.stdout.strip()

def http_req(url, method='GET', data=None, token=None, timeout=30):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    body = json.dumps(data, ensure_ascii=False).encode('utf-8') if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            raw = res.read().decode('utf-8')
            return res.status, json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as ex:
        raw = ex.read().decode('utf-8')
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {'raw': raw}
        return ex.code, parsed

def login(username, password):
    status, res = http_req(f'{BASE_URL}/auth/login', 'POST', {'username': username, 'password': password})
    if status == 200 and res.get('code') == 200:
        return res['data']['token']
    return None

def run_probe():
    evidence = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'schema': SC,
        'productSha': SHA,
        'productTag': 'V1.189',
        'evaluations': {}
    }

    print('=== SRS_F028 V1.189 独立复测开始 ===')

    # 1. 登录验证
    admin_token = login('admin', 'cares0126')
    config_token = login('set', '12345678')
    operator_token = login('oprator', '12345678')

    assert admin_token and config_token and operator_token, '三类预置角色登录失败'
    print('[P] 1. 三类角色登录成功')
    evidence['evaluations']['auth'] = {
        'status': 'PASSED',
        'admin': bool(admin_token),
        'config': bool(config_token),
        'operator': bool(operator_token)
    }

    # 2. 账号管理实时操作与审计留痕核查（闭环 DEF-S3-009 / SRS_F028.R03 / TC-085.S1）
    target_username = f's3_audit_op_{int(time.time())}'
    test_password = 'SecretPass#2026'

    # 2.1 创建账号 (USER_CREATE)
    create_body = {
        'username': target_username,
        'password': test_password,
        'realName': '虚构审计测试员',
        'role': 'OPERATOR',
        'contact': '13912345678'
    }
    st, resp = http_req(f'{BASE_URL}/users', 'POST', create_body, token=admin_token)
    assert st == 200 and resp.get('code') == 200, f'创建测试用户失败: {resp}'
    target_user_id = resp['data']['id']
    print(f'[P] 2.1 创建用户成功: {target_username} (ID: {target_user_id})')

    # 2.2 状态变更 (USER_STATUS_CHANGE) - ACTIVE -> INACTIVE
    st, resp = http_req(f'{BASE_URL}/users/{target_user_id}/status', 'POST', {'status': 'INACTIVE'}, token=admin_token)
    assert st == 200 and resp.get('code') == 200, f'更新状态为 INACTIVE 失败: {resp}'
    print('[P] 2.2 更新状态为 INACTIVE 成功')

    # 2.3 状态变更 (USER_STATUS_CHANGE) - INACTIVE -> ACTIVE
    st, resp = http_req(f'{BASE_URL}/users/{target_user_id}/status', 'POST', {'status': 'ACTIVE'}, token=admin_token)
    assert st == 200 and resp.get('code') == 200, f'更新状态为 ACTIVE 失败: {resp}'
    print('[P] 2.3 更新状态为 ACTIVE 成功')

    # 2.4 重置密码 (PASSWORD_RESET)
    st, resp = http_req(f'{BASE_URL}/users/{target_user_id}/reset-password', 'POST', {'newPassword': 'NewSecret#2026'}, token=admin_token)
    assert st == 200 and resp.get('code') == 200, f'重置密码失败: {resp}'
    print('[P] 2.4 重置密码成功')

    # 2.5 触发账号锁定与管理员解锁 (MANUAL_HANDLING)
    for _ in range(3):
        http_req(f'{BASE_URL}/auth/login', 'POST', {'username': target_username, 'password': 'WrongPassword#999'})
    st, resp = http_req(f'{BASE_URL}/users/{target_user_id}/unlock', 'POST', None, token=admin_token)
    assert st == 200 and resp.get('code') == 200, f'解锁账号失败: {resp}'
    print('[P] 2.5 触发锁定并解锁成功')

    # 2.6 核查 operation_logs 中的 detail 结构化内容 (DEF-S3-009 验证)
    st, log_resp = http_req(f'{BASE_URL}/operation-logs?username=admin&page=1&size=20', 'GET', token=admin_token)
    assert st == 200 and log_resp.get('code') == 200
    recent_logs = log_resp['data']['content']

    account_logs_found = {
        'USER_CREATE': None,
        'USER_STATUS_CHANGE_1': None,
        'USER_STATUS_CHANGE_2': None,
        'PASSWORD_RESET': None,
        'MANUAL_HANDLING': None
    }

    status_changes = []
    for log in recent_logs:
        op_type = log.get('operationType')
        target = log.get('operationTarget') or ''
        if op_type == 'USER_CREATE' and target_username in target and not account_logs_found['USER_CREATE']:
            account_logs_found['USER_CREATE'] = log
        elif op_type == 'USER_STATUS_CHANGE' and target_username in target:
            status_changes.append(log)
        elif op_type == 'PASSWORD_RESET' and target_username in target and not account_logs_found['PASSWORD_RESET']:
            account_logs_found['PASSWORD_RESET'] = log
        elif op_type == 'MANUAL_HANDLING' and target_username in target and not account_logs_found['MANUAL_HANDLING']:
            account_logs_found['MANUAL_HANDLING'] = log

    if len(status_changes) >= 2:
        account_logs_found['USER_STATUS_CHANGE_2'] = status_changes[0] # most recent: INACTIVE -> ACTIVE
        account_logs_found['USER_STATUS_CHANGE_1'] = status_changes[1] # earlier: ACTIVE -> INACTIVE

    # 逐项断言 detail 结构与凭据脱敏
    create_log = account_logs_found['USER_CREATE']
    assert create_log and create_log.get('detail'), 'USER_CREATE 日志缺少 detail'
    create_detail = json.loads(create_log['detail'])
    assert create_detail.get('action') == 'CREATE'
    assert create_detail.get('after', {}).get('username') == target_username
    assert create_detail.get('after', {}).get('role') == 'OPERATOR'
    assert create_detail.get('after', {}).get('status') == 'ACTIVE'
    assert test_password not in create_log['detail']
    assert '13912345678' not in create_log['detail']
    assert '虚构审计测试员' not in create_log['detail']

    sc1_log = account_logs_found['USER_STATUS_CHANGE_1']
    assert sc1_log and sc1_log.get('detail'), 'USER_STATUS_CHANGE 1 日志缺少 detail'
    sc1_detail = json.loads(sc1_log['detail'])
    assert sc1_detail.get('action') == 'STATUS_CHANGE'
    assert sc1_detail.get('before', {}).get('status') == 'ACTIVE'
    assert sc1_detail.get('after', {}).get('status') == 'INACTIVE'
    assert sc1_detail.get('target', {}).get('username') == target_username

    sc2_log = account_logs_found['USER_STATUS_CHANGE_2']
    assert sc2_log and sc2_log.get('detail'), 'USER_STATUS_CHANGE 2 日志缺少 detail'
    sc2_detail = json.loads(sc2_log['detail'])
    assert sc2_detail.get('action') == 'STATUS_CHANGE'
    assert sc2_detail.get('before', {}).get('status') == 'INACTIVE'
    assert sc2_detail.get('after', {}).get('status') == 'ACTIVE'
    assert sc2_detail.get('target', {}).get('username') == target_username

    reset_log = account_logs_found['PASSWORD_RESET']
    assert reset_log and reset_log.get('detail'), 'PASSWORD_RESET 日志缺少 detail'
    reset_detail = json.loads(reset_log['detail'])
    assert reset_detail.get('action') == 'RESET_PASSWORD'
    assert reset_detail.get('passwordChanged') is True
    assert 'NewSecret#2026' not in reset_log['detail']
    assert '$2a$' not in reset_log['detail']

    unlock_log = account_logs_found['MANUAL_HANDLING']
    assert unlock_log and unlock_log.get('detail'), 'MANUAL_HANDLING 日志缺少 detail'
    unlock_detail = json.loads(unlock_log['detail'])
    assert unlock_detail.get('action') == 'UNLOCK'
    assert unlock_detail.get('before', {}).get('status') == 'LOCKED'
    assert unlock_detail.get('after', {}).get('status') == 'ACTIVE'

    print('[P] 2.6 DEF-S3-009 验证通过：所有账号操作均携带结构化 before/after detail 摘要且凭据脱敏')
    evidence['evaluations']['tc085_s1_def_s3_009'] = {
        'status': 'PASSED',
        'createDetail': create_detail,
        'statusChangeDetailActiveToInactive': sc1_detail,
        'statusChangeDetailInactiveToActive': sc2_detail,
        'resetPasswordDetail': reset_detail,
        'unlockDetail': unlock_detail,
        'credentialLeakageFound': False
    }

    # 3. 业务规则 SRS_F028.R01 校验：至少记录 5 类关键操作
    r01_query = f'''
    SELECT DISTINCT operation_type FROM {SC}.operation_logs
    WHERE operation_type IN ('LOGIN', 'LOGOUT', 'DEVICE_CREATE', 'DEVICE_UPDATE', 'DEVICE_DELETE',
                             'DEVICE_STATUS_CHANGE', 'DEVICE_CAPABILITY_STATUS_CHANGE',
                             'CAP_TEMPLATE_STATUS_CHANGE', 'BASELINE_TEMPLATE_ENABLE',
                             'BASELINE_TEMPLATE_DISABLE', 'TASK_TERMINATE')
    '''
    r01_types = sql(r01_query).splitlines()
    assert any('LOGIN' in t for t in r01_types), '缺少 LOGIN 操作记录'
    assert any('DEVICE_' in t for t in r01_types), '缺少 DEVICE_* 配置记录'
    assert any('CAPABILITY' in t or 'CAP_' in t for t in r01_types), '缺少能力启停记录'
    assert any('BASELINE_TEMPLATE' in t for t in r01_types), '缺少模板启停记录'
    assert any('TASK_TERMINATE' in t for t in r01_types), '缺少人工终止记录'
    print(f'[P] 3. SRS_F028.R01 校验通过：五类核心关键操作记录齐全 ({len(r01_types)} 种操作类型)')
    evidence['evaluations']['srs_f028_r01'] = {'status': 'PASSED', 'distinctOperationTypes': r01_types}

    # 4. 业务规则 SRS_F028.R02 校验：任务定义、风险规则、人工处置
    r02_query = f'''
    SELECT DISTINCT operation_type FROM {SC}.operation_logs
    WHERE operation_type IN ('TASK_DEFINITION_CREATE', 'TASK_DEFINITION_UPDATE', 'TASK_DEFINITION_DISABLE', 'TASK_DEFINITION_ENABLE',
                             'RISK_RULE_CHANGE', 'TASK_MANUAL_ACTION', 'MANUAL_HANDLING')
    '''
    r02_types = sql(r02_query).splitlines()
    assert any('TASK_DEFINITION' in t for t in r02_types), '缺少任务定义变更记录'
    assert any('RISK_RULE' in t for t in r02_types), '缺少风险规则变更记录'
    assert any('MANUAL' in t for t in r02_types), '缺少人工处置记录'
    print(f'[P] 4. SRS_F028.R02 校验通过：任务定义变更、高风险规则变更与人工处置记录齐全')
    evidence['evaluations']['srs_f028_r02'] = {'status': 'PASSED', 'r02OperationTypes': r02_types}

    # 5. 业务规则 SRS_F028.R03 校验：全记录字段完整性
    r03_user_null_check = f'''
    SELECT count(*) FROM {SC}.operation_logs
    WHERE (username IS NOT NULL AND username != 'SYSTEM')
      AND (created_at IS NULL OR username IS NULL OR role IS NULL OR operation_type IS NULL OR operation_result IS NULL)
    '''
    user_null_count = int(sql(r03_user_null_check))
    assert user_null_count == 0, f'存在 {user_null_count} 条核心字段为空的用户操作记录'

    r03_system_null_check = f'''
    SELECT count(*) FROM {SC}.operation_logs
    WHERE username = 'SYSTEM'
      AND (created_at IS NULL OR operation_type IS NULL OR operation_result IS NULL)
    '''
    system_null_count = int(sql(r03_system_null_check))
    assert system_null_count == 0, f'存在 {system_null_count} 条核心字段为空的系统操作记录'

    print('[P] 5. SRS_F028.R03 校验通过：所有操作记录时间、操作人、角色、类型、结果完整存在 (用户操作 0 缺失，系统作业 0 缺失)')
    evidence['evaluations']['srs_f028_r03'] = {'status': 'PASSED', 'userNullCount': 0, 'systemNullCount': 0}

    # 6. 业务规则 SRS_F028.R04 校验：登录失败与越权访问写入操作记录
    # 6.1 越权访问测试：运行操作员尝试访问管理员接口 POST /api/v1/users
    unauth_st, unauth_resp = http_req(f'{BASE_URL}/users', 'POST', {'username': 'illegal_user'}, token=operator_token)
    assert unauth_st == 403, f'未授权请求未返回 403: {unauth_st}'

    # 检查数据库中是否存在 LOGIN/FAILED 与 ACCESS_DENIED
    failed_login_count = int(sql(f"SELECT count(*) FROM {SC}.operation_logs WHERE operation_type = 'LOGIN' AND operation_result = 'FAILED'"))
    access_denied_count = int(sql(f"SELECT count(*) FROM {SC}.operation_logs WHERE operation_type = 'ACCESS_DENIED' AND operation_result = 'FAILED'"))
    assert failed_login_count > 0, '未检索到登录失败记录'
    assert access_denied_count > 0, '未检索到越权访问记录'
    print(f'[P] 6. SRS_F028.R04 校验通过：登录失败记录 {failed_login_count} 条，越权访问记录 {access_denied_count} 条')
    evidence['evaluations']['srs_f028_r04'] = {
        'status': 'PASSED',
        'failedLoginRecordsCount': failed_login_count,
        'accessDeniedRecordsCount': access_denied_count
    }

    # 7. 业务规则 SRS_F028.R05 校验：操作记录不可编辑、不可删除 (防篡改)
    sample_log_id = sql(f"SELECT id FROM {SC}.operation_logs ORDER BY id DESC LIMIT 1")
    hash_query = f"SELECT md5(concat(id, operation_type, detail, created_at)) FROM {SC}.operation_logs WHERE id = {sample_log_id}"
    before_hash = sql(hash_query)

    put_st, _ = http_req(f'{BASE_URL}/operation-logs/{sample_log_id}', 'PUT', {'operationType': 'TAMPERED'}, token=admin_token)
    del_st, _ = http_req(f'{BASE_URL}/operation-logs/{sample_log_id}', 'DELETE', token=admin_token)
    after_hash = sql(hash_query)

    assert put_st in (404, 405, 500), f'PUT 请求未被拦截: {put_st}'
    assert del_st in (404, 405, 500), f'DELETE 请求未被拦截: {del_st}'
    assert before_hash == after_hash, '操作记录哈希在非法篡改请求后发生改变！'
    print('[P] 7. SRS_F028.R05 校验通过：PUT/DELETE 请求被拦截，数据库指纹严格未变')
    evidence['evaluations']['srs_f028_r05'] = {
        'status': 'PASSED',
        'putStatus': put_st,
        'deleteStatus': del_st,
        'hashIdentical': before_hash == after_hash
    }

    # 8. 业务规则 SRS_F028.R06 校验：敏感凭据脱敏与原值零泄露 (含 DEF-S3-010 保持验证)
    # 8.1 检查 GET /api/v1/users 不返回 passwordHash
    st, users_resp = http_req(f'{BASE_URL}/users?page=1&size=50', 'GET', token=admin_token)
    assert st == 200
    for u in users_resp['data']['content']:
        assert 'passwordHash' not in u, f"用户列表暴露了 passwordHash: {u.get('username')}"
        assert 'password' not in u, f"用户列表暴露了 password: {u.get('username')}"

    # 8.2 扫描数据库 operation_logs 中的 detail
    leak_check = sql(f"""
    SELECT count(*) FROM {SC}.operation_logs
    WHERE detail::text LIKE '%$2a$%' OR detail::text LIKE '%$2b$%'
       OR detail::text LIKE '%cares0126%' OR detail::text LIKE '%SecretPass#2026%' OR detail::text LIKE '%NewSecret#2026%'
    """)
    assert int(leak_check) == 0, f'在 operation_logs.detail 中检测到凭据/哈希泄露行数: {leak_check}'
    print('[P] 8. SRS_F028.R06 校验通过：用户列表无 passwordHash 暴露 (DEF-S3-010 保持关闭)，审计日志零凭据泄露')
    evidence['evaluations']['srs_f028_r06'] = {
        'status': 'PASSED',
        'userListExposesPasswordHash': False,
        'operationLogsCredentialLeakCount': 0
    }

    # 9. 业务规则 SRS_F028.R07 校验：查询权限与角色隔离
    st, admin_logs = http_req(f'{BASE_URL}/operation-logs?page=1&size=100', 'GET', token=admin_token)
    st, config_logs = http_req(f'{BASE_URL}/operation-logs?page=1&size=100', 'GET', token=config_token)
    st, operator_logs = http_req(f'{BASE_URL}/operation-logs?page=1&size=100', 'GET', token=operator_token)

    admin_total = admin_logs['data']['totalElements']
    config_total = config_logs['data']['totalElements']
    operator_total = operator_logs['data']['totalElements']

    # 检查非管理员只返回自身记录
    config_usernames = {item['username'] for item in config_logs['data']['content']}
    operator_usernames = {item['username'] for item in operator_logs['data']['content']}

    assert config_usernames.issubset({'set'}), f'配置管理员看到了其他用户的日志: {config_usernames}'
    assert operator_usernames.issubset({'oprator'}), f'运行操作员看到了其他用户的日志: {operator_usernames}'
    assert admin_total > config_total and admin_total > operator_total, '管理员日志总数应包含全量'

    # 越权参数查询测试：配置管理员传入 ?username=admin 尝试获取管理员日志
    st, cross_logs = http_req(f'{BASE_URL}/operation-logs?username=admin&page=1&size=100', 'GET', token=config_token)
    cross_usernames = {item['username'] for item in cross_logs['data']['content']}
    assert cross_usernames.issubset({'set'}), f'配置管理员通过参数越权查看了其他用户日志: {cross_usernames}'
    print(f'[P] 9. SRS_F028.R07 校验通过：管理员全量 ({admin_total})，配置管理员隔离 ({config_total})，操作员隔离 ({operator_total})')
    evidence['evaluations']['srs_f028_r07'] = {
        'status': 'PASSED',
        'adminTotalElements': admin_total,
        'configAdminTotalElements': config_total,
        'operatorTotalElements': operator_total,
        'crossParameterTamperPrevented': True
    }

    # 10. 业务规则 SRS_F028.R08 校验：操作记录与任务因果交叉追溯
    task_trace_check = sql(f"""
    SELECT concat(l.operation_target, ' | ', l.operation_type, ' | ', l.username, ' | taskId=', e.task_id, ' | ', e.event_type)
    FROM {SC}.operation_logs l
    JOIN {SC}.task_events e ON l.operation_target LIKE concat('%', e.task_id, '%')
    WHERE l.operation_type IN ('TASK_TERMINATE', 'TASK_MANUAL_ACTION')
    LIMIT 1
    """)
    assert task_trace_check, '未找到操作记录与任务事件的交叉追溯关联行'
    print(f'[P] 10. SRS_F028.R08 校验通过：操作记录与任务事件双向关联追溯正常 ({task_trace_check})')
    evidence['evaluations']['srs_f028_r08'] = {
        'status': 'PASSED',
        'sampleTraceRelation': task_trace_check
    }

    # 11. TC-085.S2 边界测试：空账号查询
    st, empty_resp = http_req(f'{BASE_URL}/operation-logs?username=nonexistent_user_xyz_99999&page=1&size=20', 'GET', token=admin_token)
    assert st == 200 and empty_resp.get('code') == 200
    assert empty_resp['data']['totalElements'] == 0
    assert len(empty_resp['data']['content']) == 0
    print('[P] 11. TC-085.S2 校验通过：空账号查询返回 0 行且不报错')
    evidence['evaluations']['tc085_s2_empty_query'] = {
        'status': 'PASSED',
        'returnedTotal': 0
    }

    # 12. 清理测试用户 (置为 INACTIVE，保持外键完整性)
    sql(f"UPDATE {SC}.users SET status = 'INACTIVE' WHERE username = '{target_username}'")
    print(f'[P] 12. 清理完成：临时用户 {target_username} 已置为 INACTIVE')

    # 保存受控证据
    OUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'=== 全部协议层与数据库核验通过，受控证据已保存至 {OUT.name} ===')
    return True

if __name__ == '__main__':
    run_probe()
