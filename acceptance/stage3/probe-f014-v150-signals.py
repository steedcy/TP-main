"""Single/combined model risk tags through the real isolated backend and SQL."""
import importlib.util,json,time
from pathlib import Path
r=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('p',r/'acceptance/stage3/probe-f014-v150.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
cfg=p.l.API('配置管理员');op=p.l.API('运行操作员');ev=p.metadata();ev['cases']=[]
family='EXT_0FA30230';ev['ruleBefore']=next(x for x in cfg('/risk-rules') if x['ruleCode']=='RULE_RESOURCE_CRITICAL')
ev['definitionBefore']=cfg('/task-definitions/17');cfg('/task-definitions/17/enable','POST')
cases={'F150_DIVERSE_ONLY':{'steps':[p.step()],'confidence':.99,'diverse':True},'F150_LOW_ONLY':{'steps':[p.step()],'confidence':.79,'diverse':False},'F150_BOUNDARY_DIVERSE':{'steps':[p.step()],'confidence':.8,'diverse':True},'F150_COMBINED':{'steps':[p.step()],'confidence':.79,'diverse':True}}
(r/'.local-test/f014-v150-cases.json').write_text(json.dumps(cases),encoding='utf-8')
try:
 cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
 for marker in cases:
  req={'taskGoal':marker+' synthetic navigation to F2_TEST_GATE','taskFamily':family,'sceneParams':{'targetLocation':'F2_TEST_GATE'}}
  task=op('/tasks','POST',req);tid=task['id']
  for _ in range(30):
   o=p.observe(op,tid)
   if o['task']['status'] in ['COMPLETED','FAILED','PENDING_MANUAL']:break
   time.sleep(.3)
  v=o['plans'][0];e=[x for x in o['events'] if x['eventType']=='SUPERVISION_JUDGED']
  row={'name':marker,'modelResponse':cases[marker],'request':req,'observed':o,'checks':{'threePass':all(v[k]=='PASS' for k in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']),'riskExpected':v['riskLevel']==('HIGH' if marker=='F150_COMBINED' else 'LOW'),'hasSupervisionEvent':bool(e)}}
  row['persisted']=p.sql(f"select risk_level,risk_reason_code,judgment_basis,confidence,rule_set_version from {p.SC}.plan_versions where task_id={tid} order by version_no")
  row['persistedEvents']=p.sql(f"select event_type,reason_code,detail_summary from {p.SC}.task_events where task_id={tid} and event_type='SUPERVISION_JUDGED' order by id")
  if cases[marker]['diverse']:row['checks']['diverseSignalListed']='候选差异较大' in str(v['judgmentBasis']) and any('候选差异较大' in str(x.get('detailSummary','')) for x in e)
  ev['cases'].append(row);p.save('signals',ev);print(marker,tid,row['checks'],flush=True)
  if o['task']['status'] not in ['COMPLETED','FAILED','MANUAL_TERMINATED']:row['cleanupTerminate']=p.raw(op,f'/tasks/{tid}/terminate',{'reason':'F014 V150 signal fixture cleanup','confirmed':True})
finally:
 cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':ev['ruleBefore']['enabled']})
 if ev['definitionBefore']['definitionStatus']=='DISABLED':cfg('/task-definitions/17/disable','POST')
 ev['fixtureRestored']=True;p.save('signals',ev)
