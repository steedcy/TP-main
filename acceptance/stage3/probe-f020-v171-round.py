"""F020 independent HTTP/SQL/protocol full round. Synthetic model/devices only.
Run after start-f020-v171-jar.py and controlled-model fixture; leaves adapters
alive for browser work until .local-test/f020-finish exists. No product edits.
"""
import importlib.util,json,time,copy,threading,traceback,hashlib
from pathlib import Path
from urllib.parse import urlencode
R=Path(__file__).resolve().parents[2];S=R/'acceptance/stage3'
sp=importlib.util.spec_from_file_location('h',S/'probe-f020-v171-helpers.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
q=h.q;m=h.m;SC=m.SC
def raw(path,body=None,method='POST',api=None):return m.p.raw(api or q.op,path,body,method)
def cfg(row,**kw):h.cfgcase(row,**kw)
def save():q.save()
def capture(row,key='after'):
 o=q.observe(row['taskId']);o['audit']=m.rows(f"select * from {SC}.operation_logs where operation_target like {m.lit(o['task']['taskCode']+'%')} order by id")
 row[key]=o;save();return o
def new(name,options=None,steps=None):
 marker='F171_'+name.upper().replace('-','_')
 q.cases[marker]={'steps':steps or [h.st()],**(options or {})};(R/'.local-test/f020-v171-cases.json').write_text(json.dumps(q.cases),encoding='utf8')
 body={'taskGoal':marker+' synthetic navigation to F2_TEST_GATE','taskFamily':q.family,'sceneParams':{'targetLocation':'F2_TEST_GATE'}}
 ret=raw('/tasks',body);tid=int(m.sql(f"select id from {SC}.tasks where task_goal={m.lit(body['taskGoal'])} order by id desc limit 1"))
 row={'name':name,'taskId':tid,'request':body,'response':ret};q.tasks.append(tid);q.ev['cases'].append(row);capture(row,'initial');return row
def pending(name):
 h.reset();return new(name,{'planHttpStatus':503})
def act(row,action,reason='Synthetic F020 operator decision',**kw):
 body={'action':action,**kw}
 if reason is not None:body['reason']=reason
 ret=raw(f"/tasks/{row['taskId']}/manual-actions",body);row.setdefault('actions',[]).append({'request':body,'response':ret});save();return ret
def auditdetail(a):
 d=a.get('detail');return json.loads(d) if isinstance(d,str) else (d or {})
def logchecks(o,reason,typ='TASK_MANUAL_ACTION'):
 logs=[a for a in o['audit'] if a['operation_type']==typ];a=logs[-1] if logs else {};d=auditdetail(a)
 return {'auditPresent':bool(logs),'auditActorTimeResult':bool(a.get('user_id')) and bool(a.get('username')) and bool(a.get('created_at')) and bool(a.get('operation_result')),'auditReason':d.get('reason')==reason}
def finish(row):
 o=h.finish(row);return capture(row)
def record(row,checks):q.record(row,checks)
def finishcase(row):q.terminate(row)
def change_model(row,**kw):cfg(row,planHttpStatus=200,**kw)
def baseline():
 h.reset();t=q.cfg('/baseline-templates','POST',{'templateName':'G171 F020 baseline '+str(time.time_ns()),'templateIntent':q.family,'inputParams':q.definitionBody['sceneParams'],'steps':[{'capabilityType':'CAP_NAVIGATION','paramMapping':[{'target':'targetLocation','source':'TEMPLATE_INPUT.targetLocation'}],'stepTimeout':180,'completionCondition':'routeGenerated=true'}]})
 q.templates.append(t['id']);save();ret=q.cfg(f"/baseline-templates/{t['id']}/dry-run",'POST',{'inputParams':{'targetLocation':'F2_TEST_GATE'},'simulatedDevices':[{'stepSeq':1,'agentId':q.devices[0].agent}]})
 row={'name':'baseline-publish-trial','taskId':ret['taskId']};q.tasks.append(row['taskId']);q.ev['cases'].append(row);o=finish(row);record(row,{'realTrialComplete':o['task']['status']=='COMPLETED'});q.cfg(f"/baseline-templates/{t['id']}/enable",'POST');return t
def checks_no_commands(o):return not o['commandRows']
def manual_paths():
 row=pending('mark-failed-boundaries');before=capture(row,'beforeInvalid');row['invalid']=[]
 for reason in [None,'','   ','x'*201]:row['invalid'].append({'reason':reason,'response':act(row,'MARK_FAILED',reason)})
 mid=capture(row,'afterInvalid');reason='F020 explicit failure reason';ret=act(row,'MARK_FAILED',reason);o=capture(row)
 record(row,{'initialManual':before['task']['status']=='PENDING_MANUAL','invalid400':all(x['response']['http']==400 for x in row['invalid']),'invalidNoMutation':mid['task']==before['task'] and mid['plans']==before['plans'] and mid['events']==before['events'],'failedTerminal':ret['http']==200 and o['task']['status']=='FAILED','failureReason':reason in o['task']['failureReason'],'eventReason':any(reason in (e.get('detailSummary') or '') and e.get('reasonCode')=='MANUAL_MARK_FAILED' for e in o['events']),**logchecks(o,reason)})
 row['terminalReject']=[act(row,a,'terminal invalid') for a in ['SWITCH_TO_BASELINE','RETRY_PLANNING','MARK_FAILED']];row['terminateReject']=raw(f"/tasks/{row['taskId']}/terminate",{'reason':'terminal invalid','confirmed':True});save()
 for name,action,reason in [('retry-valid','RETRY_PLANNING','F020 valid retry reason'),('retry-no-reason','RETRY_PLANNING',None)]:
  row=pending(name);change_model(row);ret=act(row,action,reason);o=capture(row,'afterAction');end=finish(row)
  record(row,{'action200':ret['http']==200,'newAutonomous':len(o['plans'])>=1 and o['plans'][-1]['source']=='AUTONOMOUS','threeValidatorsPass':all(o['plans'][-1][x]=='PASS' for x in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']),'supervisionBeforeDispatch':any(e['eventType']=='SUPERVISION_JUDGED' for e in o['events']),'resumedAndCompleted':end['task']['status']=='COMPLETED',**logchecks(o,reason),'reasonRecordedNonempty':bool(auditdetail(o['audit'][-1]).get('reason'))})
def protections():
 # Each rejected validator/supervision/force branch has its own task.
 for mode in ['structure','capability','constraint','high','force','missing-info']:
  row=pending('retry-reject-'+mode);st=h.st()
  if mode=='structure':st.pop('stepGoal')
  if mode=='capability':st['capabilityType']='CAP_F020_UNKNOWN'
  if mode=='constraint':st['inputParams']={'targetLocation':'F2_TEST_GATE','waypoint':[1,2]}
  change_model(row,steps=[st],confidence=.79 if mode=='high' else .99,diverse=mode=='high')
  if mode=='missing-info':
   # Explicit synthetic missing-info persisted fixture, not a natural 3-round claim.
   m.sql(f"update {SC}.tasks set missing_info_questions='[\"Synthetic unresolved destination\"]'::json where id={row['taskId']}")
  before=capture(row,'beforeAction');ret=act(row,'FORCE_EXECUTE' if mode=='force' else 'RETRY_PLANNING','F020 blocked '+mode);o=capture(row)
  c={'manualRetained':o['task']['status']=='PENDING_MANUAL','noCommands':checks_no_commands(o),'historyRetained':o['task']['taskGoal']==before['task']['taskGoal']}
  if mode in ['structure','capability','constraint']:c.update(rejectedPlan=len(o['plans'])==1 and o['plans'][-1][mode+'CheckResult']=='FAIL',noSupervision=not any(e['eventType']=='SUPERVISION_JUDGED' for e in o['events']))
  if mode=='high':c.update(supervisionHigh=any(p['riskLevel']=='HIGH' for p in o['plans']),riskReason=bool(o['task']['failureReason']))
  if mode in ['force','missing-info']:c['rejected4xx']=400<=ret['http']<500
  record(row,c);finishcase(row)
def switch_paths(t):
 for name,reason in [('switch-valid','F020 valid baseline reason'),('switch-no-reason',None)]:
  q.cfg(f"/baseline-templates/{t['id']}/disable",'POST');row=pending(name);q.cfg(f"/baseline-templates/{t['id']}/enable",'POST');ret=act(row,'SWITCH_TO_BASELINE',reason);o=capture(row,'afterAction');end=finish(row)
  record(row,{'action200':ret['http']==200,'baselineSource':o['plans'][-1]['source']=='BASELINE_TEMPLATE','templateIdentity':bool(o['plans'][-1].get('baselineTemplateId')),'threePass':all(o['plans'][-1][x]=='PASS' for x in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']),'resumedAndCompleted':end['task']['status']=='COMPLETED',**logchecks(o,reason),'reasonRecordedNonempty':bool(auditdetail(o['audit'][-1]).get('reason'))})
 # Template was published by real trial; corrupt ONLY GPT owned template payload
 # to exercise each post-publication runtime validator. Restore exact JSON finally.
 original=m.sql(f"select steps::text from {SC}.baseline_templates where id={t['id']}")
 try:
  for mode in ['structure','capability','constraint']:
   q.cfg(f"/baseline-templates/{t['id']}/disable",'POST');row=pending('switch-reject-'+mode);steps=json.loads(original)
   if mode=='structure':steps=[]
   if mode=='capability':steps[0]['capabilityType']='CAP_F020_UNKNOWN'
   if mode=='constraint':steps[0]['paramMapping']=[{'target':'targetLocation','source':'TEMPLATE_INPUT.targetLocation'},{'target':'waypoint','source':'[1,2]'}]
   m.sql(f"update {SC}.baseline_templates set steps={m.lit(json.dumps(steps))}::json,template_status='ENABLED' where id={t['id']}")
   ret=act(row,'SWITCH_TO_BASELINE','F020 invalid baseline '+mode);o=capture(row);record(row,{'manualRetained':o['task']['status']=='PENDING_MANUAL','noCommands':checks_no_commands(o),'failureExplained':bool(o['task']['failureReason']),'validatorRejected':any(p.get(mode+'CheckResult')=='FAIL' for p in o['plans'])});finishcase(row)
 finally:m.sql(f"update {SC}.baseline_templates set steps={m.lit(original)}::json,template_status='DISABLED' where id={t['id']}")
def lifecycle_and_terminate():
 h.reset();row=new('normal-two-step',steps=[h.st(),h.st(2)]);o=capture(row,'pending');d,msg=h.accept(row);o=capture(row,'executing');h.feed(row,d,msg);end=finish(row)
 record(row,{'twoStepCompleted':end['task']['status']=='COMPLETED','pendingObserved':row['pending']['task']['status']=='PENDING_ASSIGNMENT','executingObserved':o['task']['status']=='EXECUTING','goalPreserved':end['task']['taskGoal']==row['request']['taskGoal'],'orderedEvents':all(a['occurredAt']<=b['occurredAt'] for a,b in zip(end['events'],end['events'][1:])),'allocationsAndCommands':len(end['assignments'])==2 and all(a['stepStatus']=='COMPLETED' for a in end['assignments']) and len(end['commandRows'])>=4})
 row['terminalReject']=[act(row,a,'terminal invalid') for a in ['SWITCH_TO_BASELINE','RETRY_PLANNING','MARK_FAILED']];row['terminateReject']=raw(f"/tasks/{row['taskId']}/terminate",{'reason':'terminal invalid','confirmed':True});save()
 h.reset();row=new('terminate-executing',steps=[h.st(),h.st(2)]);d,msg=h.accept(row);before=capture(row,'beforeTermination');reason='F020 terminate executing reason';row['invalidConfirm']=raw(f"/tasks/{row['taskId']}/terminate",{'reason':reason,'confirmed':False});row['invalidReason']=raw(f"/tasks/{row['taskId']}/terminate",{'reason':' ','confirmed':True});row['terminate']=raw(f"/tasks/{row['taskId']}/terminate",{'reason':reason,'confirmed':True});o=capture(row,'afterTermination');d.state['workStatus']='IDLE';d.heartbeat();end=capture(row)
 logs=[a for a in end['audit'] if a['operation_type']=='TASK_TERMINATE'];detail=auditdetail(logs[-1]) if logs else {}
 record(row,{'confirmationRequired':row['invalidConfirm']['http']==400,'reasonRequired':row['invalidReason']['http']==400,'terminal':o['task']['status']=='MANUAL_TERMINATED','cancellationPersisted':any(c['command_type']=='TASK_CANCEL' for c in end['commandRows']),'safeRelease':all(a.get('current_task_id')!=row['taskId'] for a in end['agentRows']),'laterStepFrozen':any(a['stepSeq']==2 and a['stepStatus']=='FROZEN' for a in end['assignments']),'auditDeviceSummary':bool(detail.get('deviceCancelResults')),'previousState':detail.get('previousStatus')=='EXECUTING',**logchecks(end,reason,'TASK_TERMINATE')})
def search_and_immutability():
 row={'name':'search-auth-immutability'};q.ev['cases'].append(row);row['queries']=[]
 def query(params,expected):
  ret=q.op('/tasks?'+urlencode(params));row['queries'].append({'params':params,'response':ret,'expectedIds':expected});return [x['id'] for x in ret['content']]==expected
 fixtures=m.rows(f"select id,task_code,task_goal,status,task_family,created_at from {SC}.tasks where task_goal like 'F171_%' and is_dry_run=false order by id desc")
 checks={}
 for params,label,pred in [({'goalKeyword':'f171_'},'caseInsensitive',lambda r:'f171_' in r['task_goal'].lower()),({'goalKeyword':'  F171_  '},'trimmed',lambda r:True),({'goalKeyword':'nonexistent-F020-000'},'empty',lambda r:False),({'goalKeyword':'F171_','status':'COMPLETED','taskFamily':q.family},'combined',lambda r:r['status']=='COMPLETED')]:
  expected=[r['id'] for r in fixtures if pred(r)][:20];checks[label]=query(params,expected)
 first=fixtures[0];checks['exactCode']=query({'taskCode':first['task_code']},[first['id']]);checks['timeInclusive']=query({'goalKeyword':'F171_','createdFrom':first['created_at'],'createdTo':first['created_at']},[first['id']])
 checks['pagesDisjoint']=query({'goalKeyword':'F171_','page':1,'size':3},[r['id'] for r in fixtures[:3]]) and query({'goalKeyword':'F171_','page':2,'size':3},[r['id'] for r in fixtures[3:6]])
 tid=first['id'];row['taskId']=tid;before=q.op(f'/tasks/{tid}/events');row['missing']=raw('/tasks/999999999',method='GET');row['forbidden']=raw(f'/tasks/{tid}',method='GET',api=q.cfg);row['immutable']=[]
 eventid=before[0]['id']
 for path in [f'/tasks/{tid}/events/{eventid}',f'/task-events/{eventid}']:
  for method in ['PUT','DELETE']:row['immutable'].append({'path':path,'method':method,'response':raw(path,{'detailSummary':'MUTATION_FORBIDDEN'},method)})
 after=q.op(f'/tasks/{tid}/events');row['eventsBefore']=before;row['eventsAfter']=after
 checks.update(missing404=row['missing']['http']==404,forbidden403=row['forbidden']['http']==403,immutable=before==after,unsupportedExplicit=all(x['response']['http'] in [404,405] for x in row['immutable']))
 row['accessAudit']=m.rows(f"select * from {SC}.operation_logs where operation_type='ACCESS_DENIED' and operation_target like '%tasks/{tid}%' order by id desc")
 checks['accessAudit']=bool(row['accessAudit']);record(row,checks)
 # F028/DEF061 affected generic exception handler adjacency, no F028 acceptance.
 audit=first['task_code'];logs=m.rows(f"select * from {SC}.operation_logs where operation_target like {m.lit(audit+'%')} order by id")
 if logs:
  admin=m.l.API('系统管理员');aid=logs[-1]['id'];before=m.rows(f"select * from {SC}.operation_logs where id={aid}");r={'name':'audit-immutability-adjacency','logId':aid,'responses':[raw(f'/operation-logs/{aid}',{},x,admin) for x in ['PUT','DELETE']]};q.ev['cases'].append(r);r['before']=before;r['after']=m.rows(f"select * from {SC}.operation_logs where id={aid}");record(r,{'immutable':r['before']==r['after'],'explicit404or405':all(x['http'] in [404,405] for x in r['responses'])})
def ui_fixtures():
 # Keep independent waiting/manual/executing tasks for browser actions; adapters
 # and heartbeat continue while the browser uses public UI/API, no fake UI data.
 ui={}
 for name in ['ui-mark-failed','ui-terminate','ui-retry','ui-switch']:
  q.cfg(f"/baseline-templates/{q.templates[0]}/disable",'POST');row=pending(name);change_model(row);ui[name]=row['taskId']
 q.cfg(f"/baseline-templates/{q.templates[0]}/enable",'POST')
 h.reset();row=new('ui-refresh',steps=[h.st(timeout=600)]);d,msg=h.accept(row);ui['ui-refresh']=row['taskId'];q.ev['uiFixtures']=ui;save();(R/'.local-test/f020-ui-ready.json').write_text(json.dumps(ui))
 while not (R/'.local-test/f020-finish').exists():
  command=R/'.local-test/f020-command.json'
  if command.exists():
   cmd=json.loads(command.read_text());command.unlink();target=next(x for x in q.ev['cases'] if x.get('taskId')==cmd['taskId'])
   if cmd['action']=='complete':
    if cmd['taskId']==row['taskId']:h.feed(row,d,msg)
    else:finish(target)
    capture(target,'afterBrowserComplete')
  time.sleep(.2)
 for n,tid in ui.items():
  r=next(x for x in q.ev['cases'] if x.get('taskId')==tid);capture(r,'afterBrowser')
def main():
 try:
  q.setup();q.ev['rulesBefore']=q.cfg('/risk-rules');q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
  for name,fn in [('manual-paths',manual_paths),('protections',protections),('lifecycle-termination',lifecycle_and_terminate)]:q.run(name,fn)
  t=baseline();q.run('switch-paths',lambda:switch_paths(t));q.run('search-immutability',search_and_immutability);q.run('ui-fixtures',ui_fixtures)
 finally:
  for tid in q.templates:
   try:q.cfg(f'/baseline-templates/{tid}/disable','POST')
   except Exception:pass
  for r in q.ev.get('rulesBefore',[]):
   if r['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':r['enabled']})
  q.cleanup();q.ev['endedAt']=m.now();save()
if __name__=='__main__':main()
