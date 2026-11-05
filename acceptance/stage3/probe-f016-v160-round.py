"""V2.4 complete F016 round, new evidence only, fixed V1.160.
The concurrency barrier holds one OWN synthetic agent row in PostgreSQL. Two
HTTP callbacks can read but wait on their writes. It never locks shared schemas,
never stops a service, and releases the transaction in finally.
"""
import importlib.util,json,time,copy,subprocess,concurrent.futures
from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('v160',Path(__file__).with_name('probe-f016-v160.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
q=m.Probe();q.setup();before=q.cfg('/risk-rules');q.ev['rulesBefore']=before
q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False});q.ev['rulesDuring']=q.cfg('/risk-rules');q.save()
def gap():
 q.reset();row=q.submit('true-no-candidate',[m.p.step(seq=1),m.p.step(seq=2)]);d,msg=q.wait_message(row);q.response(d,msg);q.wait_message(row,'EXECUTE_CAPABILITY',d)
 row['beforeLoss']=q.observe(row['taskId']);codes=','.join(m.lit(d.code) for d in q.devices)
 row['fixture']='Scoped SQL capability loss at next-step boundary; API disable would trigger active-step recovery instead'
 m.sql(f"update {m.SC}.device_capabilities set capability_status='DISABLED' where capability_code='CAP_NAVIGATION' and device_id in (select id from {m.SC}.devices where device_code in ({codes}))")
 row['feedback']=q.complete(row,d);row['after']=q.observe(row['taskId']);o=row['after']
 q.record(row,{'capabilityGap':any(e['exception_type']=='CAPABILITY_GAP' and e['step_seq']==2 for e in o['exceptions']),'rightReason':any(e.get('reasonCode')=='ERR_NO_CANDIDATE_AVAILABLE' for e in o['events']),'noSecondStepCommand':not any(c['step_seq']==2 for c in o['commandRows']),'manual':o['task']['status']=='PENDING_MANUAL','noRetry':all(e['recovery_action']=='无可用候选设备，恢复动作未执行' for e in o['exceptions'])});q.terminate(row)
def term(offline=False):
 q.reset();row=q.submit('terminate-offline' if offline else 'terminate-online');d,msg=q.wait_message(row);q.response(d,msg);q.wait_message(row,'EXECUTE_CAPABILITY',d);row['executing']=q.observe(row['taskId'])
 if offline:d.configure(online='OFFLINE',work='BUSY')
 row['termination']=m.p.raw(q.op,f'/tasks/{row["taskId"]}/terminate',{'reason':'Synthetic BL006 boundary','confirmed':True});row['immediate']=q.observe(row['taskId'])
 def agent(o):return next(a for a in o['agentRows'] if a['agent_code']==d.agent)
 d.configure(online='OFFLINE',work='IDLE');row['offlineIdle']=q.observe(row['taskId']);d.configure(online='ONLINE',work='BUSY');row['onlineBusy']=q.observe(row['taskId'])
 d.configure(online='ONLINE',work='IDLE');row['onlineIdle']=q.observe(row['taskId']);d.heartbeat();row['duplicateIdle']=q.observe(row['taskId']);a=agent(row['onlineIdle'])
 q.record(row,{'terminated':row['immediate']['task']['status']=='MANUAL_TERMINATED','guardedUntilConfirmation':agent(row['immediate'])['work_status']=='BUSY','offlineIdleCannotRelease':agent(row['offlineIdle'])['current_task_id']==row['taskId'],'onlineBusyCannotRelease':agent(row['onlineBusy'])['current_task_id']==row['taskId'],'onlineIdleReleases':a['work_status']=='IDLE' and a['current_task_id'] is None and a['current_step_seq'] is None,'cancelConfirmed':any(c['command_type']=='TASK_CANCEL' and c['command_status']=='CONFIRMED_IDLE' and c['agent_code']==d.agent for c in row['onlineIdle']['commandRows']),'duplicateIdleSafe':agent(row['duplicateIdle'])['current_task_id'] is None});q.terminate(row)
def late():
 q.reset();row=q.submit('pending-terminate-late');d,msg=q.wait_message(row);row['before']=q.observe(row['taskId']);row['termination']=m.p.raw(q.op,f'/tasks/{row["taskId"]}/terminate',{'reason':'Synthetic pending cancellation','confirmed':True});row['immediate']=q.observe(row['taskId']);row['lateResponse']=q.response(d,msg);row['after']=q.observe(row['taskId']);a=next(a for a in row['immediate']['agentRows'] if a['agent_code']==d.agent)
 q.record(row,{'terminated':row['after']['task']['status']=='MANUAL_TERMINATED','pendingReleasedImmediately':a['work_status']=='IDLE' and a['current_task_id'] is None,'frozen':all(a['stepStatus']=='FROZEN' for a in row['after']['assignments']),'lateIgnored':any(e['eventType']=='LATE_TASK_RESPONSE_IGNORED' for e in row['after']['events']),'noExecution':not any(c['command_type']=='EXECUTE_CAPABILITY' for c in row['after']['commandRows'])});d.configure()
def tie():
 q.reset();row=q.submit('tie-code');d,msg=q.wait_message(row);q.response(d,msg);q.complete(row,d);row['after']=q.observe(row['taskId']);q.record(row,{'codeAscending':d.agent==min(d.agent for d in q.devices[:2]),'completed':row['after']['task']['status']=='COMPLETED'})
def offline_callback():
 q.reset();q.devices[1].configure(online='OFFLINE');row=q.submit('offline-before-callback');d,msg=q.wait_message(row);d.configure(online='OFFLINE');row['response']=q.response(d,msg);row['after']=q.observe(row['taskId']);q.record(row,{'noBusinessTransport':not any(x['message']['commandType']=='EXECUTE_CAPABILITY' for x in d.messages_for(row['after']['task']['taskCode'])),'exceptionDetected':bool(row['after']['exceptions']),'noOfflineExecution':row['after']['task']['status'] in ['PENDING_MANUAL','FAILED']});q.terminate(row)
def conflict_fallback():
 q.reset();a,b=q.devices[:2];a.configure(match=1);b.configure(match=.9);one=q.submit('conflict-fallback-holder');d,msg=q.wait_message(one);two=q.submit('conflict-fallback-switch');d2,msg2=q.wait_message(two)
 one['acceptResponse']=q.response(d,msg);q.wait_message(one,'EXECUTE_CAPABILITY',d);two['conflictedResponse']=q.response(d2,msg2);two['afterConflict']=q.observe(two['taskId']);b,bmsg=q.wait_message(two,device=b);two['fallbackResponse']=q.response(b,bmsg);q.wait_message(two,'EXECUTE_CAPABILITY',b)
 one['bothExecuting']=q.observe(one['taskId']);two['bothExecuting']=q.observe(two['taskId']);ownerA=next(x for x in one['bothExecuting']['agentRows'] if x['agent_code']==a.agent);ownerB=next(x for x in two['bothExecuting']['agentRows'] if x['agent_code']==b.agent)
 q.complete(one,d);q.complete(two,b);one['after']=q.observe(one['taskId']);two['after']=q.observe(two['taskId'])
 q.record(one,{'holder200':one['acceptResponse']['http']==200,'holderOccupationPreserved':ownerA['work_status']=='BUSY' and ownerA['current_task_id']==one['taskId'],'holderCompletes':one['after']['task']['status']=='COMPLETED'})
 q.record(two,{'conflictCallback200':two['conflictedResponse']['http']==200,'fallbackCallback200':two['fallbackResponse']['http']==200,'conflictEvent':any(e['eventType']=='AGENT_ASSIGNMENT_CONFLICTED' and e['reasonCode']=='ERR_AGENT_ALREADY_BUSY' for e in two['afterConflict']['events']),'differentOwner':ownerB['work_status']=='BUSY' and ownerB['current_task_id']==two['taskId'],'fallbackCompletes':two['after']['task']['status']=='COMPLETED'})
def simultaneous():
 q.reset();q.devices[1].configure(online='OFFLINE');one=q.submit('parallel-one');d,msg=q.wait_message(one);two=q.submit('parallel-two');d2,msg2=q.wait_message(two)
 for dev in q.devices:dev.paused=True
 time.sleep(.1);one['bothPending']=q.observe(one['taskId']);two['bothPending']=q.observe(two['taskId'])
 db=m.prior.p.base.d;proc=subprocess.Popen(db.common+['-d',db.shared,'-At','-q'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',env=dict(db.variables,PGCLIENTENCODING='UTF8'))
 try:
  proc.stdin.write(f"BEGIN;\nSELECT pg_backend_pid();\nSELECT id FROM {m.SC}.device_agents WHERE agent_code={m.lit(d.agent)} FOR UPDATE;\n\\echo GPT_LOCKED\n");proc.stdin.flush()
  pid=int(proc.stdout.readline().strip())
  while 'GPT_LOCKED' not in proc.stdout.readline():pass
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
   f1=pool.submit(q.response,d,msg);f2=pool.submit(q.response,d2,msg2)
   end=time.monotonic()+8;blocked=0
   while time.monotonic()<end:
    blocked=int(m.sql(f"WITH RECURSIVE w(pid) AS (SELECT pid FROM pg_stat_activity WHERE {pid}=ANY(pg_blocking_pids(pid)) UNION SELECT a.pid FROM pg_stat_activity a JOIN w ON w.pid=ANY(pg_blocking_pids(a.pid))) SELECT count(DISTINCT pid) FROM w"))
    if blocked>=2:break
    time.sleep(.05)
   one['barrier']={'scope':m.SC+'.device_agents / '+d.agent,'blockedCallbackSessionsIncludingLockQueue':blocked,'externalLockPid':pid,'purpose':'Queue both real callbacks at the owned row lock, including transitive PostgreSQL waiters'}
   proc.stdin.write('COMMIT;\n\\q\n');proc.stdin.flush();proc.wait(timeout=10)
   one['acceptResponse']=f1.result(timeout=15);two['acceptResponse']=f2.result(timeout=15)
  time.sleep(.3);one['overlap']=q.observe(one['taskId']);two['overlap']=q.observe(two['taskId'])
  count=sum(any(c['command_type']=='EXECUTE_CAPABILITY' for c in r['overlap']['commandRows']) for r in [one,two]);one['executionTaskCount']=count
  callbacksOK=all(r['acceptResponse']['http']==200 for r in [one,two]);conflictRecorded=any(e['eventType']=='AGENT_ASSIGNMENT_CONFLICTED' and e['reasonCode']=='ERR_AGENT_ALREADY_BUSY' for r in [one,two] for e in r['overlap']['events'])
  for row in [one,two]:q.record(row,{'exactlyOneExecution':count==1,'barrierEstablished':blocked>=2,'bothCallbacks200':callbacksOK,'conflictRecorded':conflictRecorded})
 finally:
  if proc.poll() is None:proc.stdin.write('ROLLBACK;\n\\q\n');proc.stdin.flush();proc.wait(timeout=10)
  for dev in q.devices:dev.paused=False
  q.terminate(one);q.terminate(two)
def pending_other_owner():
 q.reset();one=q.submit('pending-cancel-owner');d,msg=q.wait_message(one);two=q.submit('other-executing-owner');d2,msg2=q.wait_message(two);q.response(d2,msg2);q.wait_message(two,'EXECUTE_CAPABILITY',d2)
 one['otherBefore']=q.observe(two['taskId']);one['termination']=m.p.raw(q.op,f'/tasks/{one["taskId"]}/terminate',{'reason':'Cancel only pending task, preserve executing task','confirmed':True});one['after']=q.observe(one['taskId']);two['afterPendingOtherTerminated']=q.observe(two['taskId']);a=next(a for a in two['afterPendingOtherTerminated']['agentRows'] if a['agent_code']==d.agent)
 q.record(one,{'pendingTerminated':one['after']['task']['status']=='MANUAL_TERMINATED','otherOccupationPreserved':a['work_status']=='BUSY' and a['current_task_id']==two['taskId'],'otherStillExecuting':two['afterPendingOtherTerminated']['task']['status']=='EXECUTING','noCancelToOtherOwner':not any(c['command_type']=='TASK_CANCEL' for c in one['after']['commandRows'])});q.complete(two,d2);two['after']=q.observe(two['taskId']);q.record(two,{'otherCanComplete':two['after']['task']['status']=='COMPLETED'});q.terminate(one)
def cross_freeze():
 q.reset();one=q.submit('freeze-pending-other-owner',[m.p.step(seq=1),m.p.step(seq=2)]);d,msg=q.wait_message(one);q.response(d,msg);q.wait_message(one,'EXECUTE_CAPABILITY',d)
 two=q.submit('freeze-other-executing');b,msg2=q.wait_message(two);q.response(b,msg2);q.wait_message(two,'EXECUTE_CAPABILITY',b)
 bid=m.sql(f"select id from {m.SC}.device_agents where agent_code={m.lit(b.agent)}");m.sql(f"update {m.SC}.task_step_assignments set device_agent_id={bid} where task_id={one['taskId']} and step_seq=2")
 one['fixture']='Only future pending association seeded to B; B occupation belongs to independently accepted/executing other task. Mirrors owned-freeze positive control without changing actual owner.'
 one['beforeException']=q.observe(one['taskId']);two['beforeOtherFreeze']=q.observe(two['taskId']);d.configure(online='OFFLINE',work='BUSY');one['after']=q.observe(one['taskId']);two['afterOtherFreeze']=q.observe(two['taskId']);a=next(a for a in two['afterOtherFreeze']['agentRows'] if a['agent_code']==b.agent)
 q.record(one,{'futureFrozen':any(a['stepSeq']==2 and a['stepStatus']=='FROZEN' for a in one['after']['assignments']),'otherOwnerPreserved':a['work_status']=='BUSY' and a['current_task_id']==two['taskId'] and a['current_step_seq']==1,'otherStillExecuting':two['afterOtherFreeze']['task']['status']=='EXECUTING','noFutureBusiness':not any(c['step_seq']==2 and c['command_type']=='EXECUTE_CAPABILITY' for c in one['after']['commandRows'])})
 q.complete(two,b);two['after']=q.observe(two['taskId']);q.record(two,{'otherCanComplete':two['after']['task']['status']=='COMPLETED'});q.terminate(one)
def inactive():
 q.reset();c=q.devices[2];c.configure(match=2);m.sql(f"update {m.SC}.devices set device_status='INACTIVE' where device_code={m.lit(c.code)}")
 row=q.submit('inactive-device');d,msg=q.wait_message(row);q.response(d,msg);q.complete(row,d);row['after']=q.observe(row['taskId']);q.record(row,{'inactiveExcluded':d.agent!=c.agent,'completed':row['after']['task']['status']=='COMPLETED'});m.sql(f"update {m.SC}.devices set device_status='ACTIVE' where device_code={m.lit(c.code)}")
def baseline():
 q.reset();a=q.devices[0];body={'templateName':'G160 F016 baseline','templateIntent':q.family,'inputParams':copy.deepcopy(q.definitionBody['sceneParams']),'steps':[{'capabilityType':'CAP_NAVIGATION','paramMapping':[{'target':'targetLocation','source':'TEMPLATE_INPUT.targetLocation'}],'stepTimeout':60,'completionCondition':'routeGenerated=true'}]}
 t=q.cfg('/baseline-templates','POST',body);q.templates.append(t['id']);q.save();res=q.cfg(f"/baseline-templates/{t['id']}/dry-run",'POST',{'inputParams':{'targetLocation':'F2_TEST_GATE'},'simulatedDevices':[{'stepSeq':1,'agentId':a.agent}]})
 row={'name':'baseline-trial','taskId':res['taskId']};q.tasks.append(res['taskId']);q.ev['cases'].append(row);d,msg=q.wait_message(row);q.response(d,msg);q.complete(row,d);row['after']=q.observe(row['taskId']);q.record(row,{'completed':row['after']['task']['status']=='COMPLETED','dryRun':row['after']['task']['isDryRun']});q.cfg(f"/baseline-templates/{t['id']}/enable",'POST')
 q.reset();row=q.submit('baseline-match',high=True);d,msg=q.wait_message(row);row['beforeAcceptance']=q.observe(row['taskId']);q.response(d,msg);q.complete(row,d);row['after']=q.observe(row['taskId']);q.record(row,{'baseline':any(v['source']=='BASELINE_TEMPLATE' for v in row['after']['plans']),'downgradingBeforeAccept':row['beforeAcceptance']['task']['status']=='DOWNGRADING','completed':row['after']['task']['status']=='COMPLETED'});q.cfg(f"/baseline-templates/{t['id']}/disable",'POST')
def input_coords():
 q.reset()
 for d in q.devices:
  c=next(c for c in q.cfg(f'/devices/{d.code}/capabilities') if c['capabilityCode']=='CAP_NAVIGATION');body={k:c[k] for k in ['capabilityName','inputParams','outputParams','capabilityDescription']};body['inputParams'] += [{'name':key,'type':'Double','required':False,'defaultValue':0} for key in ['targetX','targetY']]
  q.cfg(f'/devices/{d.code}/capabilities/CAP_NAVIGATION','PUT',body);d.configure();q.cfg(f'/devices/{d.code}/capabilities/CAP_NAVIGATION/test','POST');q.cfg(f'/devices/{d.code}/capabilities/CAP_NAVIGATION/status','POST',{'status':'ENABLED'})
 q.devices[0].configure(x=3,y=4);q.devices[1].configure(x=0,y=0);q.devices[2].configure(online='OFFLINE');row=q.submit('input-coordinates',[m.p.step(params={'targetLocation':'F2_TEST_GATE','targetX':0,'targetY':0})]);d,msg=q.wait_message(row);q.response(d,msg);q.complete(row,d);row['after']=q.observe(row['taskId']);q.record(row,{'nearestB':d.agent==q.devices[1].agent,'completed':row['after']['task']['status']=='COMPLETED'})
try:
 for name,aa,bb in [('match',{'match':.8,'x':0,'load':0},{'match':.9,'x':10,'load':8}),('distance',{'x':3,'y':4},{'x':0,'y':0,'load':8}),('load',{'load':9},{'load':1})]:q.run(name,lambda name=name,aa=aa,bb=bb:q.ranking('rank-'+name,{'targetLocation':'F2_TEST_GATE','targetX':0,'targetY':0},aa,bb))
 for k in ['offline','busy','disabled-agent','disabled-capability','absent-capability']:q.run(k,lambda k=k:q.eligibility('eligibility-'+k,k))
 for name,fn in [('inactive',inactive),('reject-next',lambda:q.reject('reject-next')),('all-reject',lambda:q.reject('all-reject',True)),('busy-control',q.busy_control),('stale-overlap',q.concurrent),('conflict-fallback',conflict_fallback),('parallel-overlap',simultaneous),('no-candidate',gap),('freeze',q.freeze),('online-terminate',term),('offline-terminate',lambda:term(True)),('pending-terminate',late),('cross-task-owner',pending_other_owner),('cross-task-freeze',cross_freeze),('tie',tie),('offline-callback',offline_callback),('baseline',baseline),('input-params',input_coords)]:q.run(name,fn)
finally:
 for r in before:
  if r['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':r['enabled']})
 q.ev['rulesAfter']=q.cfg('/risk-rules');q.cleanup();q.ev['endedAt']=m.now();q.save()
