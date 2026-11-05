"""Independent F016 HTTP/DB probe. Own schema, model and synthetic adapter only.

Run with production JAR18129 and controlled model18117. The adapters on
18132..18134 deliberately defer callbacks so each acceptance boundary is observable.
No real hardware coverage is claimed. Local credentials stay in DPAPI/memory.
"""
import concurrent.futures, copy, importlib.util, json, socket, threading, time, traceback, urllib.request, urllib.error
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('prior',ROOT/'acceptance/stage3/probe-f015-v154.py')
prior=importlib.util.module_from_spec(s);s.loader.exec_module(prior)
p=prior.p;l=p.l;sql=prior.sql;SC=prior.SC
SHA='4f0b4d8e0ab2a2f0e4027d3ee21b20fe487dcadc'
OUT=ROOT/'acceptance/stage3/evidence/SRS_F016-V1.158-http-20261105.json'
def now():return datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
def lit(x):return "'"+str(x).replace("'","''")+"'"
def rows(q):return [json.loads(x) for x in sql(q).splitlines() if x]

class Device:
 def __init__(self,code,port):
  self.code=code;self.port=port;self.token=None;self.agent=None;self.messages=[];self.state=dict(onlineStatus='ONLINE',workStatus='IDLE',location={'x':0,'y':0,'zone':'F2_TEST'},businessStatus={'capabilityMatch':1,'workloadScore':0});self.stop=False
  d=self
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def reply(self,body,status=200):
    data=json.dumps(body).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
   def do_GET(self):
    nonce=parse_qs(urlparse(self.path).query).get('nonce',[''])[0]
    self.reply(dict(protocolVersion='1.0',nonce=nonce,deviceCode=d.code,deviceTypeCode='SIMULATOR',simulatedDeviceType='MOBILE_ROBOT',onlineStatus='ONLINE',workStatus='IDLE',location=d.state['location'],capabilities=['CAP_NAVIGATION'],reportedAt=now()))
   def do_POST(self):
    raw=b''
    if self.headers.get('Transfer-Encoding','').lower()=='chunked':
     while True:
      n=int(self.rfile.readline().strip().split(b';')[0],16)
      if not n:
       while self.rfile.readline().strip():pass
       break
      raw+=self.rfile.read(n);self.rfile.read(2)
    else:raw=self.rfile.read(int(self.headers.get('Content-Length','0')))
    body=json.loads(raw or '{}')
    if self.path.endswith('/binding'):d.agent=body['agentCode'];self.reply({})
    elif self.path.endswith('/capability-test'):self.reply({'commandId':body['commandId'],'result':'SUCCESS','outputParams':{'routeGenerated':True}})
    elif self.path.endswith('/commands'):
     d.messages.append({'at':now(),'message':body});self.reply({})
    else:self.reply({})
  self.server=ThreadingHTTPServer(('127.0.0.1',port),Handler);threading.Thread(target=self.server.serve_forever,daemon=True).start()
 def report(self,kind,payload):
  body={'reportType':kind,'reportedAt':now(),{'STATUS':'status','TASK_RESPONSE':'response','EXECUTION_FEEDBACK':'feedback'}[kind]:payload}
  req=urllib.request.Request(f'http://127.0.0.1:18129/device-api/v1/agents/{self.agent}/report',json.dumps(body).encode(),{'Content-Type':'application/json','Authorization':'Bearer '+self.token},method='POST')
  try:
   with urllib.request.urlopen(req,timeout=15) as r:return {'http':r.status,'body':json.load(r)}
  except urllib.error.HTTPError as e:return {'http':e.code,'body':json.load(e)}
 def heartbeat(self):return self.report('STATUS',copy.deepcopy(self.state))
 def configure(self,match=1,load=0,x=0,y=0,online='ONLINE',work='IDLE'):
  self.state.update(onlineStatus=online,workStatus=work,location={'x':x,'y':y,'zone':'F2_TEST'},businessStatus={'capabilityMatch':match,'workloadScore':load});return self.heartbeat()
 def messages_for(self,tid,typ=None):return [m for m in self.messages if m['message']['taskId']==tid and (typ is None or m['message']['commandType']==typ)]
 def loop(self):
  while not self.stop:
   if self.token and self.agent and not getattr(self,'paused',False):
    try:self.heartbeat()
    except Exception:pass
   time.sleep(4)

class Probe:
 def __init__(self):
  assert not OUT.exists(),'append with new path, do not overwrite'
  self.cfg=l.API('配置管理员');self.op=l.API('运行操作员');self.devices=[];self.tasks=[];self.templates=[];self.definitions=[];self.cases={}
  self.ev={'tag':'V1.158','productSha':SHA,'handoffSha':'845c8e674c9a8f3c8ff8bcb7540ab080f80cf898','executionBaseline':'V2.4','startedAt':now(),'timezone':'Asia/Shanghai','schema':SC,'redisDb':10,'cases':[],'health':l.request('http://127.0.0.1:18129/actuator/health'),'diagnostics':[]}
  self.save()
 def save(self):
  self.ev.update(taskIds=self.tasks,templateIds=self.templates,definitionIds=self.definitions)
  OUT.write_text(json.dumps(self.ev,ensure_ascii=False,indent=2),encoding='utf-8')
  (ROOT/'.local-test/f016-v158-state.json').write_text(json.dumps({'tasks':self.tasks,'cases':{r['name']:r.get('taskId') for r in self.ev['cases']},'devices':[{'code':d.code,'agent':d.agent,'port':d.port} for d in self.devices],'definitions':self.definitions,'templates':self.templates}),encoding='utf-8')
 def observe(self,tid):
  o=p.observe(self.op,tid)
  o['agentRows']=rows(f"select row_to_json(a)::text from {SC}.device_agents a join {SC}.devices d on d.id=a.device_id where d.device_code like 'G158_F016_%' order by a.id")
  for key,table in [('exceptions','task_exceptions'),('commandRows','device_commands')]:o[key]=rows(f'select row_to_json(x)::text from {SC}.{table} x where task_id={tid} order by id')
  o['transport']={d.code:copy.deepcopy(d.messages_for(o['task']['taskCode'])) for d in self.devices};return o
 def record(self,row,checks):row['checks']=checks;row['result']='P' if all(checks.values()) else 'F';self.save();print(row['name'],row.get('taskId'),row['result'],checks,flush=True)
 def run(self,name,fn):
  try:fn()
  except Exception as e:self.ev['diagnostics'].append({'name':name,'at':now(),'error':str(e),'traceback':traceback.format_exc()});self.save();print('DIAGNOSTIC',name,str(e),flush=True)
 def setup(self):
  for n in range(3):
   d=Device('G158_F016_'+chr(65+n),18132+n);self.devices.append(d)
   existing=sql(f"select count(*) from {SC}.devices where device_code={lit(d.code)}")
   if existing!='0':sql(f"update {SC}.device_agents set current_task_id=null,current_step_seq=null,work_status='IDLE' where device_id=(select id from {SC}.devices where device_code={lit(d.code)})")
   if existing=='0':self.cfg('/devices','POST',{'deviceCode':d.code,'deviceName':'Synthetic F016 '+str(n),'deviceTypeCode':'SIMULATOR','isSimulator':True,'simulatedDeviceType':'MOBILE_ROBOT','areaCode':'F2_TEST','positionX':0,'positionY':0,'accessEndpoint':f'http://127.0.0.1:{d.port}','statusReportInterval':5,'accessCredentialRef':'synthetic-f016'})
   d.token=self.cfg(f'/devices/{d.code}/device-token/rotate','POST')['accessToken']
   self.cfg(f'/devices/{d.code}/connection-test','POST')
   self.cfg(f'/devices/{d.code}/status','POST',{'status':'ACTIVE'})
   self.cfg(f'/devices/{d.code}/connection-test','POST')
   agents=self.cfg('/device-agents?page=1&size=100')['content'];d.agent=next(a['agentId'] for a in agents if a['deviceCode']==d.code)
   d.heartbeat();self.cfg(f'/devices/{d.code}/capabilities/CAP_NAVIGATION/test','POST');self.cfg(f'/devices/{d.code}/capabilities/CAP_NAVIGATION/status','POST',{'status':'ENABLED'})
   threading.Thread(target=d.loop,daemon=True).start();self.save()
  self.definitionBody={'taskName':'G158 F016 acceptance '+datetime.now().strftime('%H%M%S'),'goalTemplate':'Synthetic navigation','sceneParams':[{'name':'targetLocation','type':'String','required':True,'defaultValue':'F2_TEST_GATE'}],'availableCapabilityTypes':['CAP_NAVIGATION'],'constraintDescription':'Synthetic isolated navigation','completionCondition':'routeGenerated=true'}
  de=self.cfg('/task-definitions','POST',self.definitionBody);self.family=de['definitionCode'];self.definitions.append(de['id']);self.cfg(f"/task-definitions/{de['id']}/enable",'POST');self.save()
 def reset(self):
  for d in self.devices:
   sql(f"update {SC}.device_agents set agent_status='ENABLED',current_task_id=null,current_step_seq=null,work_status='IDLE' where agent_code={lit(d.agent)}")
   self.cfg(f'/devices/{d.code}/capabilities/CAP_NAVIGATION/status','POST',{'status':'ENABLED'});d.configure()
  self.devices[2].configure(online='OFFLINE')
 def submit(self,name,steps=None,high=False):
  marker='F158_'+name.upper().replace('-','_');self.cases[marker]={'steps':steps or [p.step(params={'targetLocation':'F2_TEST_GATE'})],'confidence':.79 if high else .99,'diverse':high}
  (ROOT/'.local-test/f016-v158-cases.json').write_text(json.dumps(self.cases),encoding='utf-8')
  body={'taskGoal':marker+' synthetic navigation to F2_TEST_GATE','taskFamily':self.family,'sceneParams':{'targetLocation':'F2_TEST_GATE'}}
  res=p.raw(self.op,'/tasks',body);tid=int(sql(f'select id from {SC}.tasks where task_goal={lit(body["taskGoal"])} order by id desc limit 1'))
  row={'name':name,'taskId':tid,'request':body,'response':res};self.tasks.append(tid);self.ev['cases'].append(row);self.save();return row
 def wait_message(self,row,typ='TASK_ACCEPT',device=None,timeout=15):
  code=self.op(f'/tasks/{row["taskId"]}')['taskCode'];end=time.monotonic()+timeout
  while time.monotonic()<end:
   found=[(d,m['message']) for d in ([device] if device else self.devices) for m in d.messages_for(code,typ)]
   if found:return found[-1]
   time.sleep(.05)
  raise RuntimeError('No '+typ+' for task '+str(row['taskId']))
 def response(self,d,msg,accepted=True):
  if accepted:d.state['workStatus']='BUSY'
  return d.report('TASK_RESPONSE',{'commandId':msg['commandId'],'accepted':accepted,**({} if accepted else {'rejectReason':'SYNTHETIC_CAPACITY_REJECTED'})})
 def complete(self,row,d=None):
  dev,msg=self.wait_message(row,'EXECUTE_CAPABILITY',d);ret=dev.report('EXECUTION_FEEDBACK',{'commandId':msg['commandId'],'attemptNo':msg['attemptNo'],'executionResult':'SUCCESS','outputParams':{'routeGenerated':True}});dev.state['workStatus']='IDLE';return ret
 def terminate(self,row):
  tid=row['taskId'];status=self.op(f'/tasks/{tid}')['status']
  if status not in ['COMPLETED','FAILED','MANUAL_TERMINATED']:row['terminateResponse']=p.raw(self.op,f'/tasks/{tid}/terminate',{'reason':'Synthetic F016 cleanup','confirmed':True})
  time.sleep(.15)
  for d in self.devices:
   d.state.update(onlineStatus='ONLINE',workStatus='IDLE')
   try:d.heartbeat()
   except Exception:pass
 def ranking(self,name,params,a,b):
  self.reset();self.devices[0].configure(**a);self.devices[1].configure(**b)
  st=p.step(params={k:v for k,v in params.items() if k not in ['targetX','targetY']});st.update({k:v for k,v in params.items() if k in ['targetX','targetY']});row=self.submit(name,[st]);d,msg=self.wait_message(row);row['beforeAcceptance']=self.observe(row['taskId']);row['acceptResponse']=self.response(d,msg);row['duringExecution']=self.observe(row['taskId']);self.complete(row,d);row['after']=self.observe(row['taskId'])
  expected=self.devices[1].agent;event=next(e for e in row['beforeAcceptance']['events'] if e['eventType']=='AGENT_ASSIGNMENT_REQUESTED')
  row['rankingEvent']=event
  self.record(row,{'selectedExpectedB':d.agent==expected,'onlyTaskAcceptBeforeResponse':all(c['command_type']=='TASK_ACCEPT' for c in row['beforeAcceptance']['commandRows']),'occupiedDuringExecution':any(a['agent_code']==d.agent and a['work_status']=='BUSY' and a['current_task_id']==row['taskId'] for a in row['duringExecution']['agentRows']),'metricsRecorded':all(x in event['detailSummary'] for x in ['匹配度','距离','负载']) if 'detailSummary' in event else False,'completed':row['after']['task']['status']=='COMPLETED'})
 def reject(self,name,all_reject=False):
  self.reset();self.devices[0].configure(match=1);self.devices[1].configure(match=.9)
  row=self.submit(name);d,msg=self.wait_message(row);row['first']=d.agent;row['rejectResponse']=self.response(d,msg,False);d2,msg2=self.wait_message(row,device=self.devices[1]);row['second']=d2.agent
  row['secondResponse']=self.response(d2,msg2,not all_reject)
  if not all_reject:self.complete(row,d2)
  time.sleep(.1);row['after']=self.observe(row['taskId'])
  o=row['after'];events=o['events'];cutoff=next((e['occurredAt'] for e in events if e['eventType']=='REPLANNING_TRIGGERED'),None);initialOffers=[c for c in o['commandRows'] if c['command_type']=='TASK_ACCEPT' and (cutoff is None or c['created_at']<cutoff)];self.record(row,{'orderedSwitch':row['first']==self.devices[0].agent and row['second']==self.devices[1].agent,'reasonPreserved':any('SYNTHETIC_CAPACITY_REJECTED' in json.dumps(e) for e in events),'rightTerminal':(o['task']['status']=='PENDING_MANUAL' or (o['task']['status']=='PENDING_ASSIGNMENT' and o['task']['replanUsed'] and sum(e['eventType']=='REPLANNING_TRIGGERED' for e in events)==1)) if all_reject else o['task']['status']=='COMPLETED','rightException':not all_reject or any(e['exception_type']=='ASSIGNMENT_FAILED' and e['recovery_action']=='全部候选设备均拒绝，恢复动作未执行' for e in o['exceptions']),'acceptsExactlyTwo':len(initialOffers)==2,'noBusinessWhenAllRejected':not all_reject or not any(c['command_type']=='EXECUTE_CAPABILITY' for c in o['commandRows'])})
 def eligibility(self,name,kind):
  self.reset();a,b,c=self.devices;a.configure(match=.9);b.configure(match=.8);c.configure(match=2)
  if kind=='offline':c.configure(match=2,online='OFFLINE')
  elif kind=='busy':c.configure(match=2,work='BUSY')
  elif kind=='disabled-agent':sql(f"update {SC}.device_agents set agent_status='DISABLED' where agent_code={lit(c.agent)}")
  elif kind=='disabled-capability':self.cfg(f'/devices/{c.code}/capabilities/CAP_NAVIGATION/status','POST',{'status':'DISABLED'})
  elif kind=='absent-capability':sql(f"update {SC}.device_capabilities set capability_type='CAP_ESCORT' where device_id=(select id from {SC}.devices where device_code={lit(c.code)}) and capability_code='CAP_NAVIGATION'")
  row=self.submit(name);d,msg=self.wait_message(row);row['before']=self.observe(row['taskId']);self.response(d,msg);self.complete(row,d);row['after']=self.observe(row['taskId']);self.record(row,{'excludedDecoy':d.agent==a.agent,'decoyNoMessages':not c.messages_for(row['after']['task']['taskCode']),'completed':row['after']['task']['status']=='COMPLETED'})
  if kind=='absent-capability':sql(f"update {SC}.device_capabilities set capability_type='CAP_NAVIGATION' where device_id=(select id from {SC}.devices where device_code={lit(c.code)}) and capability_code='CAP_NAVIGATION'")
 def concurrent(self):
  self.reset();self.devices[1].configure(online='OFFLINE');one=self.submit('concurrent-one');d,msg=self.wait_message(one);two=self.submit('concurrent-two');d2,msg2=self.wait_message(two);one['bothPending']=self.observe(one['taskId']);two['bothPending']=self.observe(two['taskId'])
  # Both independently pending offers are now acknowledged; transport does not enforce server ownership.
  one['acceptResponse']=self.response(d,msg);two['acceptResponse']=self.response(d2,msg2);time.sleep(.2)
  one['overlap']=self.observe(one['taskId']);two['overlap']=self.observe(two['taskId'])
  executionCount=sum(any(c['command_type']=='EXECUTE_CAPABILITY' for c in r['overlap']['commandRows']) for r in [one,two])
  for r in [one,two]:self.record(r,{'exactlyOneTaskExecutes':executionCount==1})
  self.terminate(one);self.terminate(two)
 def busy_control(self):
  self.reset();self.devices[1].configure(online='OFFLINE');one=self.submit('busy-holder');d,msg=self.wait_message(one);self.response(d,msg);one['during']=self.observe(one['taskId']);two=self.submit('busy-excluded');time.sleep(.1);two['after']=self.observe(two['taskId']);self.record(two,{'busyNotOffered':not two['after']['commandRows'],'notExecuting':two['after']['task']['status']=='PENDING_MANUAL'});self.complete(one,d);one['after']=self.observe(one['taskId']);self.record(one,{'completed':one['after']['task']['status']=='COMPLETED'})
 def no_candidate(self):
  self.reset();row=self.submit('no-candidate-after-first',[p.step(seq=1),p.step(seq=2)]);d,msg=self.wait_message(row);self.response(d,msg);self.wait_message(row,'EXECUTE_CAPABILITY',d)
  for dev in self.devices:self.cfg(f'/devices/{dev.code}/capabilities/CAP_NAVIGATION/status','POST',{'status':'DISABLED'})
  self.complete(row,d);row['after']=self.observe(row['taskId']);o=row['after'];self.record(row,{'capabilityGap':any(e['exception_type']=='CAPABILITY_GAP' for e in o['exceptions']),'rightReason':any(e.get('reasonCode')=='ERR_NO_CANDIDATE_AVAILABLE' for e in o['events']),'noStepTwoCommand':not any(c['step_seq']==2 for c in o['commandRows']),'pendingManual':o['task']['status']=='PENDING_MANUAL','noRetry':all(e['recovery_action']=='无可用候选设备，恢复动作未执行' for e in o['exceptions'])})
 def terminate_case(self,offline=False):
  self.reset();row=self.submit('terminate-offline' if offline else 'terminate-online');d,msg=self.wait_message(row);self.response(d,msg);row['before']=self.observe(row['taskId'])
  if offline:d.configure(online='OFFLINE',work='BUSY')
  row['terminateResponse']=p.raw(self.op,f'/tasks/{row["taskId"]}/terminate',{'reason':'Synthetic termination boundary','confirmed':True})
  row['immediate']=self.observe(row['taskId']);a=next(a for a in row['immediate']['agentRows'] if a['agent_code']==d.agent)
  d.configure(online='ONLINE',work='IDLE');time.sleep(.1);row['afterIdle']=self.observe(row['taskId']);b=next(a for a in row['afterIdle']['agentRows'] if a['agent_code']==d.agent)
  self.record(row,{'terminated':row['immediate']['task']['status']=='MANUAL_TERMINATED','immediateRelease':a['work_status']=='IDLE' and a['current_task_id'] is None and a['current_step_seq'] is None,'releaseOnOnlineIdle':b['current_task_id'] is None and b['current_step_seq'] is None and b['work_status']=='IDLE'})
 def freeze(self):
  self.reset();row=self.submit('freeze-future-occupied',[p.step(seq=1),p.step(seq=2)]);d,msg=self.wait_message(row);self.response(d,msg);self.wait_message(row,'EXECUTE_CAPABILITY',d)
  # Controlled future-step occupation exercises freezeRemainingSteps directly via the real exception path.
  b=self.devices[1];tid=row['taskId'];pid=self.op(f'/tasks/{tid}')['currentPlanVersionId'];aid=sql(f"select id from {SC}.device_agents where agent_code={lit(b.agent)}")
  sql(f"update {SC}.task_step_assignments set device_agent_id={aid} where task_id={tid} and plan_version_id={pid} and step_seq=2; update {SC}.device_agents set work_status='BUSY',current_task_id={tid},current_step_seq=2 where id={aid}")
  b.state['workStatus']='BUSY';row['fixtureBefore']=self.observe(tid);d.configure(online='OFFLINE',work='BUSY');row['after']=self.observe(tid);a=next(a for a in row['after']['agentRows'] if a['agent_code']==b.agent)
  self.record(row,{'futureFrozen':any(x['stepSeq']==2 and x['stepStatus']=='FROZEN' for x in row['after']['assignments']),'futureAgentReleased':a['work_status']=='IDLE' and a['current_task_id'] is None and a['current_step_seq'] is None,'noFutureBusiness':not any(c['step_seq']==2 and c['command_type']=='EXECUTE_CAPABILITY' for c in row['after']['commandRows'])});self.terminate(row)
 def cleanup(self):
  errors=[]
  for tid in self.tasks:
   try:self.terminate({'taskId':tid})
   except Exception as e:errors.append({'taskId':tid,'error':str(e)})
  for did in self.definitions:
   try:self.cfg(f'/task-definitions/{did}/disable','POST')
   except Exception as e:errors.append({'definitionId':did,'error':str(e)})
  for d in self.devices:
   d.stop=True
   try:self.cfg(f'/devices/{d.code}/status','POST',{'status':'INACTIVE'})
   except Exception as e:errors.append({'device':d.code,'error':str(e)})
   d.server.shutdown();d.server.server_close()
  self.ev['cleanup']={'at':now(),'errors':errors,'ownedAgentRows':rows(f"select row_to_json(a)::text from {SC}.device_agents a join {SC}.devices d on d.id=a.device_id where d.device_code like 'G158_F016_%'"),'activeAssignments':sql(f"select count(*) from {SC}.task_step_assignments where task_id in ({','.join(map(str,self.tasks)) or '0'}) and step_status in ('PENDING_ASSIGNMENT','EXECUTING')")};self.save()
 def main(self):
  self.setup()
  try:
   self.run('match',lambda:self.ranking('rank-match',{'targetLocation':'F2_TEST_GATE','targetX':0,'targetY':0},{'match':.8,'x':0,'load':0},{'match':.9,'x':10,'load':8}))
   self.run('distance',lambda:self.ranking('rank-distance',{'targetLocation':'F2_TEST_GATE','targetX':0,'targetY':0},{'x':3,'y':4},{'x':0,'y':0,'load':8}))
   self.run('load',lambda:self.ranking('rank-load',{'targetLocation':'F2_TEST_GATE','targetX':0,'targetY':0},{'load':9},{'load':1}))
   for kind in ['offline','busy','disabled-agent','disabled-capability','absent-capability']:self.run(kind,lambda kind=kind:self.eligibility('eligibility-'+kind,kind))
   self.run('reject-next',lambda:self.reject('reject-next'))
   self.run('all-reject',lambda:self.reject('all-reject',True))
   self.run('busy-control',self.busy_control);self.run('concurrent',self.concurrent);self.run('no-candidate',self.no_candidate)
   self.run('freeze',self.freeze);self.run('terminate-online',self.terminate_case);self.run('terminate-offline',lambda:self.terminate_case(True))
  finally:self.cleanup();self.ev['endedAt']=now();self.save()
if __name__=='__main__':raise SystemExit('Use probe-f016-v158-round.py for the V2.4+BL006 round; this file supplies fixtures only.')
