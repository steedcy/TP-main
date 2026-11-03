"""Check that a natural-language model goal cannot override a structured task definition."""
import importlib.util,json
from pathlib import Path
r=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('p',r/'acceptance/stage3/probe-f013-v149.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
op=p.l.API('运行操作员');cfg=p.l.API('配置管理员');ev=p.metadata()
old=json.loads((r/'acceptance/stage3/evidence/SRS_F013-V1.145-baseline-and-manual-actions-20261103.json').read_text(encoding='utf-8'))
ev['definition']=cfg(f"/task-definitions/{old['definition']['id']}")
ev['controlledCase']=json.loads((r/'.local-test/f013-v149-cases.json').read_text())['F149_NATURAL_GOAL']
ev['request']={'taskGoal':'F149_NATURAL_GOAL synthetic navigation to F2_TEST_GATE; required routeGenerated=true','taskFamily':ev['definition']['definitionCode'],'sceneParams':{'targetLocation':'F2_TEST_GATE'}}
t=op('/tasks','POST',ev['request']);tid=t['id'];ev['taskId']=tid;ev['after']=p.observe(op,tid)
v=ev['after']['plans'][-1];o=ev['after']
ev['checks']={'constraintRejected':v['constraintCheckResult']=='FAIL','conflictCode':any(e['reasonCode']=='ERR_COMPLETION_CONDITION_CONFLICT' for e in v['validationErrors']),
'notFrozen':not v['frozenAt'],'notSupervisedOrDispatched':not any(e['eventType']=='SUPERVISION_JUDGED' for e in o['events']) and not o['commands'] and not o['assignments']}
print(json.dumps({'taskId':tid,'status':o['task']['status'],'checks':ev['checks']}),flush=True)
if o['task']['status'] not in ['COMPLETED','FAILED','MANUAL_TERMINATED']:ev['cleanupTerminate']=p.raw(op,f'/tasks/{tid}/terminate',{'reason':'F013 V149 natural-completion fixture cleanup','confirmed':True})
p.save('natural-completion-definition-conflict',ev)
