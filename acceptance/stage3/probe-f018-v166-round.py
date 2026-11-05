"""V2.4 full independent F018 HTTP/SQL/protocol round; synthetic model/adapters.
Fixed V1.166. Never alters product sources. Uses GPT-owned reusable schema.
"""
import importlib.util,json,time,copy,os
from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('m',Path(__file__).with_name('probe-f018-v166.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
q=m.Probe()
def st(seq=1,timeout=180,**kw):
 x=m.p.step(seq=seq,params={'targetLocation':'F2_TEST_GATE'});x.update(stepGoal='前往区域',completionCondition='routeGenerated=true',stepTimeout=timeout);x.update(kw);return x
def wait(fn,seconds=20):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  value=fn()
  if value:return value
  time.sleep(.15)
 raise TimeoutError('Condition not observed')
def obs(row,key='after'):
 time.sleep(.2);row[key]=q.observe(row['taskId']);q.save();return row[key]
def event(o,t):return [e for e in o['events'] if e['eventType']==t]
def cfgcase(row,**kw):
 marker=row['request']['taskGoal'].split()[0];q.cases[marker].update(kw);(R/'.local-test/f018-v166-cases.json').write_text(json.dumps(q.cases),encoding='utf-8')
def msgs(row,typ):
 code=q.op(f'/tasks/{row["taskId"]}')['taskCode'];return [(d,x['message']) for d in q.devices for x in d.messages_for(code,typ)]
def accept(row):
 def pending():
  arr=q.op(f'/tasks/{row["taskId"]}/step-assignments');return next((x for x in arr if x['stepStatus']=='PENDING_ASSIGNMENT' and x.get('commandId')),None)
 a=wait(pending);code=q.op(f'/tasks/{row["taskId"]}')['taskCode']
 d=wait(lambda:next((d for d in q.devices if any(x['message']['commandId']==a['commandId'] for x in d.messages_for(code,'TASK_ACCEPT'))),None))
 msg=next(x['message'] for x in d.messages_for(code,'TASK_ACCEPT') if x['message']['commandId']==a['commandId']);ret=q.response(d,msg);row.setdefault('accepts',[]).append({'request':msg,'response':ret})
 executeId=m.sql(f"select execute_command_id from {m.SC}.task_step_assignments where task_id={row['taskId']} and command_id={m.lit(a['commandId'])}")
 return d,wait(lambda:next((mm for dd,mm in msgs(row,'EXECUTE_CAPABILITY') if dd==d and mm['commandId']==executeId and mm['attemptNo']==0),None))
def feed(row,d,msg,result='SUCCESS',reason=None,output=None):
 with d.guard:
  body={'commandId':msg['commandId'],'attemptNo':msg['attemptNo'],'executionResult':result,'outputParams':output or {'routeGenerated':True}}
  if reason:body['reasonCode']=reason
  if result=='SUCCESS':d.state['workStatus']='IDLE'
  ret=d.report('EXECUTION_FEEDBACK',body);row.setdefault('feedbacks',[]).append({'agent':d.agent,'request':body,'response':ret});q.save();return ret

def failtwice(row,d,msg,result='FAILED',reason='ERR_SYNTHETIC_HARDWARE'):
 feed(row,d,msg,result,reason);retry=wait(lambda:next((mm for dd,mm in msgs(row,'EXECUTE_CAPABILITY') if dd==d and mm['commandId']==msg['commandId'] and mm['attemptNo']==1),None));d.state['workStatus']='IDLE';feed(row,d,retry,result,reason);return retry
def finish(row,max_steps=6):
 for _ in range(max_steps):
  status=q.op(f'/tasks/{row["taskId"]}')['status']
  if status in ['COMPLETED','FAILED','PENDING_MANUAL','MANUAL_TERMINATED']:break
  d,msg=accept(row);feed(row,d,msg)
 return obs(row)
def reset():
 for d in q.devices:d.paused=False;d.delivery_failures=set()
 q.reset()
def prefix(row):
 d,msg=accept(row);feed(row,d,msg);obs(row,'prefix');return accept(row)
def intact(row,o):
 first=next(a for a in row['prefix']['assignments'] if a['stepSeq']==1)
 return any(a['stepSeq']==1 and a['stepStatus']=='COMPLETED' and a.get('outputParams')==first.get('outputParams') for a in o['assignments'])
def recovered(kind):
 reset();row=q.submit('recovered-'+kind,[st(),st(2,timeout=30 if kind=='timeout' else 180),st(3)]);d,msg=prefix(row);before=obs(row,'beforeException')
 if kind=='offline':
  d.paused=True;start=time.monotonic();wait(lambda:any(e['exception_type']=='AGENT_OFFLINE' for e in q.observe(row['taskId'])['exceptions']),30);row['elapsedOffline']=time.monotonic()-start
 elif kind=='timeout':
  start=time.monotonic();time.sleep(20);obs(row,'beforeThreshold');wait(lambda:any(e['exception_type']=='EXECUTION_TIMEOUT' for e in q.observe(row['taskId'])['exceptions']),28);row['elapsedTimeout']=time.monotonic()-start
 else:failtwice(row,d,msg,'TIMEOUT' if kind=='reported-timeout' else 'FAILED','ERR_EXECUTION_TIMEOUT' if kind=='reported-timeout' else 'ERR_SYNTHETIC_HARDWARE')
 mid=obs(row,'recovering');backup,cmd=accept(row);mid2=obs(row,'backupExecuting');feed(row,backup,cmd);end=finish(row)
 ex='AGENT_OFFLINE' if kind=='offline' else ('EXECUTION_TIMEOUT' if 'timeout' in kind else 'STEP_FAILED')
 q.record(row,{'recognized':any(x['exception_type']==ex for x in mid['exceptions']),'futureFrozen':any(a['stepSeq']==3 and a['stepStatus']=='FROZEN' for a in mid['assignments']),'prefixPreserved':intact(row,mid) and intact(row,end),'candidateChanged':backup!=d,'notPrematureSuccess':all(x['recovery_result'] is None and x['exception_status']=='PROCESSING' for x in mid2['exceptions']),'sameVersion':len(end['plans'])==1 and not end['task']['replanUsed'],'completed':end['task']['status']=='COMPLETED','resolvedAfterActualSuccess':all(x['exception_status']=='RESOLVED' and x['recovery_result']=='SUCCESS' for x in end['exceptions']),'noFutureEarlyCommands':not any(c['step_seq']==3 for c in mid['commandRows']),'candidateFinalActionTruth':bool(event(end,'EXCEPTION_RECOVERED')) and all('候选设备切换' in e['detailSummary'] and '重试成功' not in e['detailSummary'] for e in event(end,'EXCEPTION_RECOVERED'))})
def retry_success():
 reset();row=q.submit('retry-success',[st(),st(2),st(3)]);d,msg=prefix(row);feed(row,d,msg,'FAILED','ERR_SYNTHETIC_HARDWARE');obs(row,'retrying');retry=next(mm for dd,mm in msgs(row,'EXECUTE_CAPABILITY') if dd==d and mm['commandId']==msg['commandId'] and mm['attemptNo']==1);feed(row,d,retry);o=finish(row)
 q.record(row,{'oneRetry':len(event(o,'STEP_RETRY_DISPATCHED'))==1,'sameCommand':retry['commandId']==msg['commandId'],'completed':o['task']['status']=='COMPLETED','noReplan':not o['task']['replanUsed'] and len(o['plans'])==1,'failureJudgmentRecorded':bool(o['exceptions']) and bool(event(o,'EXCEPTION_RECOVERED')),'retryInitiallyProcessing':bool(row['retrying']['exceptions']) and all(e['exception_status']=='PROCESSING' and e['recovery_result'] is None for e in row['retrying']['exceptions']),'archivedWithRetryJudgment':all(e['exception_status']=='RESOLVED' and e['recovery_result']=='SUCCESS' and '重试成功' in e['impact_conclusion'] for e in o['exceptions']),'prefixPreserved':intact(row,o)})
def unrelated():
 reset();q.devices[2].configure();row=q.submit('unrelated-offline',[st(),st(2)]);d,msg=accept(row);other=next(x for x in q.devices if x!=d);other.paused=True;wait(lambda:bool(event(q.observe(row['taskId']),'UNRELATED_AGENT_OFFLINE_JUDGED')),30);mid=obs(row,'unrelatedObserved');feed(row,d,msg);o=finish(row)
 q.record(row,{'judged':any(x['reasonCode']=='ERR_AGENT_OFFLINE_UNRELATED' for x in event(mid,'UNRELATED_AGENT_OFFLINE_JUDGED')),'notFrozen':not any(a['stepStatus']=='FROZEN' for a in mid['assignments']),'notReplanned':not o['task']['replanUsed'] and len(o['plans'])==1,'completed':o['task']['status']=='COMPLETED'})
def exhaustion(mode):
 reset();row=q.submit('exhaustion-'+mode,[st(),st(2),st(3)]);cfgcase(row,replanSteps=[st()] if mode not in ['invalid','overquota'] else ([dict(st(),capabilityType='CAP_F018_NONEXISTENT')] if mode=='invalid' else [st(i) for i in range(1,6)]),**({'replanHttpStatus':503} if mode=='model-failed' else {}));d,msg=prefix(row);failtwice(row,d,msg);mid=obs(row,'firstCandidateFailed');d2,msg2=accept(row);failtwice(row,d2,msg2);replanned=obs(row,'replanned')
 if mode=='success':o=finish(row)
 elif mode in ['second-failure','noncritical']:
  if replanned['task']['status'] not in ['PENDING_MANUAL','FAILED']:
   d3,m3=accept(row);failtwice(row,d3,m3);mid3=obs(row,'replannedCandidateFailed')
   if mid3['task']['status'] not in ['PENDING_MANUAL','FAILED']:
    d4,m4=accept(row);failtwice(row,d4,m4)
  o=obs(row)
 else:o=replanned
 checks={'prefixPreserved':intact(row,o),'oneReplanUsed':o['task']['replanUsed'],'oneTrigger':len(event(o,'REPLANNING_TRIGGERED'))==1,'atMostTwoPlans':len(o['plans'])<=2,'recoveryExhaustedBeforeReplan':bool(event(replanned,'EXCEPTION_RECOVERY_FAILED'))}
 if mode=='success':checks.update(completed=o['task']['status']=='COMPLETED',newVersion=len(o['plans'])==2,allThreeValidationPass=all(v['structureCheckResult']=='PASS' and v['capabilityCheckResult']=='PASS' and v['constraintCheckResult']=='PASS' for v in o['plans']))
 else:checks.update(pendingManual=o['task']['status']=='PENDING_MANUAL',noFalseRecovered=not bool(event(o,'EXCEPTION_RECOVERED')),allArchived=all(e['exception_status']=='RESOLVED' for e in o['exceptions']))
 if mode in ['model-failed','invalid','overquota']:checks['replanExceptionRecorded']=any(e['exception_type']=='REPLAN_FAILED' and e['recovery_result']=='FAILED' for e in o['exceptions'])
 q.record(row,checks)
def pending_offline():
 reset();row=q.submit('pending-assignment-offline',[st(),st(2)]);d,cmd=q.wait_message(row);d.paused=True;wait(lambda:any(e['exception_type']=='AGENT_OFFLINE' for e in q.observe(row['taskId'])['exceptions']),30);mid=obs(row,'offlineDetected');b,msg=accept(row);feed(row,b,msg);o=finish(row);q.record(row,{'offlineBeforeExecution':not any(x['commandId']==cmd['commandId'] for _,x in msgs(row,'EXECUTE_CAPABILITY')),'nextCandidate':b!=d,'noReplan':not o['task']['replanUsed'],'completed':o['task']['status']=='COMPLETED','offlineException':any(x['exception_type']=='AGENT_OFFLINE' for x in mid['exceptions'])})
def noncritical():
 reset();row=q.submit('noncritical-satisfied',[st(),st(2,failureHandling='非关键步骤，失败可跳过；原目标完成条件已满足时继续后续步骤'),st(3)]);cfgcase(row,replanSteps=[st()]);d,msg=prefix(row);failtwice(row,d,msg);d2,msg2=accept(row);failtwice(row,d2,msg2);mid=obs(row,'afterExhaustion');o=finish(row) if not mid['task']['replanUsed'] else mid
 q.record(row,{'firstAlreadySatisfied':intact(row,o),'noReplanWhenGoalSatisfied':not o['task']['replanUsed'],'continuesOriginal':len(o['plans'])==1 and o['task']['status']=='COMPLETED','skippedNoncritical':any(a['stepSeq']==2 and a['stepStatus']=='SKIPPED' for a in o['assignments']),'explicitImpactJudgment':bool(event(o,'PLAN_CONTINUATION_JUDGED')),'allArchived':all(e['exception_status']=='RESOLVED' for e in o['exceptions']),'failedRecoveryNotInventedSuccess':not event(o,'EXCEPTION_RECOVERED')})
def no_candidate_timeout():
 reset();q.devices[1].configure(online='OFFLINE');row=q.submit('timeout-no-candidate',[st(timeout=30)]);cfgcase(row,replanHttpStatus=503);d,msg=accept(row);start=time.monotonic();wait(lambda:q.op(f'/tasks/{row["taskId"]}')['status']=='PENDING_MANUAL',48);o=obs(row);row['elapsed']=time.monotonic()-start;q.record(row,{'timeoutType':any(e['exception_type']=='EXECUTION_TIMEOUT' for e in o['exceptions']),'timeoutEvent':bool(event(o,'STEP_TIMEOUT_DETECTED')),'oneReplan':o['task']['replanUsed'] and len(event(o,'REPLANNING_TRIGGERED'))==1,'manual':o['task']['status']=='PENDING_MANUAL','archived':all(e['exception_status']=='RESOLVED' for e in o['exceptions'])})
def api_catalog():
 row={'name':'exception-catalog','taskId':q.tasks[-1]};q.ev['cases'].append(row);row['all']=q.op('/task-exceptions');row['types']={t:q.op('/task-exceptions?exceptionType='+t) for t in ['AGENT_OFFLINE','CAPABILITY_GAP','EXECUTION_TIMEOUT','STEP_FAILED','REPLAN_FAILED']};row['statuses']={t:q.op('/task-exceptions?exceptionStatus='+t) for t in ['PENDING','PROCESSING','RESOLVED','IGNORED']};row['overview']=q.op('/dashboard/overview');q.record(row,{'typeFilters':all(all(e['exceptionType']==t for e in es) for t,es in row['types'].items()),'statusFilters':all(all(e['exceptionStatus']==t for e in es) for t,es in row['statuses'].items())})
def run(name,fn):
 q.run(name,fn)
 for tid in q.tasks:
  if q.op(f'/tasks/{tid}')['status'] not in ['COMPLETED','FAILED','MANUAL_TERMINATED']:q.terminate({'taskId':tid})
try:
 q.setup();q.ev['rulesBefore']=q.cfg('/risk-rules');q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False});q.ev['settingsBefore']=q.cfg('/settings/heartbeat-timeout');q.cfg('/settings/heartbeat-timeout','PUT',{'seconds':10})
 for name,fn in [('retry-success',retry_success),('failure-candidate',lambda:recovered('failure')),('reported-timeout',lambda:recovered('reported-timeout')),('offline-candidate',lambda:recovered('offline')),('timeout-candidate',lambda:recovered('timeout')),('unrelated',unrelated),('pending-offline',pending_offline),('replan-success',lambda:exhaustion('success')),('second-failure',lambda:exhaustion('second-failure')),('model-failed',lambda:exhaustion('model-failed')),('invalid',lambda:exhaustion('invalid')),('overquota',lambda:exhaustion('overquota')),('noncritical',noncritical),('timeout-no-candidate',no_candidate_timeout),('catalog',api_catalog)]:run(name,fn)
finally:
 for rule in q.ev.get('rulesBefore',[]):
  if rule['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':rule['enabled']})
 if q.ev.get('settingsBefore'):q.cfg('/settings/heartbeat-timeout','PUT',{'seconds':q.ev['settingsBefore']['seconds']})
 q.cleanup();q.ev['endedAt']=m.now();q.save()
