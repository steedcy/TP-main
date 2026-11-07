"""Independent F021 full round against fixed packaged V1.174.
Uses GPT schema/Redis10, controlled model and three synthetic HTTP adapters.
SQL status/multi-occupancy fixtures are explicitly labelled; never product edits.
Keep alive for real UI; signal .local-test/f021-v174-finish to clean up.
"""
import importlib.util,json,time,copy,threading,traceback,urllib.request,urllib.error
from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('h',Path(__file__).with_name('probe-f021-v174-helpers.py'));h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
q=h.q;m=h.m;SC=m.SC

def raw(tid,body,path='terminate',api=None):return m.p.raw(api or q.op,f'/tasks/{tid}/{path}',body)
def capture(row,key='after'):
 o=q.observe(row['taskId']);code=o['task']['taskCode']
 o['eventRows']=m.rows(f"select row_to_json(x)::text from {SC}.task_events x where task_id={row['taskId']} order by id")
 o['audit']=m.rows(f"select row_to_json(x)::text from {SC}.operation_logs x where operation_target={m.lit(code)} order by id")
 row[key]=o;q.save();return o
def term(row,reason='F174 independent safe termination'):
 ret=raw(row['taskId'],{'reason':reason,'confirmed':True});row.setdefault('terminationRequests',[]).append({'reason':reason,'response':ret});q.save();return ret
def record(row,checks):
 o=next((row[k] for k in ['afterGates','afterBrowser','after','evidence','terminated'] if isinstance(row.get(k),dict) and 'events' in row[k]),None)
 if o and any(e['eventType']=='TASK_TERMINATED' for e in o['events']):
  row['structuredEventChecks']=verify_event_json(o)
  checks['eventJsonPersistenceAndSummary']=all(row['structuredEventChecks'].values())
 q.record(row,checks)
def idle():
 for d in q.devices:d.configure()
def new(name,steps=None):h.reset();return q.submit(name,steps or [h.st(timeout=600)])
def fixture(name,status):
 tid=int(m.sql(f"insert into {SC}.tasks(task_code,task_goal,task_family,status,replan_used,is_dry_run,created_at,updated_at,created_by) values('G174-{time.time_ns()}',{m.lit('F174_STATUS_'+name)},{m.lit(q.family)},{m.lit(status)},false,false,now(),now(),'GPT Synthetic Operator') returning id").splitlines()[0])
 row={'name':name,'taskId':tid,'fixtureLevel':'SQL status-only gate fixture; not a natural lifecycle','seededStatus':status};q.tasks.append(tid);q.ev['cases'].append(row);q.save();return row
def stable(o):return {k:o[k] for k in ['task','plans','events','assignments','commandRows','audit']}
def cancels(o):return [c for c in o['commandRows'] if c['command_type']=='TASK_CANCEL']
def detail(o):
 logs=[x for x in o['audit'] if x['operation_type']=='TASK_TERMINATE']
 if not logs:return {}
 value=logs[-1]['detail'];return value if isinstance(value,dict) else json.loads(value)
def event_json(o):
 ev=[x for x in o['events'] if x['eventType']=='TASK_TERMINATED']
 try:return json.loads(ev[-1].get('detail') or '')
 except (ValueError,IndexError,TypeError):return None

def verify_event_json(o):
 ev=[e for e in o['events'] if e['eventType'] in ['TASK_TERMINATED','MANUAL_TERMINATED']]
 sqlrows={e['id']:e for e in o['eventRows']};checks={'bothTerminationEvents':{e['eventType'] for e in ev}=={'TASK_TERMINATED','MANUAL_TERMINATED'}}
 for e in ev:
  try:j=json.loads(e['detail'])
  except (ValueError,TypeError):j=None
  k=e['eventType'];checks[k+'WholeJson']=isinstance(j,dict)
  if not isinstance(j,dict):continue
  checks[k+'AllRequiredKeys']=all(k in j for k in ['reason','previousStatus','operator','deviceCancelResults','summary','cancelledCount'])
  checks[k+'ReasonAndOperator']=j.get('reason')==o['task']['manualTerminateReason'] and bool(j.get('operator'))
  checks[k+'NaturalSummary']=e.get('detailSummary')==j.get('summary') and not e.get('detailSummary','').lstrip().startswith('{')
  checks[k+'SqlEqualsHttp']=sqlrows.get(e['id'],{}).get('detail_summary')==e['detail']
  checks[k+'DeviceFields']=all(all(d.get(k) for k in ['deviceCode','agentId','agentCode','cancelCommandId','cancelStatus']) for d in j.get('deviceCancelResults',[]))
  checks[k+'OperationMatches']=j==detail(o)
  checks[k+'DeviceCount']=j.get('cancelledCount')==len(j.get('deviceCancelResults',[]))
 return checks

def reason_boundaries():
 row=fixture('reason-and-confirmation-boundaries','PENDING_MANUAL');before=capture(row,'before');row['invalidRequests']=[]
 bodies=[{'confirmed':True},{'reason':None,'confirmed':True},{'reason':'','confirmed':True},{'reason':' \t\n ','confirmed':True},{'reason':'x'*201,'confirmed':True},{'reason':'valid'},{'reason':'valid','confirmed':False}]
 for b in bodies:row['invalidRequests'].append({'body':b,'response':raw(row['taskId'],b)})
 after=capture(row,'afterInvalid');ret=term(row,'  Z  ');end=capture(row)
 record(row,{'allMissingBlankOverlengthOrUnconfirmed400':all(x['response']['http']==400 for x in row['invalidRequests']),'noInvalidBusinessMutation':stable(before)==stable(after),'oneCharacterTrimmedAccepted':ret['http']==200 and end['task']['manualTerminateReason']=='Z','terminal':end['task']['status']=='MANUAL_TERMINATED'})
 row=fixture('exact-200-reason','PENDING_MANUAL');ret=term(row,'界'*200);o=capture(row);record(row,{'exact200Accepted':ret['http']==200,'actualReasonPersisted':o['task']['manualTerminateReason']=='界'*200 and detail(o).get('reason')=='界'*200})

def gates():
 for status in ['PLANNING','SUPERVISING','PENDING_ASSIGNMENT','DOWNGRADING','EXECUTING','PENDING_MANUAL']:
  row=fixture('legal-state-'+status,status);ret=term(row);o=capture(row);record(row,{'legalState200':ret['http']==200,'terminal':o['task']['status']=='MANUAL_TERMINATED','previousStatusAudited':detail(o).get('previousStatus')==status})
 for status in ['COMPLETED','FAILED','MANUAL_TERMINATED']:
  row=fixture('terminal-state-'+status,status);before=capture(row,'before');ret=term(row);o=capture(row);record(row,{'terminalTerminate409':ret['http']==409,'completeBusinessSnapshotUnchanged':stable(before)==stable(o)})

def normal_and_pending():
 row=new('normal-completion-neighbor',[h.st(),h.st(2)]);o=h.finish(row);capture(row);record(row,{'naturalCompletion':o['task']['status']=='COMPLETED','allStepsCompleted':all(a['stepStatus']=='COMPLETED' for a in o['assignments']),'noCancel':not cancels(o)})
 row=new('pending-assignment-terminate',[h.st(),h.st(2)]);d,msg=q.wait_message(row);capture(row,'before');ret=term(row);o=capture(row,'terminated');late=q.response(d,msg);row['lateAcceptance']=late;idle();end=capture(row)
 record(row,{'terminated':ret['http']==200 and o['task']['status']=='MANUAL_TERMINATED','allUnfinishedFrozen':all(x['stepStatus']=='FROZEN' for x in o['assignments']),'noExecuteEvenLateAcceptance':not any(c['command_type']=='EXECUTE_CAPABILITY' for c in end['commandRows']),'noWrongBusyOccupancy':all(a['current_task_id']!=row['taskId'] for a in end['agentRows']),'terminalRetained':end['task']['status']=='MANUAL_TERMINATED'})

def prefix_and_terminal():
 row=new('completed-prefix-executing-terminate',[h.st(timeout=600),h.st(2,timeout=600),h.st(3,timeout=600)]);d,msg=h.prefix(row)
 with d.guard:
  before=capture(row,'before');ret=term(row);o=capture(row,'terminated');late=h.feed(row,d,msg);row['lateExecutionFeedback']=late;d.configure();end=capture(row)
 first=next(x for x in before['assignments'] if x['stepSeq']==1)
 row['terminalActions']=[]
 for action in ['RETRY_PLANNING','SWITCH_TO_BASELINE','MARK_FAILED']:
  row['terminalActions'].append({'action':action,'response':raw(row['taskId'],{'action':action,'reason':'F174 terminal gate'},'manual-actions')})
 row['clarify']=raw(row['taskId'],{'answers':{'test':'F174'}},'clarify');row['cancel']=raw(row['taskId'],{'reason':'F174'},'cancel');row['terminateAgain']=term(row)
 final=capture(row,'afterGates')
 record(row,{'terminate200':ret['http']==200,'completedPrefixPreserved':any(x['stepSeq']==1 and x['stepStatus']=='COMPLETED' and x.get('outputParams')==first.get('outputParams') for x in final['assignments']),'unfinishedFrozen':all(x['stepStatus']=='FROZEN' for x in final['assignments'] if x['stepSeq']>1),'noFutureBusiness':not any(c['step_seq']==3 for c in final['commandRows']),'cancelDistinctFromExecuteAndAccept':all(c['command_id'] not in [msg['commandId'],row['accepts'][-1]['request']['commandId']] for c in cancels(o)),'confirmedIdle':bool(cancels(final)) and all(c['command_status']=='CONFIRMED_IDLE' for c in cancels(final)),'terminalActions409':all(x['response']['http']==409 for x in row['terminalActions']),'otherResumeRejected':400<=row['clarify']['http']<500 and 400<=row['cancel']['http']<500 and row['terminateAgain']['http']==409,'noGateBusinessMutation':stable(end)==stable(final)})
 row['auditChecks']={'operationDetailValidJSON':bool(detail(final).get('deviceCancelResults')),'eventDetailWholeJSON':event_json(final) is not None};q.save()
 auditrow={'name':'structured-event-and-operation-audit','taskId':row['taskId'],'sourceCase':row['name'],'evidence':final};q.ev['cases'].append(auditrow);record(auditrow,row['auditChecks'])

def multiple_devices():
 row=new('multi-device-cancel-summary',[h.st(timeout=600)]);d,msg=h.accept(row);other=next(x for x in q.devices if x!=d);row['fixtureLevel']='Natural executing first device; second same-task occupied device explicitly seeded through SQL to exercise multi-device cancellation independent of serial planner'
 for x in [d,other]:x.paused=True
 other.state['workStatus']='BUSY';other.heartbeat();m.sql(f"update {SC}.device_agents set current_task_id={row['taskId']},current_step_seq=1,work_status='BUSY' where agent_code={m.lit(other.agent)}")
 before=capture(row,'before');ret=term(row);o=capture(row,'terminated');a=detail(o);devs=a.get('deviceCancelResults',[])
 for x in [d,other]:x.state.update(workStatus='IDLE',onlineStatus='ONLINE');x.heartbeat()
 end=capture(row);record(row,{'twoOwnedDevices':sum(x['current_task_id']==row['taskId'] for x in before['agentRows'])==2,'twoIndependentCancelCommands':len(cancels(o))==2 and len({x['command_id'] for x in cancels(o)})==2,'structuredOperationTwoDevices':len(devs)==2 and all(all(x.get(k) for k in ['agentId','agentCode','deviceCode','cancelCommandId','cancelStatus']) for x in devs),'realDeviceCodesMapped':{x.get('deviceCode') for x in devs}=={d.code,other.code},'cancelIdsCorrelate':{x['cancelCommandId'] for x in devs}=={c['command_id'] for c in cancels(o)},'bothConfirmedIdle':all(c['command_status']=='CONFIRMED_IDLE' for c in cancels(end)),'allOccupancyReleased':all(x['current_task_id']!=row['taskId'] for x in end['agentRows']),'terminal':end['task']['status']=='MANUAL_TERMINATED'})
 for x in [d,other]:x.paused=False

def cancellation_safety():
 row=new('unconfirmed-timeout-and-online-idle-recovery');d,msg=h.accept(row)
 with d.guard:
  ret=term(row);start=time.monotonic();o=capture(row,'immediate')
  # Heartbeats stay ONLINE BUSY, so timeout is actual wall-clock default60s.
 row['waitStartedAt']=m.now()
 while time.monotonic()-start<78:
  cmds=m.rows(f"select row_to_json(x)::text from {SC}.device_commands x where task_id={row['taskId']} and command_type='TASK_CANCEL'")
  if any(c['command_status']=='TIMED_OUT' for c in cmds):break
  time.sleep(2)
 row['elapsedToTimeout']=time.monotonic()-start;mid=capture(row,'timedOut')
 d.configure(online='OFFLINE',work='IDLE');offline=capture(row,'offlineIdle');d.configure(work='BUSY');busy=capture(row,'onlineBusy');d.configure();end=capture(row,'confirmed');d.heartbeat();again=capture(row)
 timeoutEvents=[e for e in mid['events'] if e['eventType']=='TASK_CANCEL_CONFIRMATION_TIMEOUT']
 record(row,{'queuedRetainsBusy':any(x['current_task_id']==row['taskId'] and x['work_status']=='BUSY' for x in o['agentRows']),'actualDefaultTimeoutObserved':bool(timeoutEvents) and row['elapsedToTimeout']>=60,'timeoutHasAgentCommandReason':all(d.agent in e.get('detailSummary','') and e.get('reasonCode')=='DEVICE_CANCEL_NO_CONFIRMATION' for e in timeoutEvents),'timeoutPreservesSafetyOccupation':any(x['current_task_id']==row['taskId'] for x in mid['agentRows']),'offlineIdleDoesNotRelease':any(x['current_task_id']==row['taskId'] for x in offline['agentRows']),'onlineBusyDoesNotRelease':any(x['current_task_id']==row['taskId'] for x in busy['agentRows']),'onlineIdleConfirms':all(c['command_status']=='CONFIRMED_IDLE' for c in cancels(end)) and all(x['current_task_id']!=row['taskId'] for x in end['agentRows']),'noResurrection':end['task']['status']=='MANUAL_TERMINATED' and all(a['stepStatus']=='FROZEN' for a in end['assignments']),'idleConfirmationIdempotent':len([e for e in end['events'] if e['eventType']=='TASK_CANCEL_CONFIRMED_IDLE'])==len([e for e in again['events'] if e['eventType']=='TASK_CANCEL_CONFIRMED_IDLE'])})

def offline_delivery():
 row=new('offline-cancel-delivery-and-recovery');d,msg=h.accept(row);d.configure(online='OFFLINE',work='BUSY');ret=term(row);o=capture(row,'offlineTerminated');d.configure();end=capture(row)
 ownBefore=[c for c in cancels(o) if c['agent_code']==d.agent];ownAfter=[c for c in cancels(end) if c['agent_code']==d.agent]
 record(row,{'offlineCancelPersisted':len(ownBefore)==1 and ownBefore[0]['command_status']=='DELIVERY_FAILED','failureSummary':any(x.get('agentId')==d.agent and x.get('cancelStatus')=='CANCEL_FAILED' for x in detail(o).get('deviceCancelResults',[])),'noPrematureRelease':any(a['current_task_id']==row['taskId'] for a in o['agentRows']),'recoveredOnlineIdle':bool(ownAfter) and all(c['command_status']=='CONFIRMED_IDLE' for c in ownAfter) and all(a['current_task_id']!=row['taskId'] for a in end['agentRows']),'terminalPreserved':end['task']['status']=='MANUAL_TERMINATED'})

def ui_fixtures():
 ids={}
 for status in ['PLANNING','SUPERVISING','PENDING_ASSIGNMENT','DOWNGRADING','EXECUTING','PENDING_MANUAL','COMPLETED','FAILED','MANUAL_TERMINATED']:
  row=fixture('ui-status-'+status,status);ids[status]=row['taskId']
 row=new('ui-real-executing-prefix',[h.st(timeout=1200),h.st(2,timeout=1200),h.st(3,timeout=1200)]);d,msg=h.prefix(row);capture(row,'beforeBrowser');ids['REAL']=row['taskId'];q.ev['uiFixtures']=ids;q.save();(R/'.local-test/f021-v174-ui-ready.json').write_text(json.dumps(ids))
 while not (R/'.local-test/f021-v174-finish').exists():time.sleep(1)
 d.configure();end=capture(row,'afterBrowser');record(row,{'browserTerminated':end['task']['status']=='MANUAL_TERMINATED','browserReasonPersisted':end['task']['manualTerminateReason']=='F174 browser actual termination','completedPrefixPreserved':any(a['stepSeq']==1 and a['stepStatus']=='COMPLETED' for a in end['assignments']),'futureFrozen':all(a['stepStatus']=='FROZEN' for a in end['assignments'] if a['stepSeq']>1),'cancelConfirmed':bool(cancels(end)) and all(c['command_status']=='CONFIRMED_IDLE' for c in cancels(end))})

def cross_task():
 first=new('cross-owner-pending-termination',[h.st(timeout=600)]);a,accept1=q.wait_message(first)
 second=q.submit('cross-owner-executing-control',[h.st(timeout=600)]);d,msg=h.accept(second);first['fixtureLevel']='Both naturally selected same available candidate before acceptance; second accepted and executes. First preselection must not revoke second owne'
 if d!=a:raise RuntimeError('fixture failed to select same candidate; no product verdict')
 before=capture(second,'beforeOtherTermination');term(first);mid=capture(second,'afterOtherTermination');ended=capture(first)
 h.feed(second,d,msg);final=capture(second)
 record(first,{'ownStepsFrozen':all(x['stepStatus']=='FROZEN' for x in ended['assignments']),'otherOwnerRetained':any(x['current_task_id']==second['taskId'] for x in mid['agentRows']),'otherCommandsUnchanged':before['commandRows']==mid['commandRows'],'noCrossTaskCancel':not cancels(ended) and not cancels(mid),'otherTaskCompletes':final['task']['status']=='COMPLETED'})
 record(second,{'controlCompleted':final['task']['status']=='COMPLETED'})

def authorization():
 row=fixture('authorization-order-controls','PENDING_MANUAL');before=capture(row,'before');row['requests']=[]
 for body in [{},{'reason':'F174 auth control','confirmed':True}]:row['requests'].append({'role':'CONFIG_ADMIN','response':raw(row['taskId'],body,api=q.cfg)})
 req=urllib.request.Request(m.l.BASE+f"/tasks/{row['taskId']}/terminate",data=b'{}',headers={'Content-Type':'application/json'},method='POST')
 try:
  with urllib.request.urlopen(req,timeout=10) as res:unauth={'http':res.status,'body':json.load(res)}
 except urllib.error.HTTPError as e:unauth={'http':e.code,'body':json.load(e)}
 row['anonymous']=unauth;o=capture(row);record(row,{'configRoleBoth403':all(x['response']['http']==403 for x in row['requests']),'anonymous401':unauth['http']==401,'businessUnchanged':all(before[k]==o[k] for k in ['task','plans','assignments','commandRows'])})

def escaped_reason_and_cancel():
 reason='F174 引号"反斜杠\\换行\n安全终止'
 row=fixture('escaped-json-reason','PENDING_MANUAL');ret=term(row,reason);o=capture(row)
 record(row,{'accepted':ret['http']==200,'exactReasonPreserved':o['task']['manualTerminateReason']==reason,'eventEscapesRoundTrip':event_json(o).get('reason')==reason})
 row=fixture('planning-cancel-direct-neighbor','PLANNING');row['request']={'reason':reason};ret=raw(row['taskId'],row['request'],'cancel');o=capture(row)
 e=next(e for e in o['events'] if e['eventType']=='MANUAL_TERMINATED');j=json.loads(e['detail']);sqlrow=next(x for x in o['eventRows'] if x['id']==e['id'])
 record(row,{'cancel200':ret['http']==200,'terminal':o['task']['status']=='MANUAL_TERMINATED','completeJsonPersisted':sqlrow['detail_summary']==e['detail'] and j.get('reason')==reason,'zeroDeviceResults':j.get('deviceCancelResults')==[],'humanSummary':e['detailSummary']==j['summary'] and not e['detailSummary'].startswith('{'),'noCommands':not o['commandRows']})

def history_compatibility():
 row={'name':'historical-event-backward-compatibility','taskId':923,'scope':'Current serialization/API against preserved V1.173 data; not current production of old event'};q.ev['cases'].append(row);o=capture(row)
 e=next(x for x in o['events'] if x['eventType']=='TASK_TERMINATED');persisted=next(x for x in o['eventRows'] if x['id']==e['id']);ordinary=next(x for x in o['events'] if x['eventType']=='GOAL_SUBMITTED')
 # Do not call F021 current JSON assertions on pre-fix events; no historical rewrite.
 q.record(row,{'historicalTextUnchanged':persisted['detail_summary']==e['detail']==e['detailSummary'],'oldHumanTextRetained':e['detailSummary'].startswith('运行操作员'),'ordinaryEventRetainsText':ordinary['detail']==ordinary['detailSummary'] and bool(ordinary['detailSummary'])})


def main():
 try:
  q.setup();q.ev['initialResourceState']={'schema':SC,'redisDb':10,'backend':18129,'model':18117,'adapters':[18132,18133,18134],'ui':15179};q.save()
  for fn in [reason_boundaries,gates,normal_and_pending,prefix_and_terminal,multiple_devices,cancellation_safety,offline_delivery,cross_task,authorization,escaped_reason_and_cancel,history_compatibility,ui_fixtures]:
   q.run(fn.__name__,fn)
 finally:q.cleanup();q.ev['endedAt']=m.now();q.save()
if __name__=='__main__':main()
