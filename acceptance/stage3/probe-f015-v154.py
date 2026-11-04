"""F015 real HTTP/device/persistence probe, isolated GPT schema only.

Uses existing local account/DPAPI helpers without emitting credentials. Requires the
production JAR on 18129, controlled model on 18117 and GPT robot on 18132.
All template publication and trial actions use public APIs; SQL is read-only.
"""
import copy
import argparse
import importlib.util
import json
from pathlib import Path
import time
import subprocess
import re
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('prior', ROOT / 'acceptance/stage3/probe-f014-v151.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
SC = p.SC
SHA = '612ff7d39b96e9b947f97f53e6bab6322af87018'
EVIDENCE = ROOT / 'acceptance/stage3/evidence/SRS_F015-V1.154-live-baseline-20261104.json'


def sql(query):
    db = p.base.d
    result = subprocess.run(db.common + ['-d', db.shared, '-At', '-c', query],
        env=dict(db.variables, PGCLIENTENCODING='UTF8'),
        encoding='utf-8', capture_output=True, check=True)
    return result.stdout.strip()


p.sql = sql
p.base.sql = sql


def main():
    global EVIDENCE
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', default='')
    parser.add_argument('--skip-success', action='store_true',
                        help='Reuse separately captured successful control after a probe-only failure')
    args = parser.parse_args()
    if args.label:
        EVIDENCE = EVIDENCE.with_stem(EVIDENCE.stem + '-' + args.label)
    assert not EVIDENCE.exists(), 'Append evidence using a new output path; do not overwrite'
    cfg = p.l.API('配置管理员')
    op = p.l.API('运行操作员')
    family = 'EXT_0FA30230'
    template_ids = []
    task_ids = []
    cases = {}
    ev = {'version': 'V1.154', 'codeSha': SHA, 'timezone': 'Asia/Shanghai',
          'startedAt': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
          'schema': SC, 'templates': [], 'trials': [], 'formalCases': [], 'cleanup': {}}

    def save():
        EVIDENCE.write_bytes(json.dumps(ev, ensure_ascii=False, indent=2).encode('utf-8'))

    def agent():
        return next(x for x in cfg('/device-agents?page=1&size=100')['content']
                    if x['deviceCode'] == 'G126_ROBOT')

    def idle():
        for _ in range(120):
            a = agent()
            if a['onlineStatus'] == 'ONLINE' and a['workStatus'] == 'IDLE':
                return a
            time.sleep(0.5)
        raise RuntimeError('GPT robot not idle/online')

    secret = json.loads(p.l.protect((ROOT.parent / 'tip/.local-test/gpt-f007-v126-robot.dpapi').read_bytes(), True))['token']

    def scenario(value):
        result = p.l.request('http://127.0.0.1:18132/device-api/v1/control/scenario',
                             'POST', {'scenarioResult': value}, token=secret)
        return result

    def wait_task(tid):
        for _ in range(240):
            t = op(f'/tasks/{tid}')
            if t['status'] in ['COMPLETED', 'FAILED', 'PENDING_MANUAL', 'MANUAL_TERMINATED']:
                return p.observe(op, tid)
            time.sleep(0.5)
        return p.observe(op, tid)

    def trial(label, template):
        a = idle()
        request = {'inputParams': {'targetLocation': 'F2_TEST_GATE'},
                   'simulatedDevices': [{'stepSeq': 1, 'agentId': a['agentId']}]}
        response = cfg(f"/baseline-templates/{template['id']}/dry-run", 'POST', request)
        tid = response['taskId']
        task_ids.append(tid)
        row = {'name': label, 'templateId': template['id'], 'request': request, 'response': response}
        ev['trials'].append(row)
        save()
        row['observed'] = wait_task(tid)
        row['result'] = cfg(f"/baseline-templates/{template['id']}/dry-runs/{tid}")
        row['templateAfterTrial'] = cfg(f"/baseline-templates/{template['id']}")
        save()
        assert row['result']['result'] == 'SUCCESS', 'Fixture dry-run must genuinely pass'
        assert row['templateAfterTrial']['templateStatus'] == 'DRY_RUN_PASSED'
        return row

    def formal(marker, expected_template):
        idle()
        cases[marker] = {'steps': [p.step()], 'confidence': 1.0, 'diverse': False}
        (ROOT / '.local-test/f015-v154-cases.json').write_bytes(json.dumps(cases).encode('utf-8'))
        request = {'taskGoal': marker + ' synthetic navigation to F2_TEST_GATE',
                   'taskFamily': family, 'sceneParams': {'targetLocation': 'F2_TEST_GATE'}}
        response = op('/tasks', 'POST', request)
        tid = response['id']
        task_ids.append(tid)
        row = {'name': marker, 'request': request, 'response': response,
               'expectedTemplateId': expected_template}
        ev['formalCases'].append(row)
        save()
        o = row['observed'] = wait_task(tid)
        row['taskExceptions'] = p.sql(f"select row_to_json(e)::text from {SC}.task_exceptions e where task_id={tid} order by id")
        row['persistedPlans'] = p.sql(f"select id,version_no,source,baseline_template_id,rule_set_version,frozen_at from {SC}.plan_versions where task_id={tid} order by version_no")
        row['persistedEvents'] = p.sql(f"select event_type,reason_code,detail_summary,occurred_at from {SC}.task_events where task_id={tid} order by id")
        row['assignmentPlanIds'] = p.sql(f"select plan_version_id from {SC}.task_step_assignments where task_id={tid} order by id").splitlines()
        plans = o['plans']
        base = [x for x in plans if x['source'] == 'BASELINE_TEMPLATE']
        row['checks'] = {
            'autonomousHigh': plans[0]['riskLevel'] == 'HIGH',
            'baselineRevalidatedAndFrozen': len(base) == 1 and bool(base[0]['frozenAt'])
                and all(base[0][k] == 'PASS' for k in ['structureCheckResult', 'capabilityCheckResult', 'constraintCheckResult']),
            'originalGoalPreserved': o['task']['taskGoal'] == request['taskGoal'],
            'originalHighNeverAssigned': bool(base) and bool(row['assignmentPlanIds'])
                and all(int(x) == base[0]['id'] for x in row['assignmentPlanIds']),
            'expectedTemplateChosen': bool(base) and base[0]['baselineTemplateId'] == expected_template,
            'templateVersionRecorded': bool(base) and base[0]['ruleSetVersion'] == 'V1.0',
            'noReplanOrSecondBaseline': len(base) == 1 and not o['task']['replanUsed']
                and not any(x['eventType'] == 'REPLANNING_TRIGGERED' for x in o['events']),
        }
        save()
        print(marker, tid, json.dumps(row['checks']), flush=True)
        return row

    ev['definitionBefore'] = cfg('/task-definitions/17')
    ev['rulesBefore'] = cfg('/risk-rules')
    ev['templatesBefore'] = cfg('/baseline-templates')
    ev['health'] = p.l.request('http://127.0.0.1:18129/actuator/health')
    ev['keyEntrySmoke'] = {'taskListReadable': bool(op('/tasks?page=1&size=1')),
                           'overview': op('/dashboard/overview'), 'agentsReadable': bool(cfg('/device-agents?page=1&size=1'))}
    save()
    try:
        cfg('/task-definitions/17/enable', 'POST')
        cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update', 'POST', {'enabled': True})
        scenario('SUCCESS')
        seed = cfg('/baseline-templates/32')
        assert not any(x['templateStatus'] == 'ENABLED' and x['templateIntent'] == family
                       for x in ev['templatesBefore']), 'Do not change a competing active baseline'
        suffix = datetime.now().strftime('%H%M%S')
        for label in ['older-trial-A', 'newer-trial-B']:
            request = {'templateName': f'G154 F015 {label} {suffix}', 'templateIntent': family,
                       'inputParams': copy.deepcopy(seed['inputParams']), 'steps': copy.deepcopy(seed['steps'])}
            response = cfg('/baseline-templates', 'POST', request)
            template_ids.append(response['id'])
            ev['templates'].append({'name': label, 'request': request, 'response': response})
            save()
            trial(label, response)
        older, newer = template_ids
        cfg(f'/baseline-templates/{newer}/enable', 'POST')
        ev['newerEnabledFirst'] = cfg(f'/baseline-templates/{newer}')
        if not args.skip_success:
            good = formal('F154_QUALIFIED_BASELINE_SUCCESS', newer)
            assert all(good['checks'].values()) and good['observed']['task']['status'] == 'COMPLETED'
        scenario('TIMEOUT')
        failed = formal('F154_QUALIFIED_BASELINE_TIMEOUT', newer)
        failed['failureChecks'] = {
            'pendingManual': failed['observed']['task']['status'] == 'PENDING_MANUAL',
            'manualTransitionRecorded': any(x['eventType'] == 'TASK_PENDING_MANUAL' for x in failed['observed']['events']),
            'noFalseRecovered': not any(x['eventType'] == 'EXCEPTION_RECOVERED' for x in failed['observed']['events']),
            'noReplan': failed['checks']['noReplanOrSecondBaseline'],
        }
        save()
        scenario('SUCCESS')
        cfg(f'/baseline-templates/{older}/enable', 'POST')
        ev['bothEnabledOlderLast'] = [cfg(f'/baseline-templates/{x}') for x in template_ids]
        ev['trialSuccessTimesSql'] = p.sql(f"select task_id,event_type,occurred_at from {SC}.task_events where task_id in ({','.join(str(x['response']['taskId']) for x in ev['trials'])}) and event_type='DRY_RUN_SUCCEEDED' order by occurred_at")
        ev['templatesSql'] = p.sql(f"select id,template_name,template_version,template_status,updated_at from {SC}.baseline_templates where id in ({older},{newer}) order by id")
        row = formal('F154_RECENT_TRIAL_PRIORITY_REVERSED_ENABLE', newer)
        row['expected'] = 'Both templates have same family, same one-step content and V1.0. B passed trial later; enabling A later must not replace trial chronology.'
        ev['sortingResult'] = 'P' if row['checks']['expectedTemplateChosen'] else 'F'
        newest_trial = ev['trials'][-1]
        actual_trial_time = next(x['occurredAt'] for x in newest_trial['observed']['events']
                                 if x['eventType'] == 'DRY_RUN_SUCCEEDED')
        selection = next(x['detailSummary'] for x in row['observed']['events']
                         if x['eventType'] == 'BASELINE_DOWNGRADED' and '选择依据' in x['detailSummary'])
        match = re.search(r'最近试运行通过时间([^优]+)优先', selection)
        row['selectionTimeChecks'] = {'actualTrialTime': actual_trial_time,
            'selectionTime': match.group(1) if match else None,
            'sameExactTime': bool(match) and datetime.fromisoformat(match.group(1)) == datetime.fromisoformat(actual_trial_time)}
        assert row['checks']['expectedTemplateChosen'] and row['selectionTimeChecks']['sameExactTime']
        save()
    finally:
        scenario('SUCCESS')
        for tid in task_ids:
            t = op(f'/tasks/{tid}')
            if t['status'] not in ['COMPLETED', 'FAILED', 'MANUAL_TERMINATED']:
                ev['cleanup'][f'task{tid}'] = p.raw(op, f'/tasks/{tid}/terminate',
                    {'reason': 'F015 V154 independent probe cleanup; evidence retained', 'confirmed': True})
        for template_id in template_ids:
            cfg(f'/baseline-templates/{template_id}/disable', 'POST')
        if ev['definitionBefore']['definitionStatus'] == 'DISABLED':
            cfg('/task-definitions/17/disable', 'POST')
        original_rule = next(x for x in ev['rulesBefore'] if x['ruleCode'] == 'RULE_RESOURCE_CRITICAL')
        cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update', 'POST', {'enabled': original_rule['enabled']})
        ev['cleanup']['templates'] = [cfg(f'/baseline-templates/{x}') for x in template_ids]
        ev['cleanup']['definition'] = cfg('/task-definitions/17')
        ev['cleanup']['robot'] = agent()
        ev['cleanup']['activeOwnAssignments'] = p.sql(f"select count(*) from {SC}.task_step_assignments where task_id in ({','.join(map(str, task_ids)) or '0'}) and step_status in ('PENDING_ASSIGNMENT','EXECUTING')")
        ev['cleanup']['retainedTaskIds'] = task_ids
        ev['finishedAt'] = datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
        save()


if __name__ == '__main__':
    main()
