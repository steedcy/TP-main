import importlib.util,json,sys
from pathlib import Path
r=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('probe',r/'acceptance/stage3/probe-f013-v142.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
api=m.l.API('运行操作员');ev=m.metadata();ev['cases']=[]
names=sys.argv[1:] or ['MISSING_'+f for f in ['stepGoal','capabilityType','inputParams','precondition','completionCondition','failureHandling']]+['SIX','SELF','FORWARD','DEPENDENCY_MISSING','LOOP','DYNAMIC','NEGOTIATION','FAKE_CAP','DISABLED_CAP','NO_CANDIDATE','OUTSIDE_TASK','MOTION','BAD_PARAM','MULTI']
for name in names:
 req={'taskGoal':'F013_'+name+' synthetic navigation','taskFamily':'EXT_2AD8B934','sceneParams':{'targetLocation':'F2_TEST_GATE'}}
 case={'name':name,'request':req}
 try:
  task=api('/tasks','POST',req);case['observed']=m.observe(api,task['id'])
 except Exception as ex:case['probeError']=str(ex)
 ev['cases'].append(case);m.save('batch-'+names[0]+'-to-'+names[-1],ev)
 o=case.get('observed',{});print(json.dumps({'name':name,'taskId':o.get('task',{}).get('id'),'status':o.get('task',{}).get('status'),'plans':[(p['structureCheckResult'],p['capabilityCheckResult'],p['constraintCheckResult'],bool(p['frozenAt'])) for p in o.get('plans',[])],'eventReasons':[e['reasonCode'] for e in o.get('events',[]) if e.get('reasonCode')],'commands':len(o.get('commands',[])),'error':case.get('probeError')}),flush=True)
