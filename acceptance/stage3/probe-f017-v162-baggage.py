"""TC054 historical DEF069 adjacency: actual four-channel sequential execution
and normal-baggage skip branch. Existing GPT robot/scanner only, no real hardware.
"""
import importlib.util,json,time,threading,copy
from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('m',Path(__file__).with_name('probe-f017-v162.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.OUT=m.output_path('SRS_F017-V1.162-baggage-final-20261105.json');q=m.Probe();rules=q.cfg('/risk-rules');q.ev['rulesBefore']=rules;original={};caps={}
def wait_msg(row,typ,seq):
 code=q.op(f'/tasks/{row["taskId"]}')['taskCode'];end=time.monotonic()+15
 while time.monotonic()<end:
  found=[(d,x['message']) for d in q.devices for x in d.messages_for(code,typ) if x['message']['stepSeq']==seq]
  if found:return found[-1]
  time.sleep(.1)
 raise TimeoutError('missing step '+str(seq)+' '+typ)
def setup():
 for code,port,typ,types in [('G160_F016_A',18132,'MOBILE_ROBOT',['CAP_NAVIGATION']),('G145_F013_SCAN',18133,'BAGGAGE_SCANNER',['CAP_BAGGAGE_MEASURE','CAP_OVERSIZE_ALERT']),('G145_F013_DISPLAY',18134,'SMART_DISPLAY',['CAP_INFO_DISPLAY'])]:
  assert m.sql(f"select count(*) from {m.SC}.device_agents a join {m.SC}.devices d on d.id=a.device_id where d.device_code={m.lit(code)} and a.current_task_id is not null")=='0'
  original[code]={'device':m.rows(f"select row_to_json(d)::text from {m.SC}.devices d where device_code={m.lit(code)}")[0],'capabilities':q.cfg(f'/devices/{code}/capabilities')}
  d=m.Device(code,port);d.simtype=typ;d.healthcaps=types;q.devices.append(d);d.token=q.cfg(f'/devices/{code}/device-token/rotate','POST')['accessToken'];q.cfg(f'/devices/{code}/connection-test','POST');q.cfg(f'/devices/{code}/status','POST',{'status':'ACTIVE'});q.cfg(f'/devices/{code}/connection-test','POST');d.agent=next(a['agentId'] for a in q.cfg('/device-agents?page=1&size=100')['content'] if a['deviceCode']==code);d.heartbeat();threading.Thread(target=d.loop,daemon=True).start()
  for cap in types:q.cfg(f'/devices/{code}/capabilities/{cap}/test','POST');q.cfg(f'/devices/{code}/capabilities/{cap}/status','POST',{'status':'ENABLED'})
  caps.update({c['capabilityType']:c for c in q.cfg(f'/devices/{code}/capabilities') if c['capabilityType'] in types})
 q.ev['resourcesBefore']=copy.deepcopy(original);
 for record in q.ev['resourcesBefore'].values():
  for key in list(record['device']):
   if 'token' in key.lower():record['device'][key]='[REDACTED]'
 q.ev['credentialRedaction']='Device token metadata removed before write';q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False});q.save()
def values(schema):
 result={}
 for p in schema:
  v=p.get('defaultValue')
  if v is None or v=='':continue
  if p['type'] in ['Integer','Long']:v=int(v)
  elif p['type'] in ['Double','Float','Number']:v=float(v)
  elif p['type']=='Boolean':v=str(v).lower()=='true'
  result[p['name']]=v
 return result
def run_case(oversize):
 for d in q.devices:d.configure()
 types=['CAP_BAGGAGE_MEASURE','CAP_OVERSIZE_ALERT','CAP_INFO_DISPLAY','CAP_NAVIGATION'];conditions=['measureStatus=SUCCESS','reportStatus=SUCCESS','displayStatus=SUCCESS','routeGenerated=true'];steps=[]
 for seq,(cap,condition) in enumerate(zip(types,conditions),1):steps.append({'stepSeq':seq,'stepGoal':'Synthetic baggage action '+cap,'capabilityType':cap,'inputParams':values(caps[cap]['inputParams']),'precondition':'device online','completionCondition':condition,'failureHandling':'manual handling','stepTimeout':180})
 marker='F162_BAGGAGE_'+('OVERSIZE' if oversize else 'NORMAL');q.cases[marker]={'steps':steps};(R/'.local-test/f017-v162-cases.json').write_bytes(json.dumps(q.cases).encode());body={'taskGoal':marker+' synthetic baggage to F2_TEST_GATE','taskFamily':'OVERSIZE_BAGGAGE_HANDLING','sceneParams':{'targetLocation':'F2_TEST_GATE','dimensionThresholdCm':158,'weightThresholdKg':23,'baggageInfo':'synthetic baggage fixture'}};response=m.p.raw(q.op,'/tasks',body);tid=int(m.sql(f'select id from {m.SC}.tasks where task_goal={m.lit(body["taskGoal"])} order by id desc limit 1'));row={'name':marker,'taskId':tid,'request':body,'response':response,'steps':steps};q.tasks.append(tid);q.ev['cases'].append(row);row['frozen']=q.observe(tid);q.save()
 for seq in range(1,5 if oversize else 2):
  d,a=wait_msg(row,'TASK_ACCEPT',seq);q.response(d,a);d,msg=wait_msg(row,'EXECUTE_CAPABILITY',seq);output={'measureStatus':'SUCCESS','isOversize':oversize,'baggageInfo':'synthetic baggage fixture','reportStatus':'SUCCESS','displayStatus':'SUCCESS','routeGenerated':True};res=d.report('EXECUTION_FEEDBACK',{'commandId':msg['commandId'],'attemptNo':0,'executionResult':'SUCCESS','outputParams':output});row.setdefault('feedbackCalls',[]).append({'step':seq,'response':res});d.state['workStatus']='IDLE'
 row['after']=q.observe(tid);o=row['after'];execs=[c for c in o['commandRows'] if c['command_type']=='EXECUTE_CAPABILITY'];q.record(row,{'autonomousFrozen':len(o['plans'])==1 and o['plans'][0]['source']=='AUTONOMOUS' and bool(o['plans'][0].get('frozenAt')),'allThreeChecksPass':all(o['plans'][0][k]=='PASS' for k in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']),'requiredFourChannelsPresent':set(s['capabilityType'] for s in o['plans'][0]['planSteps'])==set(types),'completed':o['task']['status']=='COMPLETED','feedback200':all(x['response']['http']==200 for x in row['feedbackCalls']),'expectedExecuteOrder':[c['step_seq'] for c in execs]==([1,2,3,4] if oversize else [1]),'normalSkipsRemaining':oversize or all(a['stepStatus']=='SKIPPED' for a in o['assignments'] if a['stepSeq']>1),'deviceMessagesMatchDb':sum(len(d.messages_for(o['task']['taskCode'],'EXECUTE_CAPABILITY')) for d in q.devices)==len(execs)})
try:setup();q.run('oversize-four-channels',lambda:run_case(True));q.run('normal-skip',lambda:run_case(False))
finally:
 for rule in rules:
  if rule['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':rule['enabled']})
 q.cleanup()
 # UNTESTED cannot be restored through status API (only ENABLED/DISABLED); scoped
 # SQL restores original configuration while keeping capability-test history.
 for code,state in original.items():
  for cap in state['capabilities']:m.sql(f"update {m.SC}.device_capabilities set capability_status={m.lit(cap['capabilityStatus'])} where device_id=(select id from {m.SC}.devices where device_code={m.lit(code)}) and capability_code={m.lit(cap['capabilityCode'])}")
 q.ev['capabilityStatusesRestored']=True;q.ev['endedAt']=m.now();q.save()
