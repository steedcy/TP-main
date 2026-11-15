"""Recheck original task inputs after restoring the capability's enabled state."""
import json
import runpy
import time

context = runpy.run_path(__file__.replace('recheck.py', 'capture.py'))
env = context['env']
api = env.API('运行操作员')
results = []
for original_id in [273, 274]:
    original = api(f'/tasks/{original_id}')
    scene = original.get('sceneParams')
    if isinstance(scene, str):
        scene = json.loads(scene)
    keys = (['eventSource', 'flightNumber', 'changeType', 'originalTime', 'newTime', 'newGate', 'changeDescription']
            if original_id == 273 else ['baggageLocation', 'targetCounter'])
    scene = {key: scene[key] for key in keys if key in scene}
    payload = {'taskGoal': original['taskGoal'], 'taskFamily': original['taskFamily'], 'sceneParams': scene}
    created = api('/tasks', 'POST', payload)
    task_id = created['id']
    deadline = time.monotonic() + 150
    current = api(f'/tasks/{task_id}')
    while current['status'] not in ['COMPLETED', 'FAILED', 'PENDING_MANUAL', 'MANUAL_TERMINATED'] and time.monotonic() < deadline:
        time.sleep(3)
        current = api(f'/tasks/{task_id}')
    results.append({'originalTaskId': original_id, 'input': payload, 'task': current,
                    'events': api(f'/tasks/{task_id}/events'), 'plans': api(f'/tasks/{task_id}/plan-versions'),
                    'assignments': api(f'/tasks/{task_id}/step-assignments')})
    context['OUT'].joinpath('37-clean-input-recheck.json').write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(current['taskCode'], current['status'], flush=True)
