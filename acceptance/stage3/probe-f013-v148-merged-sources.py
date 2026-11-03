"""Isolate definition constraints without duplicating a machine assertion in the raw goal."""
import importlib.util,json
from pathlib import Path
r=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('p',r/'acceptance/stage3/probe-f013-v148.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
op=p.l.API('运行操作员');cfg=p.l.API('配置管理员');ev=p.metadata();ev['cases']=[]
old=json.loads((r/'acceptance/stage3/evidence/SRS_F013-V1.145-baseline-and-manual-actions-20261103.json').read_text(encoding='utf-8'))
ev['definition']=cfg(f"/task-definitions/{old['definition']['id']}")
controlled=json.loads((r/'.local-test/f013-v148-cases.json').read_text(encoding='utf-8'))
for marker,positive in [('F148_NATURAL_GOAL',False),('F148_MODEL_OVERRIDE',False),('F148_MODEL_GOOD',True),('F148_DUPLICATE_STEP',False)]:
 req={'taskGoal':marker+' synthetic navigation to F2_TEST_GATE','taskFamily':ev['definition']['definitionCode'],'sceneParams':{'targetLocation':'F2_TEST_GATE'}}
 t=op('/tasks','POST',req);tid=t['id'];o=p.observe(op,tid);v=o['plans'][-1]
 if positive:checks={'threePass':all(v[k]=='PASS' for k in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']),'frozen':bool(v['frozenAt']),'supervised':any(e['eventType']=='SUPERVISION_JUDGED' for e in o['events'])}
 else:checks={'constraintRejected':v['constraintCheckResult']=='FAIL','conflictCode':any(e['reasonCode']=='ERR_COMPLETION_CONDITION_CONFLICT' for e in v['validationErrors']),'notFrozen':not v['frozenAt'],'notSupervisedOrDispatched':not any(e['eventType']=='SUPERVISION_JUDGED' for e in o['events']) and not o['commands'] and not o['assignments']}
 case={'name':marker,'request':req,'controlledResponse':controlled[marker],'observed':o,'checks':checks}
 if o['task']['status'] not in ['COMPLETED','FAILED','MANUAL_TERMINATED']:case['cleanupTerminate']=p.raw(op,f'/tasks/{tid}/terminate',{'reason':'F013 V148 source-isolation fixture cleanup','confirmed':True})
 ev['cases'].append(case);p.save('merged-sources-definition-priority',ev)
 print(json.dumps({'case':marker,'taskId':tid,'checks':checks}),flush=True)
