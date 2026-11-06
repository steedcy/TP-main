"""Missing lifecycle/replan, baseline constraint and filter equivalence branches.
Filter catalog is explicitly seeded synthetic data, not lifecycle evidence.
"""
import os,importlib.util,json,copy,time
from pathlib import Path
from urllib.parse import urlencode
os.environ['GPT_EVIDENCE_LABEL']='final';P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('r',P/'probe-f020-v171-round.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q;h=r.h;m=r.m;SC=r.SC
def replanning():
 h.reset();row=r.new('lifecycle-real-replan',steps=[h.st(),h.st(2),h.st(3)]);r.cfg(row,replanSteps=[h.st(i+1) for i in range(4)])
 d,msg=h.accept(row);h.feed(row,d,msg);r.capture(row,'completedPrefix');d,msg=h.accept(row);h.failtwice(row,d,msg);r.capture(row,'candidateRecovery');backup,cmd=h.accept(row);h.failtwice(row,backup,cmd);o=r.capture(row,'afterReplan');end=r.finish(row)
 r.record(row,{'realRecoveryThenReplan':any(e['eventType']=='EXCEPTION_RECOVERY_FAILED' for e in o['events']) and any(e['eventType']=='REPLANNING_TRIGGERED' for e in o['events']),'prefixPreserved':any(a['stepSeq']==1 and a['stepStatus']=='COMPLETED' for a in o['assignments']),'twoVersions':len(end['plans'])==2,'newPlanAllChecks':all(end['plans'][-1][k]=='PASS' for k in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']),'reasonAndOriginalGoal':bool(end['task']['replanningReason']) and end['task']['taskGoal']==row['request']['taskGoal'],'completed':end['task']['status']=='COMPLETED','orderedCompleteTimeline':all(a['occurredAt']<=b['occurredAt'] for a,b in zip(end['events'],end['events'][1:])) and any(e['eventType']=='TASK_COMPLETED' for e in end['events'])})
def baseline_branches():
 row=r.pending('baseline-invalid-constraint-input');t=r.baseline();original=m.sql(f"select steps::text from {SC}.baseline_templates where id={t['id']}")
 try:
  steps=json.loads(original);steps[0]['inputParams']={'targetLocation':'F2_TEST_GATE','waypoint':[1,2]}
  m.sql(f"update {SC}.baseline_templates set steps={m.lit(json.dumps(steps))}::json where id={t['id']}")
  row['faultFixture']='Owned published template inputParams waypoint=[1,2], exact JSON restored; no unsupported paramMapping syntax.'
  ret=r.act(row,'SWITCH_TO_BASELINE','F020 constraint negative control');o=r.capture(row)
  r.record(row,{'constraintRejected':bool(o['plans']) and o['plans'][-1]['constraintCheckResult']=='FAIL','manualRetained':o['task']['status']=='PENDING_MANUAL','noDeviceCommand':not o['commandRows'],'failureReason':bool(o['task']['failureReason'])})
 finally:m.sql(f"update {SC}.baseline_templates set steps={m.lit(original)}::json where id={t['id']}")
 r.finishcase(row)
 h.reset();row=r.new('high-auto-baseline-failure',{'confidence':.79,'diverse':True});o=r.capture(row,'beforeExecution');d,msg=h.accept(row);h.failtwice(row,d,msg);b,cmd=h.accept(row);h.failtwice(row,b,cmd);end=r.capture(row)
 r.record(row,{'autonomousHighSupervised':o['plans'][0]['source']=='AUTONOMOUS' and o['plans'][0]['riskLevel']=='HIGH','automaticBaseline':o['plans'][-1]['source']=='BASELINE_TEMPLATE','baselineThreeChecks':all(o['plans'][-1][k]=='PASS' for k in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']),'failureManual':end['task']['status']=='PENDING_MANUAL','stateEvent':any(e['eventType']=='TASK_PENDING_MANUAL' for e in end['events']),'noFakeRecovery':not any(e['eventType']=='EXCEPTION_RECOVERED' for e in end['events']),'reasonStored':bool(end['task']['failureReason'])})
 r.finishcase(row)
def filter_catalog():
 statuses=['PLANNING','SUPERVISING','PENDING_ASSIGNMENT','DOWNGRADING','EXECUTING','COMPLETED','FAILED','PENDING_MANUAL','MANUAL_TERMINATED'];ids=[];rows=[]
 for i,status in enumerate(statuses):
  code='GPTF020-CATALOG-'+str(time.time_ns());goal=f"F171_CATALOG_{i} literal%_\\quote' boundary"
  tid=int(m.sql(f"insert into {SC}.tasks(task_code,task_goal,task_family,scene_params,status,replan_used,is_dry_run,created_at,updated_at,created_by) values({m.lit(code)},{m.lit(goal)},{m.lit(q.family)},'{{}}'::json,{m.lit(status)},false,false,date_trunc('day',now())+interval '{8+i} hour',now(),3) returning id"));q.tasks.append(tid);ids.append(tid);rows.append({'id':tid,'status':status,'goal':goal,'code':code})
 old=int(m.sql(f"insert into {SC}.tasks(task_code,task_goal,task_family,scene_params,status,replan_used,is_dry_run,created_at,updated_at,created_by) values('GPTF020-OLD-{time.time_ns()}','F171_CATALOG_OLD',{m.lit(q.family)},'{{}}'::json,'COMPLETED',false,false,date_trunc('day',now())-interval '9 hour',now(),3) returning id"));q.tasks.append(old)
 row={'name':'nine-state-filter-catalog','fixtureLevel':'SQL seeded task catalog for filter/query only; no real lifecycle claim','taskIds':ids+[old],'queries':[]};q.ev['cases'].append(row);checks={}
 for x in rows:
  params={'goalKeyword':'F171_CATALOG_','taskFamily':q.family,'status':x['status'],'size':100};ret=q.op('/tasks?'+urlencode(params));row['queries'].append({'params':params,'response':ret});expected=[z['id'] for z in rows if z['status']==x['status']]+([old] if x['status']=='COMPLETED' else []);checks[x['status']]=sorted(z['id'] for z in ret['content'])==sorted(expected)
 today='2026-11-06';ret=q.op('/tasks?'+urlencode({'goalKeyword':'F171_CATALOG_','createdFrom':today+'T00:00:00','createdTo':today+'T23:59:59','size':100}));row['todayResponse']=ret;checks['todayExcludesYesterday']=sorted(z['id'] for z in ret['content'])==sorted(ids)
 ret=q.op('/tasks?'+urlencode({'goalKeyword':"literal%_\\quote'",'size':100}));row['literalResponse']=ret;checks['sqlWildcardsLiteral']=sorted(z['id'] for z in ret['content'])==sorted(ids)
 r.record(row,checks)
try:
 q.setup();q.ev['rulesBefore']=q.cfg('/risk-rules');q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
 for name,fn in [('real-replan',replanning),('baseline-branches',baseline_branches),('filter-catalog',filter_catalog)]:q.run(name,fn)
finally:
 for tid in q.templates:
  try:q.cfg(f'/baseline-templates/{tid}/disable','POST')
  except Exception:pass
 for rr in q.ev.get('rulesBefore',[]):
  if rr['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':rr['enabled']})
 q.cleanup();q.ev['endedAt']=m.now();q.save()
