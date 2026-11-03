"""Record UI retry and API target-change contrast without changing product code."""
import importlib.util,json
from pathlib import Path
r=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('p',r/'acceptance/stage3/probe-f013-v142.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
api=p.l.API('运行操作员');ev=p.metadata()
ui=p.observe(api,124);ev['uiTask124AfterKeyboardRetry']=ui
ev['uiTask124ModelRequests']=[json.loads(x) for x in (r/'.local-test/f013-v142-model-requests.jsonl').read_text(encoding='utf-8').splitlines() if json.loads(x)['request'].get('taskGoal','').startswith('F013_MISSING_completionCondition')]
ev['uiTask124Audit']=p.sql(f"select operation_type,operation_target,operation_result from {p.SC}.operation_logs where operation_target like 'TASK-20261103-0124 -> %' order by id").splitlines()
before=p.observe(api,140);ev['apiRetryBefore']=before
req={'action':'RETRY_PLANNING','taskGoal':'F013_GOOD revised goal from operator','reason':'synthetic corrected goal for F013 independent retest'}
ev['apiRetryRequest']=req;ev['apiRetryResponse']=p.raw(api,'/tasks/140/manual-actions',req);after=p.observe(api,140);ev['apiRetryAfter']=after
ev['checks']={'uiCreatedSecondVersion':len(ui['plans'])==2,'uiRetainedOldGoal':ui['task']['taskGoal']=='F013_MISSING_completionCondition synthetic navigation',
 'uiNoGoalUpdatedEvent':not any(e['eventType']=='TASK_GOAL_UPDATED' for e in ui['events']),
 'apiUpdatedGoal':after['task']['taskGoal']==req['taskGoal'],'apiNewVersion':len(after['plans'])==len(before['plans'])+1,
 'apiOldFrozenVersionUnchanged':before['plans'][0]==after['plans'][0],
 'apiGoalUpdatedEvent':any(e['eventType']=='TASK_GOAL_UPDATED' for e in after['events']),
 'apiNewPlanThreeChecksAndFreeze':all(after['plans'][-1][k]=='PASS' for k in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']) and bool(after['plans'][-1]['frozenAt'])}
ev['uiTask123Correction']='The first pointer-based browser probe intended RETRY_PLANNING but audit records MARK_FAILED. Treat as browser action mismatch; task123 is not evidence of retry product behavior. Keyboard-based task124 probe explicitly records RETRY_PLANNING and is the authoritative retry observation.'
p.save('actions-and-target-retry',ev)
print(json.dumps(ev['checks']))
