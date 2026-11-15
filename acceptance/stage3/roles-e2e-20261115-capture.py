"""Read back this run's task, device and audit records without credentials."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path('C:/Users/savy/Desktop/TIP-main/tip')
OUT = Path(__file__).parent / 'evidence/roles-e2e-20261115'
spec = importlib.util.spec_from_file_location('localenv', ROOT / 'scripts/local-test-environment.py')
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)

def redact(value):
    if isinstance(value, dict):
        return {key: ('***' if any(word in key.lower() for word in ['password', 'token', 'secret', 'credential'])
                      else redact(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value

def main():
    admin = env.API('系统管理员')
    config = env.API('配置管理员')
    tasks = admin('/tasks?page=1&size=100')['content']
    tasks = [task for task in tasks if task['taskCode'].startswith('TASK-20261115-') and int(task['taskCode'].split('-')[-1]) >= 272]
    records = []
    for task in tasks:
        task_id = task['id']
        records.append({'task': admin(f'/tasks/{task_id}'),
            'events': admin(f'/tasks/{task_id}/events'), 'plans': admin(f'/tasks/{task_id}/plan-versions'),
            'assignments': admin(f'/tasks/{task_id}/step-assignments')})
    operations = admin('/operation-logs?page=1&size=100')['content']
    operations = [row for row in operations if str(row.get('createdAt', '')) >= '2026-11-15T22:31:00']
    own_logs = {}
    for role in ['配置管理员', '运行操作员']:
        api = env.API(role)
        rows = api('/operation-logs?page=1&size=100')['content']
        own_logs[role] = {'count': len(rows), 'usernames': sorted({row.get('username', '') for row in rows})}
    with urllib.request.urlopen('http://127.0.0.1:8080/actuator/health') as response:
        health = json.load(response)
    evidence = {'time': env.stamp(), 'tasks': records, 'operations': operations,
        'agents': config('/device-agents?page=1&size=100'), 'ownAuditScope': own_logs, 'health': health}
    (OUT / 'final-api-readback.json').write_text(json.dumps(redact(evidence), ensure_ascii=False, indent=2), encoding='utf-8')
    files = ['frontend/src/views/simulator/SimulatorConsoleView.vue', 'frontend/src/views/task/TaskDetailView.vue',
             'frontend/src/views/task/TaskListView.vue', 'frontend/src/views/situation/SituationView.vue']
    provenance = {'time': env.stamp(), 'sourceHead': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'trackedDiffSha256': hashlib.sha256(subprocess.check_output(['git', 'diff', '--binary'], cwd=ROOT)).hexdigest(),
        'runtimeSha256': hashlib.sha256((ROOT / '.local-test/runtime/backend.jar').read_bytes()).hexdigest(),
        'frontendFileHashes': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files}}
    (OUT / 'final-provenance.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
    print(json.dumps({'tasks': [(r['task']['taskCode'], r['task']['status']) for r in records],
                      'operations': len(operations), 'health': health}, ensure_ascii=False))

if __name__ == '__main__':
    main()

