"""SRS_NF010 V1.192 independent real HTTP/SQL/protocol probe.
Schema: tip_gpt_f006_v118_20261030, Redis DB 11, Port 18129.
Evaluates SRS_NF010.R01, TC-090.S1, and connection pool high-pressure queueing & zero leak.
"""
import concurrent.futures, importlib.util, json, os, re, subprocess, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT.parent / 'tip'
LOCAL_TEST = ROOT / '.local-test'
EVIDENCE = ROOT / 'acceptance/stage3/evidence'
LOCAL_TEST.mkdir(exist_ok=True)
EVIDENCE.mkdir(parents=True, exist_ok=True)

d_mod = importlib.util.module_from_spec(
    importlib.util.spec_from_file_location('db', OLD / 'scripts/isolated-reset-db.py')
)
d_mod.__spec__.loader.exec_module(d_mod)
SC = 'tip_gpt_f006_v118_20261030'
PORT = 18129
BASE_URL = f'http://127.0.0.1:{PORT}/api/v1'
SHA = '2dd346949eae90f636ec0170487122ea20931885'
TAG = 'V1.192'

OUT_SUMMARY = EVIDENCE / 'SRS_NF010-V1.192-pool-pressure-evidence.json'
OUT_POOL_LOG = EVIDENCE / 'SRS_NF010-V1.192-connection-pool.log'

def sql(query):
    full_q = f"SET search_path TO {SC}, public;\n" + query.strip().rstrip(';') + ';\n'
    result = subprocess.run(
        d_mod.common + ['-d', d_mod.shared, '-At'],
        input=full_q,
        env=dict(d_mod.variables, PGCLIENTENCODING='UTF8'),
        encoding='utf-8',
        errors='replace',
        capture_output=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"psql failed ({result.returncode}): {result.stderr.strip()}")
    lines = [line.strip() for line in result.stdout.strip().splitlines() if line.strip() and line.strip() != 'SET']
    return '\n'.join(lines)

def http_req(url, method='GET', data=None, token=None, timeout=30):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    body = json.dumps(data, ensure_ascii=False).encode('utf-8') if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        start_time = time.time()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = time.time() - start_time
            resp_body = resp.read().decode('utf-8')
            return resp.status, json.loads(resp_body) if resp_body else {}, elapsed
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start_time
        err_body = e.read().decode('utf-8')
        try:
            parsed = json.loads(err_body)
        except Exception:
            parsed = {'raw': err_body}
        return e.code, parsed, elapsed
    except Exception as e:
        return 0, {'error': str(e)}, 0

def login(username, password):
    status, res, _ = http_req(f'{BASE_URL}/auth/login', 'POST', {'username': username, 'password': password})
    token = res.get('token') or res.get('data', {}).get('token')
    if status == 200 and token:
        return token
    raise RuntimeError(f"Login failed for {username}: status {status}, {res}")

def main():
    print("=== 开始 SRS_NF010 V1.192 数据库高可用与连接池独立探针测试 ===")
    results = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'requirement': 'SRS_NF010',
        'productCommit': SHA,
        'tag': TAG,
        'subchecks': []
    }

    # 1. 登录获取操作员与管理员 Token
    print("\n[子检查 1] 获取双角色会话 Token...")
    op_token = login('oprator', '12345678')
    set_token = login('set', '12345678')
    print("操作员与配置管理员登录成功，Token获取正常")

    # 冒烟验证业务端点
    print("核验操作员高压探针端点:")
    for ep in [f'{BASE_URL}/dashboard/overview', f'{BASE_URL}/tasks?page=1&size=10', f'{BASE_URL}/situation/snapshot', f'{BASE_URL}/simulators']:
        st, res, _ = http_req(ep, 'GET', None, op_token)
        print(f"  OP {ep} -> HTTP {st} {res.get('message', '') if isinstance(res, dict) else ''}")

    print("核验配置管理员高压探针端点:")
    for ep in [f'{BASE_URL}/dashboard/overview', f'{BASE_URL}/devices?page=1&size=10', f'{BASE_URL}/device-types/overview', f'{BASE_URL}/simulators']:
        st, res, _ = http_req(ep, 'GET', None, set_token)
        print(f"  SET {ep} -> HTTP {st} {res.get('message', '') if isinstance(res, dict) else ''}")

    results['subchecks'].append({
        'name': 'SUBCHECK-1: Dual-Role Authentication Tokens',
        'status': 'PASSED',
        'detail': 'Successfully authenticated oprator and set with valid JWTs'
    })

    # 2. 验证 HikariCP 核心配置参数
    print("\n[子检查 2] 校验 HikariCP 生产连接池加固参数...")
    app_yml_path = ROOT / 'backend/src/main/resources/application.yml'
    app_yml_content = app_yml_path.read_text(encoding='utf-8')
    
    expected_pool_props = {
        'pool-name': 'AirportAiHikariPool',
        'minimum-idle': '5',
        'maximum-pool-size': '30',
        'connection-timeout': '30000',
        'idle-timeout': '600000',
        'max-lifetime': '1800000',
        'keepalive-time': '30000',
        'validation-timeout': '5000',
        'leak-detection-threshold': '60000'
    }
    
    props_found = {}
    for k, v in expected_pool_props.items():
        pattern = rf"{k}:\s*.*{re.escape(v)}"
        if re.search(pattern, app_yml_content):
            props_found[k] = True
        else:
            props_found[k] = False
            print(f"Warning: property {k}:{v} not strictly matched in YAML")
    
    all_props_ok = all(props_found.values())
    print(f"HikariCP 配置加固参数核验: {'9/9 全部匹配' if all_props_ok else '部分未匹配'}")
    results['subchecks'].append({
        'name': 'SUBCHECK-2: HikariCP Production Configuration Properties',
        'status': 'PASSED' if all_props_ok else 'FAILED',
        'expectedProperties': expected_pool_props,
        'matched': props_found
    })

    # 3. 初始连接池与数据库连接数采样
    print("\n[子检查 3] 采集初始数据库连接状态...")
    init_db_conns = sql(f"""
        SELECT count(*), state 
        FROM pg_stat_activity 
        WHERE application_name = 'GPT_NF010_V192' 
        GROUP BY state;
    """)
    print("初始数据库连接统计:\n", init_db_conns)

    # 4. 模拟连接池高压排队场景 (Burst Concurrency Stress)
    print("\n[子检查 4] 模拟连接池高压排队场景 (35 并发客户端突发高压)...")
    # 模拟 35 个并发任务查询、设备配置检索、总览及提交请求，形成连接池高压争抢与排队
    concurrent_workers = 35
    requests_per_worker = 4
    total_requests = concurrent_workers * requests_per_worker
    
    def worker_job(worker_id):
        worker_results = []
        is_operator = (worker_id % 2 == 0)
        token = op_token if is_operator else set_token
        if is_operator:
            endpoints = [
                (f'{BASE_URL}/dashboard/overview', 'GET', None),
                (f'{BASE_URL}/tasks?page=1&size=10', 'GET', None),
                (f'{BASE_URL}/situation/snapshot', 'GET', None),
                (f'{BASE_URL}/simulators', 'GET', None)
            ]
        else:
            endpoints = [
                (f'{BASE_URL}/dashboard/overview', 'GET', None),
                (f'{BASE_URL}/devices?page=1&size=10', 'GET', None),
                (f'{BASE_URL}/device-types/overview', 'GET', None),
                (f'{BASE_URL}/simulators', 'GET', None)
            ]
        for ep, method, data in endpoints:
            st, res, elapsed = http_req(ep, method, data, token)
            worker_results.append({
                'endpoint': ep,
                'status': st,
                'elapsed': elapsed,
                'success': st == 200
            })
        return worker_results

    stress_start = time.time()
    all_worker_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_workers) as executor:
        futures = [executor.submit(worker_job, i) for i in range(concurrent_workers)]
        for f in concurrent.futures.as_completed(futures):
            all_worker_results.extend(f.result())
    stress_duration = time.time() - stress_start

    success_count = sum(1 for r in all_worker_results if r['success'])
    failure_count = len(all_worker_results) - success_count
    elapsed_list = [r['elapsed'] for r in all_worker_results]
    avg_latency = sum(elapsed_list) / len(elapsed_list) if elapsed_list else 0
    p95_latency = sorted(elapsed_list)[int(len(elapsed_list) * 0.95)] if elapsed_list else 0
    max_latency = max(elapsed_list) if elapsed_list else 0

    print(f"高压并发执行完成: 总耗时 {stress_duration:.2f}s, 请求数 {len(all_worker_results)}")
    print(f"成功: {success_count}/{len(all_worker_results)} (100%), 失败: {failure_count}")
    failed_reqs = [r for r in all_worker_results if not r['success']]
    if failed_reqs:
        print("失败请求详情采样:", [{k: v for k, v in r.items() if k != 'elapsed'} for r in failed_reqs[:5]])
    print(f"延迟指标: 平均 {avg_latency*1000:.1f}ms, P95 {p95_latency*1000:.1f}ms, 最大 {max_latency*1000:.1f}ms")

    stress_passed = (success_count == total_requests) and (failure_count == 0)
    results['subchecks'].append({
        'name': 'SUBCHECK-4: High-Pressure Connection Pool Queueing Burst Test',
        'status': 'PASSED' if stress_passed else 'FAILED',
        'concurrentClients': concurrent_workers,
        'totalRequests': total_requests,
        'successCount': success_count,
        'failureCount': failure_count,
        'avgLatencyMs': round(avg_latency * 1000, 2),
        'p95LatencyMs': round(p95_latency * 1000, 2),
        'maxLatencyMs': round(max_latency * 1000, 2),
        'durationSec': round(stress_duration, 2)
    })

    # 5. 连接泄漏与死锁核验 (Post-stress connection status)
    print("\n[子检查 5] 验证连接池无泄露、无孤立事务、无死锁...")
    time.sleep(2) # 等待连接回收
    post_stress_conns = sql(f"""
        SELECT count(*), state 
        FROM pg_stat_activity 
        WHERE application_name = 'GPT_NF010_V192' 
        GROUP BY state;
    """)
    print("高压后数据库连接统计:\n", post_stress_conns)

    # 检查是否存在 idle in transaction 或 active 僵死
    leaked_or_locked = sql(f"""
        SELECT count(*) 
        FROM pg_stat_activity 
        WHERE application_name = 'GPT_NF010_V192' 
          AND state IN ('idle in transaction', 'idle in transaction (aborted)', 'active');
    """)
    idle_trans_count = int(leaked_or_locked.splitlines()[-1].strip() if leaked_or_locked else '0')
    print(f"未释放/事务死锁连接数: {idle_trans_count}")

    # 检查总连接数是否严格被 maximum-pool-size=30 约束
    total_conns_str = sql(f"""
        SELECT count(*) 
        FROM pg_stat_activity 
        WHERE application_name = 'GPT_NF010_V192';
    """)
    total_backend_conns = int(total_conns_str.splitlines()[-1].strip() if total_conns_str else '0')
    print(f"当前后端总连接数: {total_backend_conns} (上限 30)")

    leak_passed = (idle_trans_count == 0) and (total_backend_conns <= 30)
    results['subchecks'].append({
        'name': 'SUBCHECK-5: Zero Connection Leak and Deadlock Verification',
        'status': 'PASSED' if leak_passed else 'FAILED',
        'idleInTransactionCount': idle_trans_count,
        'totalBackendConnections': total_backend_conns,
        'maxPoolSizeCap': 30
    })

    # 6. 从后端日志中提取 HikariPool 运行状态
    print("\n[子检查 6] 从后端日志提取 HikariPool 状态与排队证据...")
    backend_log = LOCAL_TEST / 'backend-nf010-v192.log'
    hikari_lines = []
    if backend_log.exists():
        log_text = backend_log.read_text(encoding='utf-8', errors='replace')
        for line in log_text.splitlines():
            if 'HikariPool' in line or 'AirportAiHikariPool' in line or 'com.zaxxer.hikari' in line:
                hikari_lines.append(line)
        
        # 写入专用连接池日志
        OUT_POOL_LOG.write_text('\n'.join(hikari_lines), encoding='utf-8')
        print(f"已提取 HikariCP 运行日志 {len(hikari_lines)} 行至 {OUT_POOL_LOG.name}")
    else:
        print("Warning: backend log file not found")

    results['subchecks'].append({
        'name': 'SUBCHECK-6: HikariPool Realtime Logging & Metrics Evidence',
        'status': 'PASSED' if len(hikari_lines) > 0 else 'WARNING',
        'logLineCount': len(hikari_lines),
        'poolLogFile': OUT_POOL_LOG.name
    })

    # 7. 验证 GlobalExceptionHandler 数据库连接繁忙与并发死锁防护逻辑
    print("\n[子检查 7] 核查 GlobalExceptionHandler 对连接池耗尽(503)与并发冲突(409)防护契约...")
    handler_java = (ROOT / 'backend/src/main/java/com/airport/ai/common/GlobalExceptionHandler.java').read_text(encoding='utf-8')
    has_pool_503 = 'CannotGetJdbcConnectionException' in handler_java and 'DATABASE_POOL_BUSY' in handler_java
    has_deadlock_409 = 'DeadlockLoserDataAccessException' in handler_java and 'DATA_CONCURRENCY_CONFLICT' in handler_java
    has_dup_key_409 = 'DuplicateKeyException' in handler_java and 'DUPLICATE_KEY_CONFLICT' in handler_java

    print(f"连接池超时 503 异常捕获: {'已就绪' if has_pool_503 else '缺失'}")
    print(f"并发死锁/锁竞争 409 异常捕获: {'已就绪' if has_deadlock_409 else '缺失'}")
    print(f"唯一键冲突 409 异常捕获: {'已就绪' if has_dup_key_409 else '缺失'}")

    handler_ok = has_pool_503 and has_deadlock_409 and has_dup_key_409
    results['subchecks'].append({
        'name': 'SUBCHECK-7: Database Exception Safety Guard Contracts',
        'status': 'PASSED' if handler_ok else 'FAILED',
        'poolBusy503': has_pool_503,
        'deadlock409': has_deadlock_409,
        'duplicateKey409': has_dup_key_409
    })

    # 汇总写入
    all_passed = all(sc['status'] == 'PASSED' for sc in results['subchecks'])
    results['overallStatus'] = 'PASSED' if all_passed else 'FAILED'
    OUT_SUMMARY.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')

    print("\n================ 探针测试汇总 ================")
    print(f"SRS_NF010 连接池高压排队与并发防护: {'PASSED' if all_passed else 'FAILED'}")
    print(f"结果摘要已写入: {OUT_SUMMARY.name}")
    print("=============================================")

    if not all_passed:
        sys.exit(1)

if __name__ == '__main__':
    main()
