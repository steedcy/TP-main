"""V1.172 independent F020 full round, fixed JAR/own schema/model/adapters.
Synthetic 127 catalog is query-only and explicitly separated from real lifecycle.
Keep server alive for UI until version-specific finish file arrives.
"""
import importlib.util,json,time,copy,threading
from pathlib import Path
from urllib.parse import urlencode
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('r',P/'probe-f020-v172-round.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q;h=r.h;m=r.m;SC=r.SC;R=r.R

def replanning():
 h.reset();row=r.new('lifecycle-real-replan',steps=[h.st(),h.st(2),h.st(3)]);r.cfg(row,replanSteps=[h.st(i+1) for i in range(4)])
 d,msg=h.accept(row);h.feed(row,d,msg);r.capture(row,'completedPrefix');d,msg=h.accept(row);h.failtwice(row,d,msg);r.capture(row,'candidateRecovery');backup,cmd=h.accept(row);h.failtwice(row,backup,cmd);o=r.capture(row,'afterReplan');end=r.finish(row)
 r.record(row,{'realRecoveryThenReplan':any(e['eventType']=='EXCEPTION_RECOVERY_FAILED' for e in o['events']) and any(e['eventType']=='REPLANNING_TRIGGERED' for e in o['events']),'prefixPreserved':any(a['stepSeq']==1 and a['stepStatus']=='COMPLETED' for a in o['assignments']),'twoVersions':len(end['plans'])==2,'newPlanAllChecks':all(end['plans'][-1][k]=='PASS' for k in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']),'reasonAndOriginalGoal':bool(end['task']['replanningReason']) and end['task']['taskGoal']==row['request']['taskGoal'],'completed':end['task']['status']=='COMPLETED','orderedCompleteTimeline':all(a['occurredAt']<=b['occurredAt'] for a,b in zip(end['events'],end['events'][1:])) and any(e['eventType']=='TASK_COMPLETED' for e in end['events'])})

def missing():
 q.family='SPECIAL_PASSENGER_SERVICE';row=r.new('natural-three-clarifications',{'goalOverride':{'infoComplete':False,'origin':None,'destination':None,'missingInfoQuestions':['Synthetic assistance type required','Synthetic origin required','Synthetic destination required']}})
 row['clarifications']=[]
 for _ in range(3):
  task=q.op(f"/tasks/{row['taskId']}");questions=task.get('missingInfoQuestions') or []
  row['clarifications'].append({'questions':questions,'response':r.raw(f"/tasks/{row['taskId']}/clarify",{'answers':{x:'Synthetic still unknown' for x in questions}})})
 o=r.capture(row,'afterThree');row['manualRejects']=[r.act(row,a,'F020 no missing information override') for a in ['SWITCH_TO_BASELINE','RETRY_PLANNING']];end=r.capture(row)
 r.record(row,{'threeRoundsSent':len(row['clarifications'])==3 and all(x['response']['http']==200 for x in row['clarifications']),'actualPendingManual':o['task']['status']=='PENDING_MANUAL','missingQuestionsRetained':len(o['task'].get('missingInfoQuestions') or [])>=3,'bothManualActionsBlocked':all(x['http']==400 for x in row['manualRejects']),'noPlanNoCommands':not end['plans'] and not end['commandRows'],'noDefaultInformationInjected':end['task'].get('sceneParams',{}).get('assistanceType') is None})

def reason_negatives(row,action):
 before=r.capture(row,'beforeInvalid');row['reasonNegatives']=[]
 for reason in [None,'','   ','x'*201]:
  ret=r.act(row,action,reason);row['reasonNegatives'].append({'reason':reason,'response':ret})
 after=r.capture(row,'afterInvalid')
 return {'missingBlank400MissingParameter':all(x['response']['http']==400 and x['response']['body']['code']==3000 for x in row['reasonNegatives'][:3]),'over200Rejected':row['reasonNegatives'][-1]['response']['http']==400,'noInvalidBusinessMutation':all(before[k]==after[k] for k in ['task','plans','events','assignments','commandRows','audit'])}

def mark_retry():
 row=r.pending('mark-failed-boundaries');checks=reason_negatives(row,'MARK_FAILED');reason='M'*200;ret=r.act(row,'MARK_FAILED',reason);o=r.capture(row)
 checks.update(legal200chars=ret['http']==200 and o['task']['status']=='FAILED',eventHasActualReason=any(reason in (e.get('detailSummary') or '') for e in o['events']),**r.logchecks(o,reason));r.record(row,checks)
 row=r.pending('retry-original-062-counterexample');checks=reason_negatives(row,'RETRY_PLANNING');r.change_model(row);ret=r.act(row,'RETRY_PLANNING',' R ');o=r.capture(row,'afterAction');end=r.finish(row)
 checks.update(legal1charTrimmed=ret['http']==200,newAutonomous=o['plans'][-1]['source']=='AUTONOMOUS',threeChecksPass=all(o['plans'][-1][k]=='PASS' for k in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']),supervisionJudged=any(e['eventType']=='SUPERVISION_JUDGED' for e in o['events']),completed=end['task']['status']=='COMPLETED',eventReason=any('原因: R' in (e.get('detailSummary') or '') for e in o['events']),**r.logchecks(o,'R'));r.record(row,checks)

def prepare_waiting():
 rows={}
 for name in ['switch-original-062-counterexample','switch-invalid-structure','switch-invalid-capability','switch-invalid-constraint','ui-mark-failed','ui-terminate','ui-retry','ui-switch']:
  rows[name]=r.pending(name)
  if name.startswith('ui-'):r.change_model(rows[name])
 return rows

def baseline_cases(rows,t):
 row=rows['switch-original-062-counterexample'];checks=reason_negatives(row,'SWITCH_TO_BASELINE');reason='S'*200;ret=r.act(row,'SWITCH_TO_BASELINE','  '+reason+'  ')
 # DTO length includes outer spaces: this 204-char request is an invalid control;
 # legal exact200 follows, never attribute a DTO rejection to product failure.
 row['rawLength204Control']=ret
 if ret['http']==400:ret=r.act(row,'SWITCH_TO_BASELINE',reason)
 o=r.capture(row,'afterAction');end=r.finish(row);checks.update(legal200chars=ret['http']==200,baselineSource=o['plans'][-1]['source']=='BASELINE_TEMPLATE',threeChecksPass=all(o['plans'][-1][k]=='PASS' for k in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']),completed=end['task']['status']=='COMPLETED',eventReason=any(reason in (e.get('detailSummary') or '') for e in o['events']),**r.logchecks(o,reason));r.record(row,checks)
 original=m.sql(f"select steps::text from {SC}.baseline_templates where id={t['id']}")
 try:
  for mode in ['structure','capability','constraint']:
   row=rows['switch-invalid-'+mode];h.reset();steps=json.loads(original)
   if mode=='structure':steps=[]
   if mode=='capability':steps[0]['capabilityType']='CAP_F020_UNKNOWN'
   if mode=='constraint':steps[0]['inputParams']={'targetLocation':'F2_TEST_GATE','waypoint':[1,2]}
   m.sql(f"update {SC}.baseline_templates set steps={m.lit(json.dumps(steps))}::json where id={t['id']}");r.act(row,'SWITCH_TO_BASELINE','F020 reject '+mode);o=r.capture(row);r.record(row,{'validatorRejected':any(p[mode+'CheckResult']=='FAIL' for p in o['plans']),'manualRetained':o['task']['status']=='PENDING_MANUAL','noCommands':not o['commandRows'],'failureExplained':bool(o['task']['failureReason'])});r.finishcase(row)
 finally:m.sql(f"update {SC}.baseline_templates set steps={m.lit(original)}::json where id={t['id']}")
 h.reset();row=r.new('high-auto-baseline-failure',{'confidence':.79,'diverse':True});o=r.capture(row,'beforeExecution');d,msg=h.accept(row);h.failtwice(row,d,msg);b,cmd=h.accept(row);h.failtwice(row,b,cmd);end=r.capture(row)
 r.record(row,{'autonomousHigh':o['plans'][0]['riskLevel']=='HIGH','autoBaseline':o['plans'][-1]['source']=='BASELINE_TEMPLATE','threeChecksPass':all(o['plans'][-1][k]=='PASS' for k in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']),'actualPendingManual':end['task']['status']=='PENDING_MANUAL','pendingEvent':any(e['eventType']=='TASK_PENDING_MANUAL' for e in end['events']),'noFakeRecovery':not any(e['eventType']=='EXCEPTION_RECOVERED' for e in end['events'])});r.finishcase(row)

def catalog():
 row={'name':'127-query-catalog','fixtureLevel':'SQL seeded query/filter and status-gate fixtures only; not natural lifecycle','rows':[],'queries':[],'gates':[]};q.ev['cases'].append(row)
 states=['PLANNING','SUPERVISING','PENDING_ASSIGNMENT','DOWNGRADING','EXECUTING','COMPLETED','FAILED','PENDING_MANUAL','MANUAL_TERMINATED']
 for i in range(127):
  code='G172C-'+str(time.time_ns());goal=f"F172_CATALOG_{i:03} literal%_\\quote'";status=states[i%9]
  result=m.sql(f"insert into {SC}.tasks(task_code,task_goal,task_family,scene_params,status,replan_used,is_dry_run,created_at,updated_at,created_by) values({m.lit(code)},{m.lit(goal)},{m.lit(q.family)},'{{}}'::json,{m.lit(status)},false,false,date_trunc('day',now())+interval '8 hour'+interval '{i} minute',now(),'GPT Synthetic Operator') returning id");tid=int(result.splitlines()[0]);q.tasks.append(tid);row['rows'].append({'id':tid,'code':code,'goal':goal,'status':status})
 old=int(m.sql(f"insert into {SC}.tasks(task_code,task_goal,task_family,status,replan_used,is_dry_run,created_at,updated_at,created_by) values('G172OLD-{time.time_ns()}','F172_OLD_CATALOG',{m.lit(q.family)},'COMPLETED',false,false,date_trunc('day',now())-interval '9 hour',now(),'GPT Synthetic Operator') returning id").splitlines()[0]);q.tasks.append(old);row['oldId']=old;checks={}
 for status in states:
  ret=q.op('/tasks?'+urlencode({'goalKeyword':'F172_CATALOG_','status':status,'size':100}));row['queries'].append({'status':status,'response':ret});checks['filter-'+status]=sorted(x['id'] for x in ret['content'])==sorted(x['id'] for x in row['rows'] if x['status']==status)
  if status!='PENDING_MANUAL':
   tid=next(x['id'] for x in row['rows'] if x['status']==status);before=q.op(f'/tasks/{tid}');events=q.op(f'/tasks/{tid}/events');ret=[r.raw(f'/tasks/{tid}/manual-actions',{'action':a,'reason':'F172 invalid status control'}) for a in ['SWITCH_TO_BASELINE','RETRY_PLANNING','MARK_FAILED']];row['gates'].append({'status':status,'taskId':tid,'responses':ret});checks['gate-'+status]=all(400<=z['http']<500 for z in ret) and q.op(f'/tasks/{tid}')==before and q.op(f'/tasks/{tid}/events')==events
 for params,key,expected in [({'goalKeyword':row['rows'][0]['goal'],'size':20},'literalWildcards',[row['rows'][0]['id']]),({'goalKeyword':'F172_','createdFrom':'2026-11-06T08:00:00','createdTo':'2026-11-06T08:00:00','size':20},'timeClosedBoundary',[row['rows'][0]['id']]),({'goalKeyword':'F172_CATALOG_','taskFamily':'EXT_F172_NONEXISTENT','size':20},'emptyConjunction',[])]:
  ret=q.op('/tasks?'+urlencode(params));row['queries'].append({'params':params,'response':ret});checks[key]=sorted(x['id'] for x in ret['content'])==expected
 ret=q.op('/tasks?'+urlencode({'goalKeyword':'F172_CATALOG_','page':1,'size':20}));row['page1']=ret;checks['exact127']=ret['totalElements']==127 and ret.get('total')==127
 q.ev['catalog']={'taskIds':[x['id'] for x in row['rows']],'oldId':old,'family':q.family};r.record(row,checks)

def ui_wait(rows):
 h.reset();row=r.new('ui-refresh',steps=[h.st(timeout=600)]);d,msg=h.accept(row);ids={n:x['taskId'] for n,x in rows.items() if n.startswith('ui-')};ids['ui-refresh']=row['taskId'];q.ev['uiFixtures']=ids;q.save()
 (R/'.local-test/f020-v172-ui-ready.json').write_text(json.dumps({'tasks':ids,'catalog':q.ev['catalog'],'cases':{x['name']:x.get('taskId') for x in q.ev['cases']}}),encoding='utf8')
 while not (R/'.local-test/f020-v172-finish').exists():
  command=R/'.local-test/f020-v172-command.json'
  if command.exists():
   cmd=json.loads(command.read_text());command.unlink();target=next(x for x in q.ev['cases'] if x.get('taskId')==cmd['taskId'])
   if cmd['action']=='complete':
    if cmd['taskId']==row['taskId']:h.feed(row,d,msg)
    else:r.finish(target)
    r.capture(target,'afterBrowserComplete')
    (R/f".local-test/f020-v172-command-done-{cmd['taskId']}.json").write_text(json.dumps({'taskId':cmd['taskId'],'at':m.now()}))
  time.sleep(.2)
 for n,tid in ids.items():
  target=next(x for x in q.ev['cases'] if x.get('taskId')==tid);o=r.capture(target,'afterBrowser');expected={'ui-mark-failed':'FAILED','ui-terminate':'MANUAL_TERMINATED','ui-retry':'COMPLETED','ui-switch':'COMPLETED','ui-refresh':'COMPLETED'}[n];checks={'expectedState':o['task']['status']==expected}
  if n!='ui-refresh':checks.update(r.logchecks(o,{'ui-mark-failed':'F172 browser mark reason','ui-terminate':'F172 browser terminate reason','ui-retry':'F172 browser retry reason','ui-switch':'F172 browser switch reason'}[n],'TASK_TERMINATE' if n=='ui-terminate' else 'TASK_MANUAL_ACTION'))
  r.record(target,checks)

def main():
 try:
  assert not (R/'.local-test/f020-v172-finish').exists(),'use fresh version-specific control file'
  q.setup();q.ev['rulesBefore']=q.cfg('/risk-rules');q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
  for name,fn in [('manual-reasons',mark_retry),('all-autonomous-protections',r.protections),('normal-termination',r.lifecycle_and_terminate),('real-replan',replanning)]:q.run(name,fn)
  rows=prepare_waiting();t=r.baseline();q.run('all-baseline-branches',lambda:baseline_cases(rows,t));q.run('search-auth-immutable',r.search_and_immutability);q.run('127-catalog',catalog)
  family=q.family;q.run('three-clarification-counterexample',missing);q.family=family
  q.run('browser-observations',lambda:ui_wait(rows))
 finally:
  for tid in q.templates:
   try:q.cfg(f'/baseline-templates/{tid}/disable','POST')
   except Exception:pass
  for rule in q.ev.get('rulesBefore',[]):
   if rule['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':rule['enabled']})
  q.cleanup();q.ev['endedAt']=m.now();q.save()
if __name__=='__main__':main()
