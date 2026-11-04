"""V2.4 complete F015 round. Product V1.155 stays fixed; F does not stop later cases.

Requires own JAR18129/model18117/robot18132/Vite15179. Starts a second own
simulator18133. Credentials remain in local helpers/DPAPI, never in evidence.
Only the declared GPT schema is used. SQL fixtures are restricted to a new
synthetic prefix-family definition and deliberate corruption of an owned template.
"""
import copy, importlib.util, json, re, socket, subprocess, time, traceback
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('old',ROOT/'acceptance/stage3/probe-f015-v154.py')
old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
p=old.p;sql=old.sql;SC=old.SC
SHA='78eb774a0546216deaa42c2fc2a5dc6ee8f661dd'
OUT=ROOT/'acceptance/stage3/evidence/SRS_F015-V1.155-full-round-20261104.json'
STATE=ROOT/'.local-test/f015-v155-state.json'

def now():return datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
def literal(value):return "'"+str(value).replace("'","''")+"'"

class Probe:
 def __init__(self):
  assert not OUT.exists(),'Use a new evidence file, do not overwrite'
  self.cfg=p.l.API('配置管理员');self.op=p.l.API('运行操作员')
  self.templates=[];self.tasks=[];self.definitions=[];self.modelCases={};self.tokens={}
  self.tokens['G126_ROBOT']=json.loads(p.l.protect((ROOT.parent/'tip/.local-test/gpt-f007-v126-robot.dpapi').read_bytes(),True))['token']
  self.ports={'G126_ROBOT':18132}
  self.ev={'tag':'V1.155','productSha':SHA,'executionBaseline':'V2.4','startedAt':now(),
   'timezone':'Asia/Shanghai','schema':SC,'redisDb':10,'cases':[],'trials':[],
   'planned':['high-valid','malformed-plan','planning-unavailable','understanding-unavailable',
    'capability-hard-fail','constraint-hard-fail','structure-hard-fail-six','valid-five-steps',
    'no-template','disabled-template','manual-ui-switch','fewer-steps','exact-family',
    'recent-trial-reversed-enable','multi-candidate-recovered','multi-candidate-exhausted',
    'frozen-live-edit','autonomous-replan-neighbor','readonly-ui'],
   'rulesBefore':self.cfg('/risk-rules'),'primaryDeviceBefore':self.cfg('/devices/G126_ROBOT'),
   'primaryCapabilitiesBefore':self.cfg('/devices/G126_ROBOT/capabilities'),
   'health':p.l.request('http://127.0.0.1:18129/actuator/health')}
  self.save()
 def save(self):
  self.ev['ownedTemplateIds']=self.templates;self.ev['ownedTaskIds']=self.tasks;self.ev['ownedDefinitionIds']=self.definitions
  OUT.write_bytes(json.dumps(self.ev,ensure_ascii=False,indent=2).encode('utf-8'))
  STATE.write_bytes(json.dumps({'family':getattr(self,'family',None),'definitionId':getattr(self,'definitionId',None),
   'templates':self.templates,'tasks':self.tasks,'cases':{x['name']:x.get('taskId') for x in self.ev['cases']},
   'uiTaskId':getattr(self,'uiTaskId',None),'uiTemplateId':getattr(self,'uiTemplateId',None)},ensure_ascii=False,indent=2).encode('utf-8'))
 def agents(self):return self.cfg('/device-agents?page=1&size=100')['content']
 def agent(self,code='G126_ROBOT'):return next(x for x in self.agents() if x['deviceCode']==code)
 def idle(self):
  for _ in range(180):
   if all(self.agent(c)['onlineStatus']=='ONLINE' and self.agent(c)['workStatus']=='IDLE' for c in self.ports):return
   time.sleep(.25)
  raise RuntimeError('Own robot(s) not idle/online')
 def scenario(self,value):
  for code,port in self.ports.items():
   v=value.get(code,'SUCCESS') if isinstance(value,dict) else value
   p.l.request(f'http://127.0.0.1:{port}/device-api/v1/control/scenario','POST',{'scenarioResult':v},token=self.tokens[code])
 def create_definition(self):
  self.definitionBody={'taskName':'G155 F015 complete round '+datetime.now().strftime('%H%M%S'),
   'goalTemplate':'Synthetic navigation to selected destination','sceneParams':[{'name':'targetLocation','type':'String','required':True,'defaultValue':'F2_TEST_GATE'}],
   'availableCapabilityTypes':['CAP_NAVIGATION'],'constraintDescription':'Synthetic F015 isolated navigation','completionCondition':'routeGenerated=true'}
  d=self.cfg('/task-definitions','POST',self.definitionBody);self.definitionId=d['id'];self.family=d['definitionCode'];self.definitions.append(d['id'])
  self.cfg(f"/task-definitions/{d['id']}/enable",'POST');self.ev['definition']=self.cfg(f"/task-definitions/{d['id']}");self.save()
 def create(self,name,count=1,family=None):
  body={'templateName':'G155 '+name+' '+datetime.now().strftime('%H%M%S%f'),'templateIntent':family or self.family,
   'inputParams':copy.deepcopy(self.definitionBody['sceneParams']),
   'steps':[{'capabilityType':'CAP_NAVIGATION','paramMapping':[{'target':'targetLocation','source':'TEMPLATE_INPUT.targetLocation'}],
    'stepTimeout':60,'completionCondition':'routeGenerated=true'} for _ in range(count)]}
  t=self.cfg('/baseline-templates','POST',body);self.templates.append(t['id']);self.save();return t
 def wait(self,tid,timeout=100):
  deadline=time.monotonic()+timeout
  while time.monotonic()<deadline:
   t=self.op(f'/tasks/{tid}')
   if t['status'] in ['COMPLETED','FAILED','PENDING_MANUAL','MANUAL_TERMINATED']:return p.observe(self.op,tid)
   time.sleep(.25)
  return p.observe(self.op,tid)
 def trial(self,t,enable=True):
  self.scenario('SUCCESS');self.idle();a=self.agent()
  body={'inputParams':{'targetLocation':'F2_TEST_GATE'},'simulatedDevices':[{'stepSeq':i+1,'agentId':a['agentId']} for i in range(len(t['steps']))]}
  response=self.cfg(f"/baseline-templates/{t['id']}/dry-run",'POST',body);tid=response['taskId'];self.tasks.append(tid)
  row={'templateId':t['id'],'request':body,'response':response};self.ev['trials'].append(row);self.save()
  row['observed']=self.wait(tid);row['templateAfterTrial']=self.cfg(f"/baseline-templates/{t['id']}");self.save()
  if row['observed']['task']['status']!='COMPLETED' or row['templateAfterTrial']['templateStatus']!='DRY_RUN_PASSED':raise RuntimeError('Fixture trial did not genuinely pass')
  if enable:self.cfg(f"/baseline-templates/{t['id']}/enable",'POST')
  return row
 def disable(self,tid):
  self.cfg(f'/baseline-templates/{tid}/disable','POST')
 def disable_all(self):
  for tid in self.templates:
   if self.cfg(f'/baseline-templates/{tid}')['templateStatus']=='ENABLED':self.disable(tid)
 def submit(self,name,model=None,wait=True):
  self.idle();marker='F155_'+name.replace('-','_').upper()
  case={'steps':[p.step()],'confidence':.79,'diverse':True};case.update(model or {})
  self.modelCases[marker]=case;(ROOT/'.local-test/f015-v155-cases.json').write_bytes(json.dumps(self.modelCases).encode('utf-8'))
  body={'taskGoal':marker+' synthetic navigation to F2_TEST_GATE','taskFamily':self.family,'sceneParams':{'targetLocation':'F2_TEST_GATE'}}
  response=p.raw(self.op,'/tasks',body);ids=sql(f"select id from {SC}.tasks where task_goal={literal(body['taskGoal'])} order by id desc limit 1")
  if not ids:raise RuntimeError('Task absent after submit: HTTP '+str(response['http']))
  tid=int(ids);self.tasks.append(tid);row={'name':name,'taskId':tid,'request':body,'response':response}
  self.ev['cases'].append(row);self.save()
  if wait:self.observe(row)
  return row
 def observe(self,row):
  tid=row['taskId'];row['observed']=self.wait(tid)
  row['persistedPlans']=sql(f'select row_to_json(p)::text from {SC}.plan_versions p where task_id={tid} order by version_no')
  row['persistedEvents']=sql(f'select row_to_json(e)::text from {SC}.task_events e where task_id={tid} order by id')
  row['exceptions']=sql(f'select row_to_json(e)::text from {SC}.task_exceptions e where task_id={tid} order by id')
  row['assignmentPlanIds']=sql(f'select plan_version_id from {SC}.task_step_assignments where task_id={tid} order by id').splitlines()
  row['deviceCommandRows']=sql(f'select row_to_json(c)::text from {SC}.device_commands c where task_id={tid} order by id');self.save();return row['observed']
 def judge(self,row,checks):
  row['checks']=checks;row['result']='P' if all(checks.values()) else 'F';self.save();print(row['name'],row['taskId'],row['result'],json.dumps(checks),flush=True)
 def baseline_checks(self,row,template_id,completed=True):
  o=row['observed'];base=[v for v in o['plans'] if v['source']=='BASELINE_TEMPLATE'];t=o['task'];b=base[-1] if base else {}
  return {'rightTemplate':b.get('baselineTemplateId')==template_id,'threeChecksPass':all(b.get(k)=='PASS' for k in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']),
   'frozen':bool(b.get('frozenAt')),'goalUnchanged':t['taskGoal']==row['request']['taskGoal'],
   'originalNeverAssigned':bool(base) and bool(row['assignmentPlanIds']) and all(int(x)==b['id'] for x in row['assignmentPlanIds']),
   'expectedStatus':t['status']==('COMPLETED' if completed else 'PENDING_MANUAL')}
 def run(self,name,fn):
  try:fn()
  except Exception as exc:
   self.ev.setdefault('probeDiagnostics',[]).append({'name':name,'at':now(),'error':str(exc),'traceback':traceback.format_exc()})
   self.save();print('PROBE_ERROR',name,str(exc),flush=True)
   # Continue independent cases; diagnose and repair these before final NT decisions.
 def second_robot(self):
  code='G155_F015_ROBOT_B';port=18133
  with socket.socket() as s:assert s.connect_ex(('127.0.0.1',port))!=0
  body={'deviceCode':code,'deviceName':'Synthetic F015 recovery robot B','deviceTypeCode':'SIMULATOR','isSimulator':True,
   'simulatedDeviceType':'MOBILE_ROBOT','areaCode':'F2_TEST','positionX':3,'positionY':4,'accessEndpoint':f'http://127.0.0.1:{port}',
   'accessCredentialRef':'gpt-f015-synthetic-robot-b','statusReportInterval':5}
  self.ev['robotBCreate']=self.cfg('/devices','POST',body)
  token=self.cfg(f'/devices/{code}/device-token/rotate','POST')['accessToken'];self.tokens[code]=token;self.ports[code]=port
  (ROOT/'.local-test/f015-v155-robot-b.dpapi').write_bytes(p.l.protect(json.dumps({'token':token}).encode(),False))
  env=p.l.env();env.update(SIMULATOR_PORT=str(port),SIMULATOR_DEVICE_CODE=code,SIMULATED_DEVICE_TYPE='MOBILE_ROBOT',SIMULATOR_DEVICE_TOKEN=token,
   SIMULATOR_X='3',SIMULATOR_Y='4',SIMULATOR_ZONE='F2_TEST',SIMULATOR_HEARTBEAT_INTERVAL_SECONDS='5',SIMULATOR_EXECUTION_DELAY_MS='3000')
  log=(ROOT/'.local-test/robot-b-v155.log').open('ab',buffering=0)
  proc=subprocess.Popen(['java','-Xmx96m','-XX:+UseSerialGC','-jar',str(ROOT.parent/'tip/.local-test/gpt-f007-v123-simulator-build/target/device-simulator-runtime.jar')],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  (ROOT/'.local-test/robot-b-v155-runtime.json').write_bytes(json.dumps({'pid':proc.pid,'port':port,'deviceCode':code}).encode())
  for _ in range(120):
   try:
    connected=self.cfg(f'/devices/{code}/connection-test','POST')
    if connected.get('result')=='PASSED':
     self.cfg(f'/devices/{code}/status','POST',{'status':'ACTIVE'})
     self.cfg(f'/devices/{code}/connection-test','POST')
    if self.agent(code)['onlineStatus']=='ONLINE':break
   except Exception:time.sleep(.5)
  else:raise RuntimeError('B connection failed')
  self.cfg(f'/devices/{code}/capabilities/CAP_NAVIGATION/test','POST');self.cfg(f'/devices/{code}/capabilities/CAP_NAVIGATION/status','POST',{'status':'ENABLED'})
  self.idle();self.ev['robotBAgent']=self.agent(code);self.save()
 def core_cases(self):
  self.create_definition();base=self.create('base-one');self.trial(base);self.uiTemplateId=base['id'];self.save()
  for name,model in [('high-valid',{}),('malformed-plan',{'planMode':'MALFORMED'}),('planning-unavailable',{'planHttpStatus':503}),('understanding-unavailable',{'goalHttpStatus':503})]:
   def body(name=name,model=model):
    row=self.submit(name,model);self.judge(row,self.baseline_checks(row,base['id']))
    if name=='high-valid':self.uiTaskId=row['taskId'];self.save()
   self.run(name,body)
  def cap_fail():
   self.cfg('/devices/G126_ROBOT/capabilities/CAP_NAVIGATION/status','POST',{'status':'DISABLED'})
   try:
    row=self.submit('capability-hard-fail');o=row['observed'];b=o['plans'][-1]
    self.judge(row,{'capabilityFails':b['capabilityCheckResult']=='FAIL','notFrozen':not b['frozenAt'],'pendingManual':o['task']['status']=='PENDING_MANUAL','zeroCommands':not o['commands']})
   finally:self.cfg('/devices/G126_ROBOT/capabilities/CAP_NAVIGATION/test','POST');self.cfg('/devices/G126_ROBOT/capabilities/CAP_NAVIGATION/status','POST',{'status':'ENABLED'})
  self.run('capability-hard-fail',cap_fail)
  def constraint_fail():
   original={k:v for k,v in self.definitionBody.items() if k!='taskName'}
   changed=copy.deepcopy(original);changed['completionCondition']='routeGenerated=false'
   self.cfg(f'/task-definitions/{self.definitionId}','PUT',changed)
   try:
    step=p.step();step['completionCondition']='routeGenerated=false'
    row=self.submit('constraint-hard-fail',{'goalCompletion':'routeGenerated=false','steps':[step]});o=row['observed'];b=o['plans'][-1]
    self.judge(row,{'baselineSelected':b['source']=='BASELINE_TEMPLATE','constraintFails':b['constraintCheckResult']=='FAIL','notFrozen':not b['frozenAt'],'pendingManual':o['task']['status']=='PENDING_MANUAL','zeroCommands':not o['commands']})
   finally:self.cfg(f'/task-definitions/{self.definitionId}','PUT',original)
  self.run('constraint-hard-fail',constraint_fail)
  self.disable(base['id'])
  for name in ['disabled-template','no-template']:
   def body(name=name):
    row=self.submit(name,{'taskNote':name});o=row['observed']
    self.judge(row,{'pendingManual':o['task']['status']=='PENDING_MANUAL','noBaselineVersion':all(v['source']!='BASELINE_TEMPLATE' for v in o['plans']),'zeroCommands':not o['commands'],'noMatchReason':any(e['reasonCode']=='ERR_NO_BASELINE_TEMPLATE' for e in o['events'])})
   self.run(name,body)
  # Pending validation page gets a newly qualified template, then actual UI chooses it.
  def manual():
   bad=p.step();bad.pop('precondition');row=self.submit('manual-ui-switch',{'steps':[bad]});row['beforeManual']=copy.deepcopy(row['observed'])
   t=self.create('manual-one');self.trial(t)
   process=subprocess.run(['node',str(ROOT/'acceptance/stage3/retest-f015-v155-ui.cjs'),'manual',str(row['taskId'])],cwd=ROOT,capture_output=True,encoding='utf-8',timeout=90)
   row['browserExit']=process.returncode;row['browserOutput']=process.stdout;row['browserError']=process.stderr;self.observe(row)
   checks=self.baseline_checks(row,t['id']);checks['browserClicked']=process.returncode==0;checks['initialHardFailNotFrozen']=not row['beforeManual']['plans'][0]['frozenAt'];self.judge(row,checks);self.disable(t['id'])
  self.run('manual-ui-switch',manual)
 def sorting_cases(self):
  self.disable_all();short=self.create('sort-short',1);self.trial(short);long=self.create('sort-long',2);self.trial(long)
  row=self.submit('fewer-steps',{'planMode':'MALFORMED'});self.judge(row,self.baseline_checks(row,short['id']));self.disable(short['id'])
  prefix=self.family[:-2]
  assert sql(f'select count(*) from {SC}.task_definitions where definition_code={literal(prefix)}')=='0'
  q=f"insert into {SC}.task_definitions(definition_code,task_name,goal_template,scene_params,available_capability_types,constraint_description,completion_condition,is_preset,definition_status,created_at,updated_at,updated_by) select {literal(prefix)},'G155 synthetic prefix-family fixture',goal_template,scene_params,available_capability_types,constraint_description,completion_condition,false,'ENABLED',now(),now(),'GPT_FIXTURE' from {SC}.task_definitions where id={self.definitionId} returning id"
  parent_id=int(sql(q).splitlines()[0]);self.definitions.append(parent_id);self.ev['prefixDefinitionFixture']={'id':parent_id,'code':prefix,'method':'Explicit GPT-only synthetic definition insert because public API generates exact family codes; template/trial/publication still via API.'};self.save()
  parent=self.create('sort-prefix',1,prefix);self.trial(parent)
  row=self.submit('exact-family',{'planMode':'MALFORMED'});self.judge(row,self.baseline_checks(row,long['id']));self.disable(long['id']);self.disable(parent['id'])
  a=self.create('sort-recent-A');self.trial(a,False);b=self.create('sort-recent-B');br=self.trial(b,False)
  self.cfg(f"/baseline-templates/{b['id']}/enable",'POST');self.cfg(f"/baseline-templates/{a['id']}/enable",'POST')
  row=self.submit('recent-trial-reversed-enable');checks=self.baseline_checks(row,b['id'])
  expected=next(e['occurredAt'] for e in br['observed']['events'] if e['eventType']=='DRY_RUN_SUCCEEDED')
  detail=next(e['detailSummary'] for e in row['observed']['events'] if e['eventType']=='BASELINE_DOWNGRADED' and '选择依据' in e['detailSummary']);match=re.search(r'最近试运行通过时间([^优]+)优先',detail)
  row['expectedTrialTime']=expected;row['selectionTime']=match.group(1) if match else None;checks['exactTrialTime']=bool(match) and datetime.fromisoformat(match.group(1))==datetime.fromisoformat(expected);self.judge(row,checks);self.disable(a['id']);self.disable(b['id'])
 def five_and_structure(self):
  self.disable_all();t=self.create('upper-five',5);self.trial(t)
  row=self.submit('valid-five-steps',{'planMode':'MALFORMED'});checks=self.baseline_checks(row,t['id']);checks['fiveExecuted']=len(row['observed']['assignments'])==5;self.judge(row,checks)
  original=self.cfg(f"/baseline-templates/{t['id']}");bad=copy.deepcopy(original['steps']);bad.append(copy.deepcopy(bad[-1]));bad[-1]['stepSeq']=6
  self.ev['structureStorageFault']={'templateId':t['id'],'before':original,'fault':'Six persisted steps after genuine five-step trial/publication, GPT-owned template only; restore exact steps in finally.'};self.save()
  try:
   sql(f"update {SC}.baseline_templates set steps={literal(json.dumps(bad))}::json where id={t['id']}")
   row=self.submit('structure-hard-fail-six');o=row['observed'];base=o['plans'][-1]
   self.judge(row,{'baselineSelected':base['source']=='BASELINE_TEMPLATE','structureFails':base['structureCheckResult']=='FAIL','notFrozen':not base['frozenAt'],'pendingManual':o['task']['status']=='PENDING_MANUAL','zeroCommands':not o['commands']})
  finally:
   sql(f"update {SC}.baseline_templates set steps={literal(json.dumps(original['steps']))}::json where id={t['id']}");self.ev['structureStorageFault']['restored']=True;self.disable(t['id']);self.save()
 def recovery_and_frozen(self):
  self.disable_all();self.second_robot();t=self.create('recovery-frozen');self.trial(t)
  ordered=sorted(self.ports,key=lambda c:self.agent(c)['agentId']);first,second=ordered
  self.ev['recoveryScenarioOrder']={'first':first,'second':second,'orderReason':'Product candidate tie-break uses agent code; both same zero distance/no targetX/Y and IDLE.'};self.save()
  self.scenario({first:'FAILED',second:'SUCCESS'})
  row=self.submit('multi-candidate-recovered',{'planMode':'MALFORMED'});o=row['observed'];checks=self.baseline_checks(row,t['id']);checks.update({'firstFailureSeen':any(e['eventType']=='STEP_RETRY' or 'SIMULATED_DEVICE_ERROR' in str(e) for e in o['events']),'secondExecuted':any(a.get('agentId')==self.agent(second)['agentId'] for a in o['assignments']) or self.agent(second)['agentId'] in row['persistedEvents'],'noReplan':not o['task']['replanUsed'] and not any(e['eventType']=='REPLANNING_TRIGGERED' for e in o['events'])});self.judge(row,checks)
  self.scenario('FAILED');row=self.submit('multi-candidate-exhausted',{'planMode':'MALFORMED'});o=row['observed']
  self.judge(row,{'pendingManual':o['task']['status']=='PENDING_MANUAL','onlyBaselineV1':len(o['plans'])==1 and o['plans'][0]['source']=='BASELINE_TEMPLATE','noReplan':not o['task']['replanUsed'] and not any(e['eventType']=='REPLANNING_TRIGGERED' for e in o['events']),'manualStateEvent':any(e['eventType']=='TASK_PENDING_MANUAL' for e in o['events']),'bothFailed':all(self.agent(c)['agentId'] in row['persistedEvents'] for c in ordered),'noFalseRecovered':not any(e['eventType']=='EXCEPTION_RECOVERED' for e in o['events'])})
  # A failed case stays in the evidence; continue to immutable-version and neighbor checks.
  self.scenario('SUCCESS');self.idle();row=self.submit('frozen-live-edit',wait=False);tid=row['taskId']
  before=p.observe(self.op,tid);row['beforeEdit']=before;template=self.cfg(f"/baseline-templates/{t['id']}");changed=copy.deepcopy(template['steps']);changed[0]['completionCondition']='routeGenerated=false'
  row['templateAfterEdit']=self.cfg(f"/baseline-templates/{t['id']}",'PUT',{'inputParams':template['inputParams'],'steps':changed});self.observe(row);o=row['observed']
  self.judge(row,{'wasExecuting':before['task']['status']=='EXECUTING','newTemplateVersion':row['templateAfterEdit']['templateVersion']!=template['templateVersion'],'newTemplateDraft':row['templateAfterEdit']['templateStatus']=='DRAFT','frozenPlanUnchanged':o['plans']==before['plans'],'completedOriginalCondition':o['task']['status']=='COMPLETED','keptFrozenVersion':o['plans'][-1]['ruleSetVersion']==template['templateVersion']})
  self.scenario('FAILED');row=self.submit('autonomous-replan-neighbor',{'confidence':1.0,'diverse':False});o=row['observed']
  self.judge(row,{'autonomousInitial':o['plans'][0]['source']=='AUTONOMOUS','replanUsed':o['task']['replanUsed'],'oneReplanTriggered':sum(e['eventType']=='REPLANNING_TRIGGERED' for e in o['events'])==1,'pendingManualAfterSecondFailure':o['task']['status']=='PENDING_MANUAL'})
  self.scenario('SUCCESS')
 def cleanup(self):
  self.scenario('SUCCESS');self.ev['cleanup']={'tasks':[]}
  for tid in self.tasks:
   t=self.op(f'/tasks/{tid}')
   if t['status'] not in ['COMPLETED','FAILED','MANUAL_TERMINATED']:
    self.ev['cleanup']['tasks'].append({'taskId':tid,'response':p.raw(self.op,f'/tasks/{tid}/terminate',{'reason':'F015 V155 complete round cleanup; preserve all evidence','confirmed':True})})
  for tid in self.templates:
   if self.cfg(f'/baseline-templates/{tid}')['templateStatus']!='DISABLED':self.disable(tid)
  for did in self.definitions:self.cfg(f'/task-definitions/{did}/disable','POST')
  if 'G155_F015_ROBOT_B' in self.ports:
   self.cfg('/devices/G155_F015_ROBOT_B/capabilities/CAP_NAVIGATION/status','POST',{'status':'DISABLED'});self.cfg('/devices/G155_F015_ROBOT_B/status','POST',{'status':'INACTIVE'})
  for rule in self.ev['rulesBefore']:
   self.cfg('/risk-rules/'+rule['ruleCode']+'/update','POST',{'enabled':rule['enabled']})
  self.ev['cleanup']['activeAssignments']=sql(f"select count(*) from {SC}.task_step_assignments where task_id in ({','.join(map(str,self.tasks)) or '0'}) and step_status in ('PENDING_ASSIGNMENT','EXECUTING')")
  self.ev['cleanup']['agentsAllocated']=sql(f'select count(*) from {SC}.device_agents where current_task_id is not null')
  self.ev['finishedAt']=now();self.save()

def main():
 q=Probe()
 try:
  q.run('core-batch',q.core_cases)
  q.run('sorting-batch',q.sorting_cases)
  q.run('five-and-structure-batch',q.five_and_structure)
  q.run('recovery-and-frozen-batch',q.recovery_and_frozen)
  q.run('readonly-ui',lambda:subprocess.run(['node',str(ROOT/'acceptance/stage3/retest-f015-v155-ui.cjs'),'details'],cwd=ROOT,check=True,timeout=180))
 finally:q.cleanup()

if __name__=='__main__':main()
