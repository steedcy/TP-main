"""V2.4 F017 complete independent HTTP/persistence/protocol round, fixed V1.162.
G160_F016_A/B/C are inactive GPT-owned reusable protocol devices, not real hardware.
Only dispatch-injection cases alter OWN frozen plan JSON after validation to reach
the final dispatch guard. Original and injected plans are saved; all other paths
use public product APIs. A scoped trigger observes transient task state writes.
"""
import importlib.util,json,time,copy,subprocess,re
from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('m',Path(__file__).with_name('probe-f017-v162.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
q=m.Probe();q.setup();rules=q.cfg('/risk-rules');q.ev['rulesBefore']=rules
q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
m.sql(f"""CREATE TABLE {m.SC}.gpt_f017_states(id bigserial,task_id bigint,old_status text,new_status text,at timestamptz default clock_timestamp());
CREATE FUNCTION {m.SC}.gpt_f017_capture() RETURNS trigger LANGUAGE plpgsql AS $fn$ BEGIN IF NEW.task_goal LIKE 'F162_%' THEN INSERT INTO {m.SC}.gpt_f017_states(task_id,old_status,new_status) VALUES(NEW.id,CASE WHEN TG_OP='INSERT' THEN NULL ELSE OLD.status END,NEW.status); END IF; RETURN NEW; END $fn$;
CREATE TRIGGER gpt_f017_capture AFTER INSERT OR UPDATE OF status ON {m.SC}.tasks FOR EACH ROW EXECUTE FUNCTION {m.SC}.gpt_f017_capture();""")
def st(seq=1,goal='前往区域',condition='routeGenerated=true',timeout=180,cap='CAP_NAVIGATION',params=None):
 x=m.p.step(seq=seq,cap=cap,params=params);x.update(stepGoal=goal,completionCondition=condition,stepTimeout=timeout);return x
def wait_for(fn,timeout=15):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  v=fn()
  if v:return v
  time.sleep(.1)
 raise TimeoutError('Expected condition not observed')
def feedback(row,d,msg,result='SUCCESS',output=None,reason=None):
 body={'commandId':msg['commandId'],'attemptNo':msg['attemptNo'],'executionResult':result,'outputParams':output or {'routeGenerated':True}}
 if reason:body['reasonCode']=reason
 response=d.report('EXECUTION_FEEDBACK',body);row.setdefault('feedbackCalls',[]).append({'request':body,'response':response});return response
def ui(row,phase,completed,total,current):
 result=subprocess.run(['node',str(R/'acceptance/stage3/retest-f017-v162-ui.cjs'),str(row['taskId']),phase,str(completed),str(total),str(current)],cwd=R,capture_output=True,text=True,encoding='utf-8',timeout=55)
 row.setdefault('ui',[]).append({'phase':phase,'exit':result.returncode,'stdout':result.stdout,'stderr':result.stderr});q.save()
 if result.returncode:raise RuntimeError('UI fixture failed: '+result.stderr[-200:])
def execute(row):
 d,msg=q.wait_message(row);row['acceptResponse']=q.response(d,msg);return d,q.wait_message(row,'EXECUTE_CAPABILITY',d)[1]
def observed(row):time.sleep(.3);row['after']=q.observe(row['taskId']);return row['after']
def cmds(o):return [x for x in o['commandRows'] if x['command_type']=='EXECUTE_CAPABILITY']
def event(o,kind):return any(x['eventType']==kind for x in o['events'])
def reset():
 for d in q.devices:d.delivery_failures=set()
 q.reset()
def normal():
 reset();row=q.submit('ordered-receipt',[st(),st(2,goal='空间引导')]);d,msg=execute(row);row['receiptOnly']=q.observe(row['taskId']);time.sleep(2);row['afterReceiptWait']=q.observe(row['taskId']);ui(row,'receipt',0,2,1)
 ret=feedback(row,d,msg);d.state['workStatus']='IDLE';d2,accept=q.wait_message(row,'TASK_ACCEPT');row['firstCompleted']=q.observe(row['taskId']);ui(row,'middle',1,2,2);q.response(d2,accept);msg2=q.wait_message(row,'EXECUTE_CAPABILITY',d2)[1];feedback(row,d2,msg2);d2.state['workStatus']='IDLE';o=observed(row);ui(row,'completed',2,2,'none')
 c=cmds(o);e=o['events'];row['receiptMeaning']='Adapter HTTP200 payload received=true/已收到 is transport/business receipt only; execution feedback deliberately deferred. TASK_ACCEPT separately acknowledges assignment.'
 q.record(row,{'receiptNotComplete':row['afterReceiptWait']['assignments'][0]['stepStatus']=='EXECUTING','secondNotSentBeforeCondition':all(x['step_seq']==1 for x in cmds(row['afterReceiptWait'])),'firstConditionReleasesOwner':all(a['current_task_id']!=row['taskId'] for a in row['firstCompleted']['agentRows']),'bothFeedback200':all(x['response']['http']==200 for x in row['feedbackCalls']),'completed':o['task']['status']=='COMPLETED','twoLogicalExecuteIds':len({x['command_id'] for x in c})==2,'idsFormat':all(re.fullmatch(r'CMD-\d{14}-[0-9A-F]{8}',x['command_id']) for x in o['commandRows']),'order':len(c)==2 and c[0]['step_seq']==1 and c[1]['step_seq']==2,'fullEvents':all(event(o,t) for t in ['STEP_DISPATCHED','EXECUTION_FEEDBACK_RECEIVED','STEP_COMPLETED','TASK_COMPLETED'])})
def delivery(first_only=True):
 reset();row=q.submit('delivery-retry-success' if first_only else 'delivery-retry-failure',[st(),st(2)]);d,accept=q.wait_message(row);code=q.op(f'/tasks/{row["taskId"]}')['taskCode'];d.delivery_failures={(code,1,0)} if first_only else {(code,1,0),(code,1,1)};q.response(d,accept)
 if first_only:
  wait_for(lambda:any(x['message']['commandType']=='EXECUTE_CAPABILITY' and x['message']['attemptNo']==1 for x in d.messages_for(code)));msg=next(x['message'] for x in d.messages_for(code,'EXECUTE_CAPABILITY') if x['message']['attemptNo']==1);feedback(row,d,msg);d.state['workStatus']='IDLE';d2,msg2=q.wait_message(row,'TASK_ACCEPT');q.response(d2,msg2);feedback(row,d2,q.wait_message(row,'EXECUTE_CAPABILITY',d2)[1]);d2.state['workStatus']='IDLE'
 else:
  wait_for(lambda:bool(q.observe(row['taskId'])['exceptions']));q.terminate(row)
 o=observed(row);c=[x for x in cmds(o) if x['step_seq']==1];q.record(row,{'sameLogicalId':len({x['command_id'] for x in c})==1,'attemptZeroAndOneOnly':sorted(x['attempt_no'] for x in c)==[0,1],'oneRetryEvent':sum(x['eventType']=='STEP_RETRY_DISPATCHED' for x in o['events'])==1,'rightOutcome':o['task']['status']=='COMPLETED' if first_only else any(x['exception_type']=='STEP_FAILED' for x in o['exceptions']),'failureRecorded':event(o,'STEP_RETRY_DISPATCHED') and (first_only or event(o,'STEP_FAILED'))})
def predicate(name,expected,output,positive=False):
 reset();row=q.submit(name,[st(condition='routeGenerated='+str(expected).lower()),st(2)]);d,msg=execute(row);feedback(row,d,msg,output={'routeGenerated':output});
 if positive:
  d.state['workStatus']='IDLE';d2,a=q.wait_message(row);q.response(d2,a);feedback(row,d2,q.wait_message(row,'EXECUTE_CAPABILITY',d2)[1]);d2.state['workStatus']='IDLE'
 else:
  retry=q.wait_message(row,'EXECUTE_CAPABILITY',d)[1];feedback(row,d,retry,output={'routeGenerated':output});time.sleep(.3)
 o=observed(row);q.record(row,{'matchesPlanPredicate':o['task']['status']=='COMPLETED' if positive else not any(a['stepSeq']==1 and a['stepStatus']=='COMPLETED' for a in o['assignments']),'noPrematureNextStep':positive or not any(x['step_seq']==2 for x in cmds(o)),'failureTrace':positive or event(o,'STEP_FAILED'),'httpSuccessNotBusinessSuccess':all(x['response']['http']==200 for x in row['feedbackCalls'])})
def timeout():
 reset();row=q.submit('real-silent-timeout',[st(timeout=30),st(2)]);d,msg=execute(row);row['before']=q.observe(row['taskId']);start=time.monotonic();time.sleep(20);row['beforeThreshold']=q.observe(row['taskId']);wait_for(lambda:event(q.observe(row['taskId']),'STEP_TIMEOUT_DETECTED'),25);row['elapsedSeconds']=time.monotonic()-start;o=observed(row)
 a=next(a for a in o['assignments'] if a['stepSeq']==1);c=next(c for c in cmds(o) if c['command_id']==msg['commandId']);row['lateFeedback']=feedback(row,d,msg);row['afterLate']=q.observe(row['taskId']);q.record(row,{'beforeThirtyStillExecuting':row['beforeThreshold']['assignments'][0]['stepStatus']=='EXECUTING','realTimeoutRange':28<=row['elapsedSeconds']<=43,'stepFailedTimeout':a['stepStatus']=='FAILED' and a['executionResult']=='TIMEOUT' and a['reasonCode']=='ERR_EXECUTION_TIMEOUT','commandTimedOut':c['command_status']=='TIMED_OUT','exceptionPersisted':any(x['exception_type']=='EXECUTION_TIMEOUT' for x in o['exceptions']),'noNextStep':not any(c['step_seq']==2 for c in cmds(o)),'agentReleased':all(x['current_task_id']!=row['taskId'] for x in o['agentRows']),'lateCannotAdvance':not any(c['step_seq']==2 for c in cmds(row['afterLate']))})
def safety(key):
 reset();row=q.submit('dispatch-block-'+key,[st()]);d,accept=q.wait_message(row);o=q.observe(row['taskId']);plan=next(v for v in o['plans'] if v['id']==o['task']['currentPlanVersionId']);steps=json.loads(plan['planSteps']) if isinstance(plan['planSteps'],str) else plan['planSteps'];row['originalFrozenPlan']=copy.deepcopy(plan);steps[0]['inputParams'][key]=1
 # Controlled SQL is solely to reach dispatch-phase defense after a legal frozen validation.
 row['injection']='Scoped own frozen plan inputParams only; not an API mutation/normal reachability claim';m.sql(f"update {m.SC}.plan_versions set plan_steps={m.lit(json.dumps(steps,ensure_ascii=False))}::json where id={plan['id']}");row['injectedSteps']=steps;q.response(d,accept);o=observed(row)
 q.record(row,{'blockedEvent':any(e['eventType']=='COMMAND_DISPATCH_BLOCKED' and e['reasonCode']=='ERR_MOTION_SAFETY_FIELD' for e in o['events']),'stepFailed':any(a['stepStatus']=='FAILED' and a['reasonCode']=='ERR_MOTION_SAFETY_FIELD' for a in o['assignments']),'zeroExecuteRecords':not cmds(o),'zeroDeviceBusinessMessages':not any(d.messages_for(o['task']['taskCode'],'EXECUTE_CAPABILITY') for d in q.devices)})
def invalid(name,step=None,mode=None):
 reset();marker='F162_'+name.upper().replace('-','_');q.cases[marker]={'steps':[step or st()],**(mode or {})};(R/'.local-test/f017-v162-cases.json').write_bytes(json.dumps(q.cases).encode());body={'taskGoal':marker+' synthetic navigation','taskFamily':q.family,'sceneParams':{'targetLocation':'F2_TEST_GATE'}};response=m.p.raw(q.op,'/tasks',body);tid=int(m.sql(f'select id from {m.SC}.tasks where task_goal={m.lit(body["taskGoal"])} order by id desc limit 1'));row={'name':name,'taskId':tid,'request':body,'response':response};q.tasks.append(tid);q.ev['cases'].append(row);o=observed(row);q.record(row,{'noCommands':not o['commandRows'],'noExecution':not any(d.messages_for(o['task']['taskCode'],'EXECUTE_CAPABILITY') for d in q.devices),'safeManual':o['task']['status']=='PENDING_MANUAL','reasonRecorded':bool(o['events'])})
 if name=='model-http-failure':
  row['markFailed']=m.p.raw(q.op,f'/tasks/{tid}/manual-actions',{'action':'MARK_FAILED','reason':'Synthetic independent failure closure'});row['afterFailed']=q.observe(tid);q.save()
def baseline():
 reset();a=q.devices[0];body={'templateName':'G162 F017 baseline','templateIntent':q.family,'inputParams':copy.deepcopy(q.definitionBody['sceneParams']),'steps':[{'capabilityType':'CAP_NAVIGATION','paramMapping':[{'target':'targetLocation','source':'TEMPLATE_INPUT.targetLocation'}],'stepTimeout':180,'completionCondition':'routeGenerated=true'}]};t=q.cfg('/baseline-templates','POST',body);q.templates.append(t['id']);q.save();res=q.cfg(f"/baseline-templates/{t['id']}/dry-run",'POST',{'inputParams':{'targetLocation':'F2_TEST_GATE'},'simulatedDevices':[{'stepSeq':1,'agentId':a.agent}]});row={'name':'baseline-trial','taskId':res['taskId']};q.tasks.append(row['taskId']);q.ev['cases'].append(row);d,msg=execute(row);feedback(row,d,msg);d.state['workStatus']='IDLE';o=observed(row);q.record(row,{'completed':o['task']['status']=='COMPLETED'});q.cfg(f"/baseline-templates/{t['id']}/enable",'POST')
 reset();row=q.submit('baseline-high-risk',high=True);row['downgrading']=q.observe(row['taskId']);d,msg=execute(row);feedback(row,d,msg);d.state['workStatus']='IDLE';o=observed(row);q.record(row,{'downgrading':row['downgrading']['task']['status']=='DOWNGRADING','baselineSource':any(v['source']=='BASELINE_TEMPLATE' for v in o['plans']),'completed':o['task']['status']=='COMPLETED'});q.cfg(f"/baseline-templates/{t['id']}/disable",'POST')
def terminated():
 reset();row=q.submit('manual-terminated');d,msg=execute(row);row['before']=q.observe(row['taskId']);q.terminate(row);o=observed(row);q.record(row,{'manualTerminated':o['task']['status']=='MANUAL_TERMINATED','event':event(o,'MANUAL_TERMINATED'),'cancelSent':any(c['command_type']=='TASK_CANCEL' for c in o['commandRows'])})
def run(name,fn):
 q.run(name,fn)
 # Reconcile this round's tasks before resetting its own adapter/agent fixtures.
 for tid in q.tasks:
  if q.op(f'/tasks/{tid}')['status'] not in ['COMPLETED','FAILED','MANUAL_TERMINATED']:q.terminate({'taskId':tid})
try:
 for name,fn in [('ordered-receipt',normal),('delivery-success',delivery),('delivery-failure',lambda:delivery(False)),('false-predicate-counterexample',lambda:predicate('false-predicate-counterexample',False,True)),('false-predicate-legal-control',lambda:predicate('false-predicate-legal-control',False,False,True)),('true-predicate-counterexample',lambda:predicate('true-predicate-counterexample',True,False)),('real-silent-timeout',timeout)]:run(name,fn)
 for key in ['速度','加速度','姿态','路径点','避障','急停','限速','失联停靠']:run('safety-'+key,lambda key=key:safety(key))
 for name,step,mode in [('model-http-failure',None,{'planHttpStatus':503}),('model-malformed',None,{'planMode':'MALFORMED'}),('validation-structure',{k:v for k,v in st().items() if k!='precondition'},None),('validation-capability',st(cap='CAP_F017_FICTIONAL'),None),('validation-motion',st(params={'targetLocation':'F2_TEST_GATE','speed':2}),None)]:run(name,lambda name=name,step=step,mode=mode:invalid(name,step,mode))
 run('baseline',baseline);run('termination',terminated)
finally:
 q.ev['observedStateWrites']=m.rows(f'select row_to_json(x)::text from {m.SC}.gpt_f017_states x order by id');m.sql(f'DROP TRIGGER gpt_f017_capture ON {m.SC}.tasks; DROP FUNCTION {m.SC}.gpt_f017_capture(); DROP TABLE {m.SC}.gpt_f017_states;')
 for t in q.templates:
  try:q.cfg(f'/baseline-templates/{t}/disable','POST')
  except Exception:pass
 for rule in rules:
  if rule['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':rule['enabled']})
 q.ev['rulesAfter']=q.cfg('/risk-rules');q.cleanup();q.ev['endedAt']=m.now();q.save()
