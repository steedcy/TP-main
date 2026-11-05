"""Final missing F017 branches: exact callback replay, model-fault baseline,
and actual 30s timeout with no alternate candidate (stable terminal observation).
Run sequentially after final.py releases the three GPT protocol ports.
"""
import importlib.util,json,time,copy,subprocess,urllib.request,urllib.error
from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('m',Path(__file__).with_name('probe-f017-v162.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.OUT=m.output_path('SRS_F017-V1.162-extra-20261105.json');q=m.Probe();q.setup();rules=q.cfg('/risk-rules');q.ev['rulesBefore']=rules;q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
def wait(fn,timeout=15):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  value=fn()
  if value:return value
  time.sleep(.1)
 raise TimeoutError('Expected observation absent')
def execute(row):
 d,a=q.wait_message(row);row['acceptResponse']=q.response(d,a);return d,q.wait_message(row,'EXECUTE_CAPABILITY',d)[1]
def observe(row):time.sleep(.2);row['after']=q.observe(row['taskId']);return row['after']
def raw_report(d,packet):
 req=urllib.request.Request(f'http://127.0.0.1:18129/device-api/v1/agents/{d.agent}/report',json.dumps(packet).encode(),{'Content-Type':'application/json','Authorization':'Bearer '+d.token},method='POST')
 try:
  with urllib.request.urlopen(req,timeout=15) as response:return {'http':response.status,'body':json.load(response)}
 except urllib.error.HTTPError as ex:return {'http':ex.code,'body':json.load(ex)}
def replay():
 q.reset();row=q.submit('exact-feedback-replay');d,msg=execute(row);packet={'reportType':'EXECUTION_FEEDBACK','reportedAt':m.now(),'feedback':{'commandId':msg['commandId'],'attemptNo':0,'executionResult':'SUCCESS','outputParams':{'routeGenerated':True}}};row['exactPacketWithoutCredentials']=copy.deepcopy(packet);row['first']=raw_report(d,packet);d.state['workStatus']='IDLE';row['beforeReplay']=q.observe(row['taskId']);row['sameByteReplay']=raw_report(d,packet);row['afterReplay']=q.observe(row['taskId']);row['invalidAttempts']=[]
 for n in [-1,2]:
  bad=copy.deepcopy(packet);bad['reportedAt']=m.now();bad['feedback']['attemptNo']=n;row['invalidAttempts'].append({'attempt':n,'response':raw_report(d,bad)})
 wrong=q.devices[1] if d!=q.devices[1] else q.devices[0];other=copy.deepcopy(packet);other['reportedAt']=m.now();row['wrongAgent']=raw_report(wrong,other);o=observe(row)
 q.record(row,{'bothExactReports200':row['first']['http']==200 and row['sameByteReplay']['http']==200,'singleCompletionEvent':sum(e['eventType']=='STEP_COMPLETED' for e in o['events'])==1,'replayNoExtraEvent':len(row['beforeReplay']['events'])==len(row['afterReplay']['events']),'onlyOneExecuteTransmission':sum(len(d.messages_for(o['task']['taskCode'],'EXECUTE_CAPABILITY')) for d in q.devices)==1,'badAttempts400':all(x['response']['http']==400 for x in row['invalidAttempts']),'wrongAgentRejected':row['wrongAgent']['http'] in [400,403,409],'completedPreserved':o['task']['status']=='COMPLETED'})
def template_trial():
 q.reset();a=q.devices[0];body={'templateName':'G162 F017 timeout baseline','templateIntent':q.family,'inputParams':copy.deepcopy(q.definitionBody['sceneParams']),'steps':[{'capabilityType':'CAP_NAVIGATION','paramMapping':[{'target':'targetLocation','source':'TEMPLATE_INPUT.targetLocation'}],'stepTimeout':30,'completionCondition':'routeGenerated=true'}]};t=q.cfg('/baseline-templates','POST',body);q.templates.append(t['id']);q.save();res=q.cfg(f"/baseline-templates/{t['id']}/dry-run",'POST',{'inputParams':{'targetLocation':'F2_TEST_GATE'},'simulatedDevices':[{'stepSeq':1,'agentId':a.agent}]});row={'name':'timeout-template-trial','taskId':res['taskId']};q.tasks.append(row['taskId']);q.ev['cases'].append(row);d,msg=execute(row);q.complete(row,d);d.state['workStatus']='IDLE';o=observe(row);q.record(row,{'completed':o['task']['status']=='COMPLETED'});q.cfg(f"/baseline-templates/{t['id']}/enable",'POST')
def fault_baseline():
 q.reset();marker='F162_MODEL_FAILURE_WITH_VALID_BASELINE';q.cases[marker]={'planHttpStatus':503};(R/'.local-test/f017-v162-cases.json').write_bytes(json.dumps(q.cases).encode());body={'taskGoal':marker+' synthetic navigation','taskFamily':q.family,'sceneParams':{'targetLocation':'F2_TEST_GATE'}};response=m.p.raw(q.op,'/tasks',body);tid=int(m.sql(f'select id from {m.SC}.tasks where task_goal={m.lit(body["taskGoal"])} order by id desc limit 1'));row={'name':'model-failure-valid-baseline','taskId':tid,'request':body,'response':response};q.tasks.append(tid);q.ev['cases'].append(row);row['beforeAcceptance']=q.observe(tid);d,msg=execute(row);q.complete(row,d);d.state['workStatus']='IDLE';o=observe(row);base=[v for v in o['plans'] if v['source']=='BASELINE_TEMPLATE'];q.record(row,{'modelFaultRecorded':any(e.get('reasonCode')=='ERR_PLANNING_MODEL_FAILED' for e in o['events']),'validatedFrozenBaseline':bool(base) and all(v.get('frozenAt') for v in base),'downgrading':row['beforeAcceptance']['task']['status']=='DOWNGRADING','completed':o['task']['status']=='COMPLETED','noUnvalidatedOriginalExecution':not any(v['source']=='AUTONOMOUS' and v.get('frozenAt') for v in o['plans'])})
def timeout():
 q.reset();q.devices[1].configure(online='OFFLINE');row=q.submit('baseline-silent-timeout-terminal',high=True);d,msg=execute(row);row['before']=q.observe(row['taskId']);start=time.monotonic();time.sleep(20);row['beforeThirty']=q.observe(row['taskId']);wait(lambda:any(e['eventType']=='STEP_TIMEOUT_DETECTED' for e in q.observe(row['taskId'])['events']),25);row['elapsedSeconds']=time.monotonic()-start;o=observe(row);row['assignmentSql']=m.rows(f"select row_to_json(x)::text from {m.SC}.task_step_assignments x where task_id={row['taskId']}");c=next(c for c in o['commandRows'] if c['command_id']==msg['commandId']);q.record(row,{'beforeThirtyExecuting':row['beforeThirty']['assignments'][0]['stepStatus']=='EXECUTING','timeoutThirtyToForty':28<=row['elapsedSeconds']<=43,'failedTimeoutPersisted':any(a['step_status']=='FAILED' and a['execution_result']=='TIMEOUT' and a['reason_code']=='ERR_EXECUTION_TIMEOUT' for a in row['assignmentSql']),'commandTimedOut':c['command_status']=='TIMED_OUT','exceptionPersisted':any(e['exception_type']=='EXECUTION_TIMEOUT' for e in o['exceptions']),'pendingManual':o['task']['status']=='PENDING_MANUAL','agentReleased':all(a['current_task_id']!=row['taskId'] for a in o['agentRows']),'noSecondReplan':not o['task']['replanUsed'] and not any(e['eventType']=='REPLANNING_TRIGGERED' for e in o['events'])})
 result=subprocess.run(['node',str(R/'acceptance/stage3/retest-f017-v162-ui.cjs'),str(row['taskId']),'silent-timeout','0','1','none'],cwd=R,capture_output=True,text=True,encoding='utf-8',timeout=55);row['ui']={'exit':result.returncode,'stdout':result.stdout,'stderr':result.stderr};q.save()
try:
 q.run('exact-replay',replay);q.run('template-trial',template_trial);q.run('model-error-baseline',fault_baseline);q.run('terminal-timeout',timeout)
 q.ev['coreSmoke']={path:q.op(path) for path in ['/tasks?page=1&size=2','/device-agents?page=1&size=2','/dashboard/overview']};q.save()
finally:
 for tid in q.templates:
  try:q.cfg(f'/baseline-templates/{tid}/disable','POST')
  except Exception as ex:q.ev.setdefault('cleanupDiagnostics',[]).append(str(ex))
 for rule in rules:
  if rule['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':rule['enabled']})
 q.cleanup();q.ev['endedAt']=m.now();q.save()
