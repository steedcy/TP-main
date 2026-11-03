"""Controlled plan contradicts the same explicit Boolean completion condition in task definition and understood goal."""
import importlib.util,json
from pathlib import Path
r=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('p',r/'acceptance/stage3/probe-f013-v145.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
op=p.l.API('运行操作员');cfg=p.l.API('配置管理员');ev=p.metadata()
base=json.loads((r/'acceptance/stage3/evidence/SRS_F013-V1.145-baseline-and-manual-actions-20261103.json').read_text(encoding='utf-8'))
family=base['definition']['definitionCode'];ev['definition']=base['definition']
step={'stepSeq':1,'stepGoal':'Generate route to F2_TEST_GATE','capabilityType':'CAP_NAVIGATION','inputParams':{'targetLocation':'F2_TEST_GATE'},'precondition':'device online','completionCondition':'routeGenerated=false','failureHandling':'manual handling','stepTimeout':60}
path=r/'.local-test/f013-v145-model-cases.json';cases=json.loads(path.read_text(encoding='utf-8'));cases['F013_COMPLETION_CONFLICT']=[step];path.write_bytes(json.dumps(cases,ensure_ascii=False).encode('utf-8'))
request={'taskGoal':'F013_COMPLETION_CONFLICT synthetic navigation to F2_TEST_GATE; required completion routeGenerated=true','taskFamily':family,'sceneParams':{'targetLocation':'F2_TEST_GATE'}}
ev['request']=request;ev['controlledResponseSteps']=[step]
task=op('/tasks','POST',request);ev['observed']=p.observe(op,task['id']);plan=ev['observed']['plans'][0]
ev['checks']={'definitionRequiresTrue':base['definition']['completionCondition']=='routeGenerated=true','understoodGoalRequiresTrue':ev['observed']['task']['goalParsingResult']['completionCondition']=='routeGenerated=true',
 'candidateRequiresOpposite':plan['planSteps'][0]['completionCondition']=='routeGenerated=false',
 'expectedConstraintRejection':plan['constraintCheckResult']=='FAIL','expectedUnfrozen':not plan['frozenAt'],
 'expectedNoSupervision':not any(e['eventType']=='SUPERVISION_JUDGED' for e in ev['observed']['events']),
 'noCommands':not ev['observed']['commands']}
p.save('completion-condition-conflict',ev);print(json.dumps({'taskId':task['id'],'checks':ev['checks']}))
