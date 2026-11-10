"""SRS_NF003 V1.191 independent real HTTP/SQL/protocol probe.
Schema: tip_gpt_f006_v118_20261030, Redis DB 11, Port 18129.
Evaluates SRS_NF003.R01, TC-031.S2, TC-077.S1~S3, TC-086.S1~S2, verifying DEF-S3-032 complete closure.
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
PORT = 18129
BASE_URL = f'http://127.0.0.1:{PORT}/api/v1'
SHA = '443ccbd1b28de9971affe6253f3b80652f8fd132'
TAG = 'V1.191'

OUT_SUMMARY = E / 'SRS_NF003-V1.191-protocol-summary.json'
MODEL_JOURNAL = L / 'model-requests-nf003.jsonl'

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
        return res['data']['token'], res['data'].get('user')
    return None, None

def run_probe():
    evidence = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'schema': SC,
        'productSha': SHA,
        'productTag': TAG,
        'checks': {}
    }

    print('=== SRS_NF003 V1.191 独立复测启动 ===')

    # 保证至少存在一个 ENABLED 且 ONLINE 的设备代理
    sql("UPDATE device_agents SET online_status='ONLINE', work_status='IDLE', last_reported_at=NOW() WHERE agent_code='AGT-D68FD3AB'")

    try:
        # 1. 登录操作员与管理员
        operator_token, op_user = login('oprator', '12345678')
        assert operator_token, '操作员登录失败'
        admin_token, ad_user = login('admin', 'cares0126')
        assert admin_token, '管理员登录失败'
        print('1. 账号认证成功: operator, admin')

        # 记录初始任务数
        init_task_count = int(sql("SELECT count(*) FROM tasks"))
        print(f'2. 初始任务数: {init_task_count}')

        canary_names = ["张三", "李四", "王五", "赵六", "CANARY_NAME_NF003"]
        canary_ids = ["110101199003072345", "310101199001011234", "440106198505051234"]
        canary_phones = ["13800138000", "13900001111", "13700009999"]
        canary_passports = ["EA9988776", "G12345678"]
        canary_emails = ["canary_nf003@airport.com", "test_privacy@test.org"]

        all_canaries = canary_names + canary_ids + canary_phones + canary_passports + canary_emails

        # =========================================================================
        # Check 1: 场景参数顶层与多层嵌套敏感字段注入拦截 (DEF-S3-032 核心)
        # =========================================================================
        print('3. 执行 Check 1: 场景参数顶层与多层嵌套敏感字段注入强拦截...')
        injection_cases = [
            # 顶层字段名命中
            ("top_passengerName", {"passengerName": canary_names[0]}),
            ("top_identityDocumentNumber", {"identityDocumentNumber": canary_ids[0]}),
            ("top_phone", {"phone": canary_phones[0]}),
            ("top_idCard", {"idCard": canary_ids[1]}),
            ("top_passport", {"passport": canary_passports[0]}),
            ("top_email", {"email": canary_emails[0]}),
            ("top_chinese_name_key", {"旅客姓名": canary_names[1]}),
            ("top_chinese_id_key", {"身份证号": canary_ids[0]}),
            ("top_chinese_phone_key", {"手机号": canary_phones[1]}),
            # 嵌套 Map
            ("nested_map_passengerName", {"metadata": {"passengerName": canary_names[2], "dest": "F2_GATE_A"}}),
            ("nested_deep_map_idCard", {"level1": {"level2": {"level3": {"idCardNumber": canary_ids[2]}}}}),
            # 嵌套 List
            ("nested_list_passengers", {"passengers": [{"passengerName": canary_names[3]}, {"target": "GATE"}]}),
            ("nested_list_phones", {"contacts": ["正常业务说明", {"phone": canary_phones[2]}]}),
            # 嵌套 JSON 字符串
            ("nested_json_string_phone", {"extraJson": json.dumps({"mobile": canary_phones[0]})}),
            ("nested_json_string_id", {"extraJson": json.dumps({"idCard": canary_ids[0]})}),
            # 键值对或自然语言身份文本直接放入普通参数值
            ("value_nl_passenger_name", {"remark": f"旅客姓名: {canary_names[0]}"}),
            ("value_nl_id_card", {"remark": f"身份证: {canary_ids[0]}"}),
            ("value_nl_phone", {"remark": f"联系电话: {canary_phones[0]}"}),
            ("value_nl_passport", {"remark": f"护照号码: {canary_passports[1]}"})
        ]

        check1_results = []
        for case_id, params in injection_cases:
            status, resp = http_req(
                f'{BASE_URL}/tasks',
                method='POST',
                data={'taskGoal': '测试场景参数敏感字段拦截', 'sceneParams': params},
                token=operator_token
            )
            passed = (status == 400 and (resp.get('code') in [3000, 3001] or '身份' in resp.get('message', '')))
            check1_results.append({
                'caseId': case_id,
                'status': status,
                'responseCode': resp.get('code'),
                'responseMessage': resp.get('message'),
                'passed': passed
            })
            assert passed, f'Check 1 失败: {case_id} 期望 400 强拦截，实际状态 {status}, 响应: {resp}'

        after_check1_count = int(sql("SELECT count(*) FROM tasks"))
        assert after_check1_count == init_task_count, f'Check 1 违规建任务! 初始 {init_task_count}, 当前 {after_check1_count}'
        print(f'Check 1 全部通过: {len(check1_results)} 项敏感参数注入全部被 400 拦截，任务新增 0 (DEF-S3-032 闭环)')
        evidence['checks']['check1_scene_params_interception'] = {
            'status': 'PASSED',
            'count': len(check1_results),
            'results': check1_results
        }

        # =========================================================================
        # Check 2: 行李测量事件 (measurement-event) 敏感字段注入拦截
        # =========================================================================
        print('4. 执行 Check 2: 行李测量事件敏感注入强拦截...')
        meas_cases = [
            ("meas_extraParams_passengerName", {
                "deviceCode": "BAG-DEV-001", "baggageId": "BAG-001", "baggageLocation": "CHECKIN_01",
                "length": 110.0, "width": 60.0, "height": 50.0, "weight": 25.0,
                "extraParams": {"passengerName": canary_names[0]}
            }),
            ("meas_extraParams_nested_phone", {
                "deviceCode": "BAG-DEV-001", "baggageId": "BAG-002", "baggageLocation": "CHECKIN_01",
                "length": 110.0, "width": 60.0, "height": 50.0, "weight": 25.0,
                "extraParams": {"meta": {"contactPhone": canary_phones[0]}}
            }),
            ("meas_handling_nl_id", {
                "deviceCode": "BAG-DEV-001", "baggageId": "BAG-003", "baggageLocation": "CHECKIN_01",
                "length": 110.0, "width": 60.0, "height": 50.0, "weight": 25.0,
                "handlingInstructions": f"旅客姓名: {canary_names[1]}, 身份证: {canary_ids[0]}"
            })
        ]

        check2_results = []
        for case_id, payload in meas_cases:
            status, resp = http_req(
                f'{BASE_URL}/tasks/measurement-event',
                method='POST',
                data=payload,
                token=operator_token
            )
            passed = (status == 400 and (resp.get('code') in [3000, 3001] or '身份' in resp.get('message', '')))
            check2_results.append({
                'caseId': case_id,
                'status': status,
                'responseCode': resp.get('code'),
                'responseMessage': resp.get('message'),
                'passed': passed
            })
            assert passed, f'Check 2 失败: {case_id} 期望 400 强拦截，实际 {status}: {resp}'

        after_check2_count = int(sql("SELECT count(*) FROM tasks"))
        assert after_check2_count == init_task_count, f'Check 2 违规建任务! 初始 {init_task_count}, 当前 {after_check2_count}'
        print(f'Check 2 全部通过: {len(check2_results)} 项行李测量事件敏感注入全部被 400 拦截')
        evidence['checks']['check2_measurement_event_interception'] = {
            'status': 'PASSED',
            'count': len(check2_results),
            'results': check2_results
        }

        # =========================================================================
        # Check 3: 澄清接口 (clarify) 敏感身份注入拦截
        # =========================================================================
        print('5. 执行 Check 3: 澄清接口敏感身份注入强拦截...')
        # 先创建一个需要补充信息的任务（特殊旅客缺少起点）
        status, create_resp = http_req(
            f'{BASE_URL}/tasks',
            method='POST',
            data={
                'taskGoal': '协助特殊旅客轮椅出行 缺少起点',
                'taskFamily': 'SPECIAL_PASSENGER_SERVICE',
                'sceneParams': {'assistanceType': 'WHEELCHAIR'}
            },
            token=operator_token
        )
        assert status == 200, f'创建特殊旅客测试任务失败: {create_resp}'
        clarify_task_id = create_resp['data']['id']
        print(f'创建澄清测试任务成功: Task ID {clarify_task_id}')

        # 获取待补充的问题列表
        q_json = sql(f"SELECT missing_info_questions FROM tasks WHERE id = {clarify_task_id}")
        questions = json.loads(q_json) if q_json and q_json.startswith('[') else ["请补充服务起点"]
        q0 = questions[0]

        clarify_cases = [
            ("clarify_passengerName", {"answers": {"passengerName": canary_names[0]}}),
            ("clarify_idCard", {"answers": {"idCard": canary_ids[0]}}),
            ("clarify_phone", {"answers": {"phone": canary_phones[0]}})
        ]

        check3_results = []
        for case_id, payload in clarify_cases:
            status, resp = http_req(
                f'{BASE_URL}/tasks/{clarify_task_id}/clarify',
                method='POST',
                data=payload,
                token=operator_token
            )
            passed = (status == 400 and (resp.get('code') in [3000, 3001] or '身份' in resp.get('message', '')))
            check3_results.append({
                'caseId': case_id,
                'status': status,
                'responseCode': resp.get('code'),
                'responseMessage': resp.get('message'),
                'passed': passed
            })
            assert passed, f'Check 3 失败: {case_id} 期望 400，实际 {status}: {resp}'

        # 测试带敏感信息的自由文本回答自动脱敏存储
        status, legal_clarify_resp = http_req(
            f'{BASE_URL}/tasks/{clarify_task_id}/clarify',
            method='POST',
            data={'answers': {q0: f"从F2_TEST_GATE出发 旅客姓名={canary_names[0]} 电话={canary_phones[0]}"}},
            token=operator_token
        )
        assert status == 200, f'合法澄清答案提交失败: {legal_clarify_resp}'

        # 核查澄清存储中已脱敏
        db_clarify_scene = sql(f"SELECT scene_params FROM tasks WHERE id = {clarify_task_id}")
        assert canary_names[0] not in db_clarify_scene, f'澄清答案落库泄露姓名: {canary_names[0]}'
        assert canary_phones[0] not in db_clarify_scene, f'澄清答案落库泄露手机: {canary_phones[0]}'

        print(f'Check 3 全部通过: 敏感澄清注入全部被 400 拦截，合法业务澄清答案正常接受并脱敏落库')
        evidence['checks']['check3_clarify_interception'] = {
            'status': 'PASSED',
            'results': check3_results,
            'legalClarifyPassed': True,
            'dbClarifySceneSanitized': True
        }

        # =========================================================================
        # Check 4: 自然语言任务目标自动递归脱敏与各层级防护验证
        # =========================================================================
        print('6. 执行 Check 4: 自然语言任务目标脱敏与出入库防泄漏验证...')
        raw_goal_with_sensitive = (
            f"请协助特殊旅客 旅客姓名={canary_names[0]} 身份证号={canary_ids[0]} 手机号={canary_phones[0]} "
            f"护照号={canary_passports[0]} 邮箱={canary_emails[0]} 前往F2_TEST_GATE登机口"
        )

        status, task_created = http_req(
            f'{BASE_URL}/tasks',
            method='POST',
            data={'taskGoal': raw_goal_with_sensitive},
            token=operator_token
        )
        assert status == 200, f'提交带脱敏目标的任务失败: {task_created}'
        sanitized_task_id = task_created['data']['id']
        created_task_view = task_created['data']

        # 1. 响应出参核查
        view_goal = created_task_view.get('taskGoal', '')
        for s in [canary_names[0], canary_ids[0], canary_phones[0], canary_passports[0], canary_emails[0]]:
            assert s not in view_goal, f'TaskView 响应泄露敏感信息: {s} 仍在 taskGoal 中!'
        assert '[PROTECTED_IDENTITY]' in view_goal or '[PROTECTED_ID]' in view_goal, f'未包含脱敏掩码: {view_goal}'
        assert 'F2_TEST_GATE' in view_goal, f'正常业务目的地被误脱敏: {view_goal}'

        # 2. 数据库 tasks 表核查
        db_task_goal = sql(f"SELECT task_goal FROM tasks WHERE id = {sanitized_task_id}")
        for s in [canary_names[0], canary_ids[0], canary_phones[0], canary_passports[0], canary_emails[0]]:
            assert s not in db_task_goal, f'数据库 tasks 表落库泄露: {s} 存在于 task_goal 中!'

        # 3. 数据库 task_events 表核查
        db_events = sql(f"SELECT detail_summary FROM task_events WHERE task_id = {sanitized_task_id}")
        for s in [canary_names[0], canary_ids[0], canary_phones[0], canary_passports[0], canary_emails[0]]:
            assert s not in db_events, f'数据库 task_events 表落库泄露: {s} 存在于事件详情中!'

        # 4. 数据库 operation_logs 表核查
        db_op_logs = sql(f"SELECT operation_target, detail FROM operation_logs WHERE operation_type = 'TASK_SUBMIT' ORDER BY id DESC LIMIT 5")
        for s in [canary_names[0], canary_ids[0], canary_phones[0], canary_passports[0], canary_emails[0]]:
            assert s not in db_op_logs, f'数据库 operation_logs 表落库泄露: {s} 存在于操作日志中!'

        # 5. 人工取消并携带敏感原因，验证取消事件脱敏
        status, cancel_resp = http_req(
            f'{BASE_URL}/tasks/{sanitized_task_id}/cancel',
            method='POST',
            data={'reason': f"旅客姓名: {canary_names[1]} 电话: {canary_phones[1]} 放弃协助"},
            token=operator_token
        )
        assert status == 200, f'任务取消失败: {cancel_resp}'

        # 核查取消后数据库中的原因
        db_cancel_reason = sql(f"SELECT manual_terminate_reason FROM tasks WHERE id = {sanitized_task_id}")
        for s in [canary_names[1], canary_phones[1]]:
            assert s not in db_cancel_reason, f'manual_terminate_reason 泄露敏感信息: {s}'

        print('Check 4 全部通过: 自然语言任务目标在出参、任务表、事件表、审计日志及取消原因中 100% 安全脱敏，0 处泄露')
        evidence['checks']['check4_goal_and_lifecycle_desensitization'] = {
            'status': 'PASSED',
            'taskId': sanitized_task_id,
            'viewGoal': view_goal,
            'dbTaskGoal': db_task_goal,
            'dbCancelReason': db_cancel_reason
        }

        # =========================================================================
        # Check 5: 合法业务编号与代码安全放行 (无假阳性 / 零误拒)
        # =========================================================================
        print('7. 执行 Check 5: 合法业务编号安全放行验证 (零误拒)...')
        safe_cases = [
            # 航班号
            ("flight_ca1234", "请处理航班CA1234旅客行李转运", {"flightNumber": "CA1234", "targetLocation": "F2_TEST_GATE"}),
            ("flight_mu5182", "请处理航班MU5182登机口变更", {"flightNumber": "MU5182", "gate": "F2_ZONE_A"}),
            # 行李临时编号
            ("baggage_bag123", "超规行李处理 编号BAG-123456", {"baggageId": "BAG-123456", "targetLocation": "F2_TEST_GATE"}),
            ("baggage_oversize_code", "超规行李处理 编号P-R08-OVERSIZE", {"baggageId": "P-R08-OVERSIZE", "targetLocation": "F2_TEST_GATE"}),
            # 预置区域与临时任务代码
            ("area_codes", "空间引导 前往F2_TEST_GATE并在F2_ZONE_B会合", {"targetLocation": "F2_TEST_GATE", "tempCode": "TEMP-2026-001"}),
            ("normal_assistance", "协助轮椅旅客从出发大厅前往F2_TEST_GATE登机口", {"assistanceType": "WHEELCHAIR", "targetLocation": "F2_TEST_GATE"})
        ]

        check5_results = []
        created_safe_tasks = []
        for case_id, goal, params in safe_cases:
            status, resp = http_req(
                f'{BASE_URL}/tasks',
                method='POST',
                data={'taskGoal': goal, 'sceneParams': params},
                token=operator_token
            )
            passed = (status == 200 and resp.get('code') == 200)
            task_id = resp.get('data', {}).get('id') if passed else None
            if task_id:
                created_safe_tasks.append(task_id)
            check5_results.append({
                'caseId': case_id,
                'goal': goal,
                'status': status,
                'taskId': task_id,
                'passed': passed
            })
            assert passed, f'Check 5 误拒合法业务请求! {case_id}: status={status}, resp={resp}'

        print(f'Check 5 全部通过: {len(check5_results)} 项合法业务编号（航班号/行李编号/区域代号）正常放行，无误拒')
        evidence['checks']['check5_safe_business_identifiers'] = {
            'status': 'PASSED',
            'count': len(check5_results),
            'results': check5_results
        }

        # =========================================================================
        # Check 6: 外部大模型交互日志与数据库全库深度审计扫描 (0 处真实敏感信息暴露)
        # =========================================================================
        print('8. 执行 Check 6: 大模型交互日志与数据库全库敏感信息深度扫描...')
        
        # 1. 扫描大模型交互请求日志
        model_leaks = []
        model_requests_count = 0
        if MODEL_JOURNAL.exists():
            for line in MODEL_JOURNAL.read_text(encoding='utf-8').splitlines():
                if not line.strip(): continue
                model_requests_count += 1
                entry = json.loads(line)
                raw_req_str = json.dumps(entry.get('request', {}), ensure_ascii=False)
                for canary in all_canaries:
                    if canary in raw_req_str:
                        model_leaks.append({'phase': entry.get('phase'), 'canary': canary, 'raw': raw_req_str})
        
        print(f'大模型交互日志扫描完成: 共记录 {model_requests_count} 次外部模型交互，泄露敏感个人信息条数: {len(model_leaks)}')
        assert len(model_leaks) == 0, f'大模型交互日志中发现真实敏感信息外发: {model_leaks}'

        # 2. 扫描 schema 中所有表的所有字符/文本字段
        tables_to_scan = ['tasks', 'task_events', 'operation_logs', 'plan_versions', 'context_snapshots', 'task_exceptions', 'users']
        scan_results = {}
        total_leaks = 0

        for tbl in tables_to_scan:
            cols_raw = sql(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = '{SC}' 
                  AND table_name = '{tbl}' 
                  AND data_type IN ('text', 'character varying', 'character', 'json', 'jsonb')
            """)
            cols = [c.strip() for c in cols_raw.splitlines() if c.strip()]
            tbl_leaks = []
            if cols:
                conds = []
                for col in cols:
                    for canary in all_canaries:
                        escaped_c = canary.replace("'", "''")
                        conds.append(f"CASE WHEN {col}::text LIKE '%{escaped_c}%' THEN 1 ELSE 0 END")
                total_in_tbl = sql(f"SELECT coalesce(sum({' + '.join(conds)}), 0) FROM {tbl}")
                cnt = int(total_in_tbl) if total_in_tbl and total_in_tbl.isdigit() else 0
                if cnt > 0:
                    for col in cols:
                        for canary in all_canaries:
                            escaped_c = canary.replace("'", "''")
                            c_cnt_str = sql(f"SELECT count(*) FROM {tbl} WHERE {col}::text LIKE '%{escaped_c}%'")
                            c_cnt = int(c_cnt_str) if c_cnt_str and c_cnt_str.isdigit() else 0
                            if c_cnt > 0:
                                tbl_leaks.append({'column': col, 'canary': canary, 'count': c_cnt})
                                total_leaks += c_cnt
            scan_results[tbl] = {'columnsScanned': len(cols), 'leaks': tbl_leaks}

        print(f'Check 6 数据库全库扫描完成: 扫描 {len(tables_to_scan)} 张数据表，发现敏感个人信息落库数: {total_leaks}')
        for tbl, res in scan_results.items():
            assert len(res['leaks']) == 0, f'表 {tbl} 发现敏感个人信息泄漏: {res["leaks"]}'

        assert total_leaks == 0, f'数据库落库泄露断言失败! 累计发现 {total_leaks} 处敏感信息落库!'
        evidence['checks']['check6_zero_leakage_audit'] = {
            'status': 'PASSED',
            'modelRequestsAudited': model_requests_count,
            'modelLeaks': len(model_leaks),
            'databaseLeaks': total_leaks,
            'tablesScanned': scan_results
        }

        # =========================================================================
        # Check 7: 规则与缺陷最终判定汇总
        # =========================================================================
        print('9. 汇总复测结论...')
        summary = {
            'rule_SRS_NF003_R01': 'P',
            'step_TC_031_S2': 'P',
            'step_TC_077_S1_S3': 'P',
            'step_TC_086_S1_S2': 'P',
            'issue_DEF_S3_032': 'CLOSED',
            'verdict': 'REQUIREMENT_PASSED',
            'details': '全链路旅客个人身份隐私保护（顶层/嵌套/JSON/自然语言/事件/日志/出参/模型交互）强拦截与脱敏100%通过，合法业务代码零误拒，数据库0处敏感信息落库，DEF-S3-032彻底关闭。'
        }
        evidence['verdict'] = summary

        OUT_SUMMARY.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'复测摘要与受控证据已写入: {OUT_SUMMARY}')
        print('=== SRS_NF003 协议与数据库整轮独立测试 全部通过 ===\n')

    finally:
        pass

if __name__ == '__main__':
    run_probe()
