"""Verify the live local role workflows and collect task/device command evidence.

Credentials are loaded from the named local workspace and never persisted.
The scenario argument selects a task already submitted through the browser.
"""
import argparse
import importlib.util
import json
import pathlib
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/product-improvements/evidence/PI-005'

def environment(workspace):
    spec = importlib.util.spec_from_file_location('local_environment', workspace / 'scripts/local-test-environment.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def collect(env, task_id):
    api = env.API('运行操作员')
    deadline = time.monotonic() + 180
    task = api(f'/tasks/{task_id}')
    while task['status'] not in ['COMPLETED', 'FAILED', 'PENDING_MANUAL', 'MANUAL_TERMINATED'] and time.monotonic() < deadline:
        time.sleep(2)
        task = api(f'/tasks/{task_id}')
    query_env = env.env()
    query_env['PGPASSWORD'] = query_env.get('DB_PASSWORD', '123456')
    query_env['PGCLIENTENCODING'] = 'UTF8'
    query = f"select coalesce(json_agg(x),'[]') from (select step_seq,agent_code,capability_type,command_status,command_payload::json->'inputParams' as params from device_commands where task_id={int(task_id)} and command_type='EXECUTE_CAPABILITY' order by id) x;"
    result = subprocess.run(['C:/Program Files/PostgreSQL/15/bin/psql.exe', '-XAt', '-v', 'ON_ERROR_STOP=1',
        '-h', query_env.get('DB_HOST', 'localhost'), '-p', query_env.get('DB_PORT', '5432'),
        '-U', query_env.get('DB_USERNAME', 'admin'), '-d', query_env.get('DB_NAME', 'airport_ai'), '-c', query],
        env=query_env, capture_output=True, text=True, encoding='utf-8', check=True)
    return {'time': env.stamp(), 'task': task, 'commands': json.loads(result.stdout),
            'steps': api(f'/tasks/{task_id}/step-assignments'), 'events': api(f'/tasks/{task_id}/events'),
            'plans': api(f'/tasks/{task_id}/plan-versions')}

def validate(name, record):
    checks = {'completed': record['task']['status'] == 'COMPLETED'}
    commands = record['commands']
    if name == 'flight':
        publications = [c for c in commands if c['capability_type'] in ['CAP_FLIGHT_UPDATE', 'CAP_INFO_DISPLAY', 'CAP_NOTIFICATION']]
        checks['three_publication_channels'] = len(publications) == 3
        checks['same_delay_content'] = all('23:00' in json.dumps(c['params'], ensure_ascii=False)
            and 'GATE_A05' in json.dumps(c['params'], ensure_ascii=False)
            and 'F2_TEST_GATE' not in json.dumps(c['params']) for c in publications)
        checks['delay_type'] = any(c['params'].get('updateType') == 'DELAY' for c in publications)
    elif name == 'normal':
        checks['only_measurement'] = [c['capability_type'] for c in commands] == ['CAP_BAGGAGE_MEASURE']
        checks['within_limit'] = any(e['reasonCode'] == 'BAGGAGE_WITHIN_LIMIT' for e in record['events'])
    elif name == 'escort':
        checks['meeting_notices'] = all('T2值机区' in json.dumps(c['params'], ensure_ascii=False)
            and 'GATE_A05' in json.dumps(c['params'], ensure_ascii=False) for c in commands[:2])
        navigations = [c for c in commands if c['capability_type'] == 'CAP_NAVIGATION']
        escorts = [c for c in commands if c['capability_type'] == 'CAP_ESCORT']
        checks['meeting_then_escort_same_robot'] = bool(navigations and escorts
            and navigations[0]['params'].get('targetLocation') == 'T2值机区'
            and navigations[0]['agent_code'] == escorts[0]['agent_code']
            and escorts[0]['params'].get('targetLocation') == 'GATE_A05')
        checks['meeting_arrival_feedback'] = any(s.get('outputParams', {}).get('arrivalLocation') == 'T2值机区'
            and s.get('outputParams', {}).get('arrivalStatus') == 'ARRIVED' for s in record['steps'])
    elif name == 'oversize':
        checks['event_sample_reused'] = any(s.get('reasonCode') == 'MEASUREMENT_EVENT_REUSED' for s in record['steps'])
        checks['no_second_measurement'] = all(c['capability_type'] != 'CAP_BAGGAGE_MEASURE' for c in commands)
        checks['alert_display_navigation'] = {'CAP_OVERSIZE_ALERT', 'CAP_INFO_DISPLAY', 'CAP_NAVIGATION'}.issubset(
            {c['capability_type'] for c in commands}) and len({s['stepSeq'] for s in record['steps']}) <= 5
        checks['counter_reached'] = any(s.get('outputParams', {}).get('arrivalLocation') == '超规行李专柜B01' for s in record['steps'])
    return checks

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scenario', choices=['flight', 'normal', 'escort', 'oversize'])
    parser.add_argument('task_id', type=int)
    parser.add_argument('--workspace', type=pathlib.Path, default=ROOT.parent / 'tip')
    args = parser.parse_args()
    record = collect(environment(args.workspace), args.task_id)
    record['checks'] = validate(args.scenario, record)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'{args.scenario}-{args.task_id}.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'task': record['task']['taskCode'], 'status': record['task']['status'], 'checks': record['checks']}, ensure_ascii=False))
    if not all(record['checks'].values()):
        raise SystemExit(1)

if __name__ == '__main__':
    main()
