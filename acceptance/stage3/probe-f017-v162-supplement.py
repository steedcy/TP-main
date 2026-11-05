"""Corrected missing assertions and independent business branches; fixed V1.162.
Initial fixture diagnostics remain intact in the main evidence. All SQL uses UTF-8
stdin. Frozen-plan injections are scoped to own tasks to reach dispatch guard.
"""
import importlib.util,json,time,copy,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('m',Path(__file__).with_name('probe-f017-v162.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.OUT=m.output_path('SRS_F017-V1.162-supplement-20261105.json')
q=m.Probe()
# Recover task IDs created before the initial Windows SQL argv encoding failure.
all_prior=m.rows(f"select row_to_json(x)::text from (select id,status,task_goal from {m.SC}.tasks where id between 433 and 455 order by id) x")
q.ev['priorRoundTaskRecovery']=all_prior
for task in all_prior:
 if task['status'] not in ['COMPLETED','FAILED','MANUAL_TERMINATED']:
  q.ev.setdefault('priorTermination',[]).append({'taskId':task['id'],'response':m.p.raw(q.op,f'/tasks/{task["id"]}/terminate',{'reason':'Reconcile scoped initial encoding diagnostic task','confirmed':True})})
q.save();q.setup();rules=q.cfg('/risk-rules');q.ev['rulesBefore']=rules;q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
caps_before={}
def st(seq=1,condition='routeGenerated=true',cap='CAP_NAVIGATION',goal='前往区域',params=None,timeout=180):
 x=m.p.step(seq=seq,cap=cap,params=params);x.update(completionCondition=condition,stepGoal=goal,stepTimeout=timeout);return x
def wait(fn,timeout=15):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  value=fn()
  if value:return value
  time.sleep(.08)
 raise TimeoutError('Expected protocol/DB observation missing')
def message(row,kind='EXECUTE_CAPABILITY',seq=1,attempt=0):
 code=q.op(f'/tasks/{row["taskId"]}')['taskCode']
 def found():
  candidates=[(d,x['message']) for d in q.devices for x in d.messages_for(code,kind) if x['message']['stepSeq']==seq and x['message']['attemptNo']==attempt]
  return candidates[-1] if candidates else None
 return wait(found)
def accept(row,seq=1):
 d,offer=message(row,'TASK_ACCEPT',seq);res=q.response(d,offer);row.setdefault('acceptResponses',[]).append(res);return message(row,seq=seq)
def feed(row,d,msg,output,result='SUCCESS',reason=None):
 body={'commandId':msg['commandId'],'attemptNo':msg['attemptNo'],'executionResult':result,'outputParams':output}
 if reason:body['reasonCode']=reason
 res=d.report('EXECUTION_FEEDBACK',body);row.setdefault('feedbackCalls',[]).append({'request':body,'response':res});q.save();return res
def observe(row):time.sleep(.2);row['after']=q.observe(row['taskId']);return row['after']
def event(o,t):return any(e['eventType']==t for e in o['events'])
def reset():q.reset()
def predicate(expected,actual,positive=False):
 reset();name=('false' if not expected else 'true')+'-predicate-'+('legal-control' if positive else 'counterexample')+'-corrected';row=q.submit(name,[st(condition='routeGenerated='+str(expected).lower()),st(2)]);d,msg=accept(row);feed(row,d,msg,{'routeGenerated':actual})
 if positive:
  d.state['workStatus']='IDLE';d2,msg2=accept(row,2);feed(row,d2,msg2,{'routeGenerated':True});d2.state['workStatus']='IDLE'
 else:
  d,retry=message(row,attempt=1);row['afterFirstFailure']=q.observe(row['taskId']);feed(row,d,retry,{'routeGenerated':actual});wait(lambda:event(q.observe(row['taskId']),'STEP_FAILED'))
 o=observe(row);c=[x for x in o['commandRows'] if x['command_type']=='EXECUTE_CAPABILITY'];q.record(row,{'frozenValidated':any(v.get('frozenAt') and v['source']=='AUTONOMOUS' for v in o['plans']),'feedback200':all(x['response']['http']==200 for x in row['feedbackCalls']),'planPredicateRespected':o['task']['status']=='COMPLETED' if positive else not any(a['stepSeq']==1 and a['stepStatus']=='COMPLETED' for a in o['assignments']),'nextStepGated':positive or not any(x['step_seq']==2 for x in c),'failureRecorded':positive or event(o,'STEP_FAILED'),'sameIdSingleRetry':positive or len({x['command_id'] for x in c if x['step_seq']==1})==1})
def safety(key):
 reset();row=q.submit('dispatch-guard-'+key,[st()]);d,offer=message(row,'TASK_ACCEPT');before=q.observe(row['taskId']);plan=next(v for v in before['plans'] if v['id']==before['task']['currentPlanVersionId']);steps=plan['planSteps'];steps=json.loads(steps) if isinstance(steps,str) else steps;row['originalFrozenPlan']=copy.deepcopy(plan);steps[0]['inputParams'][key]=1;row['injectedSteps']=steps;row['fixture']='Own frozen plan JSON injection only, after valid validation to reach final dispatch guard; not a production edit API/reachability claim'
 m.sql(f"update {m.SC}.plan_versions set plan_steps={m.lit(json.dumps(steps))}::json where id={plan['id']}");row['acceptResponse']=q.response(d,offer);o=observe(row);row['failedAssignmentsSql']=m.rows(f"select row_to_json(x)::text from {m.SC}.task_step_assignments x where task_id={row['taskId']}")
 q.record(row,{'http200':row['acceptResponse']['http']==200,'dispatchBlockedReason':any(e['eventType']=='COMMAND_DISPATCH_BLOCKED' and e['reasonCode']=='ERR_MOTION_SAFETY_FIELD' for e in o['events']),'stepFailedReason':any(x['step_status']=='FAILED' and x['reason_code']=='ERR_MOTION_SAFETY_FIELD' for x in row['failedAssignmentsSql']),'noBusinessCommandRecords':not any(c['command_type']=='EXECUTE_CAPABILITY' for c in o['commandRows']),'noBusinessTransport':not any(d.messages_for(o['task']['taskCode'],'EXECUTE_CAPABILITY') for d in q.devices)})
def enable_extra_caps():
 q.definitionBody['availableCapabilityTypes']=['CAP_NAVIGATION','CAP_ESCORT','CAP_NOTIFICATION'];q.cfg(f'/task-definitions/{q.definitions[0]}','PUT',q.definitionBody)
 for d in q.devices[:2]:
  caps=q.cfg(f'/devices/{d.code}/capabilities');caps_before[d.code]={c['capabilityCode']:c['capabilityStatus'] for c in caps}
  for cap in ['CAP_ESCORT','CAP_NOTIFICATION']:q.cfg(f'/devices/{d.code}/capabilities/{cap}/test','POST');q.cfg(f'/devices/{d.code}/capabilities/{cap}/status','POST',{'status':'ENABLED'})
 q.ev['capabilitiesBefore']=caps_before;q.save()
def legal(intent,cap,condition,params,output):
 reset();row=q.submit('legal-'+intent,[st(cap=cap,goal=intent,condition=condition,params=params)]);d,msg=accept(row);row['message']=msg;feed(row,d,msg,output);d.state['workStatus']='IDLE';o=observe(row);q.record(row,{'legalIntentDelivered':msg['commandType']=='EXECUTE_CAPABILITY' and msg['capabilityType']==cap,'intentNotBlocked':not event(o,'COMMAND_DISPATCH_BLOCKED'),'completed':o['task']['status']=='COMPLETED','resultPersisted':any(a['stepStatus']=='COMPLETED' and a['executionResult']=='SUCCESS' for a in o['assignments'])})
def feedback_retry():
 reset();row=q.submit('feedback-failed-then-success',[st()]);d,msg=accept(row);feed(row,d,msg,{'routeGenerated':False},'FAILED','SYNTHETIC_EXECUTION_FAILED');d,retry=message(row,attempt=1);row['duringRetry']=q.observe(row['taskId']);feed(row,d,retry,{'routeGenerated':True});d.state['workStatus']='IDLE';o=observe(row);q.record(row,{'sameCommandId':msg['commandId']==retry['commandId'],'retryExactlyOne':retry['attemptNo']==1 and sum(e['eventType']=='STEP_RETRY_DISPATCHED' for e in o['events'])==1,'completed':o['task']['status']=='COMPLETED','failureAndSuccessFeedback200':all(x['response']['http']==200 for x in row['feedbackCalls'])})
def run(name,fn):
 q.run(name,fn)
 for tid in q.tasks:
  if q.op(f'/tasks/{tid}')['status'] not in ['COMPLETED','FAILED','MANUAL_TERMINATED']:q.terminate({'taskId':tid})
try:
 for expected,actual,positive in [(False,True,False),(False,False,True),(True,False,False)]:run('predicate-'+str(expected)+'-'+str(actual),lambda expected=expected,actual=actual,positive=positive:predicate(expected,actual,positive))
 for key in ['speed','acceleration','attitude','pathPoints','obstacleAvoidance','emergencyStop','speedLimit','lostConnectionParking']:run('guard-'+key,lambda key=key:safety(key))
 run('feedback-retry',feedback_retry);enable_extra_caps()
 for intent,cap,condition,params,output in [('前往区域','CAP_NAVIGATION','routeGenerated=true',{'targetLocation':'F2_TEST_GATE'},{'routeGenerated':True}),('会合','CAP_ESCORT','arrivalStatus=ARRIVED',{'targetLocation':'F2_TEST_GATE','escortMode':'LEAD','maxDuration':60},{'arrivalStatus':'ARRIVED'}),('陪同','CAP_ESCORT','arrivalStatus=ARRIVED',{'targetLocation':'F2_TEST_GATE','escortMode':'FOLLOW','maxDuration':60},{'arrivalStatus':'ARRIVED'}),('空间引导','CAP_NAVIGATION','routeGenerated=true',{'targetLocation':'F2_TEST_GATE'},{'routeGenerated':True}),('现场通知','CAP_NOTIFICATION','notificationStatus=SUCCESS',{'notificationType':'TEXT','notificationContent':'Synthetic service notice','repeatCount':1},{'notificationStatus':'SUCCESS'})]:run('legal-'+intent,lambda intent=intent,cap=cap,condition=condition,params=params,output=output:legal(intent,cap,condition,params,output))
 result=subprocess.run(['node',str(R/'acceptance/stage3/retest-f017-v162-ui.cjs'),'435','retry-failed', '0','2','none'],cwd=R,capture_output=True,text=True,encoding='utf-8',timeout=55);q.ev['failureUi']={'exit':result.returncode,'stdout':result.stdout,'stderr':result.stderr};q.save()
finally:
 for code,caps in caps_before.items():
  for cap in ['CAP_ESCORT','CAP_NOTIFICATION']:
   try:q.cfg(f'/devices/{code}/capabilities/{cap}/status','POST',{'status':caps[cap]})
   except Exception as ex:q.ev.setdefault('cleanupDiagnostics',[]).append(str(ex))
 for rule in rules:
  if rule['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':rule['enabled']})
 q.cleanup();q.ev['endedAt']=m.now();q.save()
