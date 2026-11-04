"""Verify actual per-device command feedback against recovery events, offline.

Consumes preserved raw current-round observations; creates no new business tasks.
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path


def main():
    folder = Path(__file__).resolve().parent / 'evidence'
    source = folder / 'SRS_F015-V1.156-full-round-20261104.json'
    out = folder / 'SRS_F015-V1.156-recovery-command-verification-20261104.json'
    assert not out.exists(), 'Do not overwrite verification evidence'
    data = json.loads(source.read_text(encoding='utf8'))
    assert data.get('finishedAt'), 'Wait for the complete main probe'
    order = data['recoveryScenarioOrder']
    first = data['robotBAgent']['agentId'] if order['first'] == 'G156_F015_ROBOT_B' else 'AGT-803437A3'
    second = data['robotBAgent']['agentId'] if order['second'] == 'G156_F015_ROBOT_B' else 'AGT-803437A3'
    results = []
    for name in ['multi-candidate-recovered', 'multi-candidate-exhausted']:
        case = next(x for x in data['cases'] if x['name'] == name)
        rows = [json.loads(line) for line in case['deviceCommandRows'].splitlines()]
        commands = [x for x in rows if x['command_type'] == 'EXECUTE_CAPABILITY']
        feedback = {agent: [json.loads(x['response_payload'])['executionResult']
                            for x in commands if x['agent_code'] == agent]
                    for agent in [first, second]}
        assert feedback[first] and all(x == 'FAILED' for x in feedback[first])
        assert feedback[second], 'Ranking/acceptance text alone is not actual execution'
        exceptions = [json.loads(line) for line in case['exceptions'].splitlines()]
        assert exceptions
        for ex in exceptions:
            assert all(ex.get(k) for k in ['occurred_at', 'exception_type', 'step_seq',
                                           'reason_code', 'recovery_action', 'recovery_result',
                                           'impact_conclusion', 'resolved_at', 'resolved_by'])
            assert ex['exception_status'] == 'RESOLVED'
        recovered = [e for e in case['observed']['events'] if e['eventType'] == 'EXCEPTION_RECOVERED']
        if name == 'multi-candidate-recovered':
            assert feedback[second][-1] == 'SUCCESS'
            assert all(ex['recovery_result'] == 'SUCCESS' for ex in exceptions)
            success_time = max(datetime.fromisoformat(x['updated_at']) for x in commands
                               if json.loads(x['response_payload'])['executionResult'] == 'SUCCESS')
            assert recovered and all(datetime.fromisoformat(e['occurredAt']) >= success_time for e in recovered)
        else:
            assert all(x == 'FAILED' for x in feedback[second])
            assert all(ex['recovery_result'] == 'FAILED' for ex in exceptions)
            assert not recovered
        progress = case['inFlightRecovery']
        assert all(x['recovery_result'] is None and x['exception_status'] == 'PROCESSING'
                   for x in progress['exceptions'])
        assert not any(e['eventType'] == 'EXCEPTION_RECOVERED' for e in progress['observed']['events'])
        results.append({'name': name, 'taskId': case['taskId'], 'feedbackByAgent': feedback,
                        'exceptions': exceptions, 'recoveredEvents': recovered, 'result': 'P'})
    out.write_bytes(json.dumps({'source': source.name,
                                'sourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                                'layer': 'Offline assertions on original real HTTP/command/SQL observations; zero new tasks',
                                'cases': results}, ensure_ascii=False, indent=2).encode('utf8'))
    print(json.dumps({'tasks': [x['taskId'] for x in results], 'result': 'P'}))


if __name__ == '__main__':
    main()
