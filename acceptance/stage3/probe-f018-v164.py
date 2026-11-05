"""Independent F018 HTTP/DB probe. Own schema, model and synthetic adapter only.

Run with production JAR18129 and controlled model18117. The adapters on
18132..18134 deliberately defer callbacks so each acceptance boundary is observable.
No real hardware coverage is claimed. Local credentials stay in DPAPI/memory.
"""
import re, base64, concurrent.futures, copy, importlib.util, json, socket, threading, time, traceback, urllib.request, urllib.error, subprocess, os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('prior',ROOT/'acceptance/stage3/probe-f015-v154.py')
prior=importlib.util.module_from_spec(s);s.loader.exec_module(prior)
p=prior.p;l=p.l;sql=prior.sql;SC=prior.SC
# Windows psql -c re-encodes non-ASCII argv; feed UTF-8 SQL through stdin instead.
def sql(query):
 db=prior.p.base.d
 result=subprocess.run(db.common+['-d',db.shared,'-At'],input=query+';\n',env=dict(db.variables,PGCLIENTENCODING='UTF8'),encoding='utf-8',capture_output=True,check=True)
 return result.stdout.strip()
SHA='bf200f81c63688072549bb3215b72a74837fb977'
def output_path(name):
 label=os.environ.get('GPT_EVIDENCE_LABEL','')
 path=ROOT/'acceptance/stage3/evidence'/name
 return path.with_stem(path.stem+'-'+label) if label else path
OUT=output_path('SRS_F018-V1.164-http-20261105.json')
def now():return datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
def lit(x):return "'"+str(x).replace("'","''")+"'"
def rows(q):
 # ASCII base64 transport avoids Windows psql re-encoding non-ASCII cell text.
 return [json.loads(base64.b64decode(x)) for x in sql("select replace(encode(convert_to(row_to_json(gpt_row)::text,'UTF8'),'base64'),E'\\n','') from ("+re.sub(r'select row_to_json\((\w+)\)::text',r'select \1.*',q)+") gpt_row").splitlines() if x]

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
    self.reply(dict(protocolVersion='1.0',nonce=nonce,deviceCode=d.code,deviceTypeCode='SIMULATOR',simulatedDeviceType=getattr(d,'simtype','MOBILE_ROBOT'),onlineStatus='ONLINE',workStatus='IDLE',location=d.state['location'],capabilities=getattr(d,'healthcaps',['CAP_NAVIGATION']),reportedAt=now()))
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
    elif self.path.endswith('/capability-test'):self.reply({'commandId':body['commandId'],'result':'SUCCESS','outputParams':{'routeGenerated':True,'measureStatus':'SUCCESS','isOversize':True,'length':80.0,'width':55.0,'height':35.0,'weight':35.0,'baggageInfo':'synthetic baggage','reportStatus':'SUCCESS','alertId':'SYNTHETIC-ALERT','reportTime':now(),'arrivalStatus':'ARRIVED','actualDistance':10,'actualDuration':10,'notificationStatus':'SUCCESS','actualRepeatCount':1,'displayStatus':'SUCCESS','estimatedDistance':10,'estimatedDuration':10,'waypointCount':2}})
    elif self.path.endswith('/commands'):
     d.messages.append({'at':now(),'message':body});key=(body.get('taskId'),body.get('stepSeq'),body.get('attemptNo'));failed=body.get('commandType')=='EXECUTE_CAPABILITY' and key in getattr(d,'delivery_failures',set());self.reply({'received':True,'message':'已收到'} if not failed else {'error':'SYNTHETIC_DELIVERY_FAILURE'},500 if failed else 200)
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
  self.ev={'tag':'V1.164','productSha':SHA,'handoffSha':'0ebe23c040875d79d49a1ddf43352509b99c7849','executionBaseline':'V2.4','startedAt':now(),'timezone':'Asia/Shanghai','schema':SC,'redisDb':10,'cases':[],'health':l.request('http://127.0.0.1:18129/actuator/health'),'diagnostics':[]}
  self.save()
 def save(self):
  self.ev.update(taskIds=self.tasks,templateIds=self.templates,definitionIds=self.definitions)
  OUT.write_text(json.dumps(self.ev,ensure_ascii=False,indent=2),encoding='utf-8')
  (ROOT/'.local-test/f018-v164-state.json').write_text(json.dumps({'tasks':self.tasks,'cases':{r['name']:r.get('taskId') for r in self.ev['cases']},'devices':[{'code':d.code,'agent':d.agent,'port':d.port} for d in self.devices],'definitions':self.definitions,'templates':self.templates}),encoding='utf-8')
 def observe(self,tid):
  o=p.observe(self.op,tid)
  o['agentRows']=rows(f"select row_to_json(a)::text from {SC}.device_agents a join {SC}.devices d on d.id=a.device_id where d.device_code like 'G160_F016_%' order by a.id")
  for key,table in [('exceptions','task_exceptions'),('commandRows','device_commands')]:o[key]=rows(f'select row_to_json(x)::text from {SC}.{table} x where task_id={tid} order by id')
  o['transport']={d.code:copy.deepcopy(d.messages_for(o['task']['taskCode'])) for d in self.devices};return o
 def record(self,row,checks):row['checks']=checks;row['result']='P' if all(checks.values()) else 'F';self.save();print(row['name'],row.get('taskId'),row['result'],checks,flush=True)
 def run(self,name,fn):
  try:fn()
  except Exception as e:self.ev['diagnostics'].append({'name':name,'at':now(),'error':str(e),'traceback':traceback.format_exc()});self.save();print('DIAGNOSTIC',name,str(e),flush=True)
 def setup(self):
  for n in range(3):
   d=Device('G160_F016_'+chr(65+n),18132+n);self.devices.append(d)
   existing=sql(f"select count(*) from {SC}.devices where device_code={lit(d.code)}")
   if existing!='0':
    assert sql(f"select count(*) from {SC}.device_agents where agent_code in (select agent_code from {SC}.device_agents a join {SC}.devices d on d.id=a.device_id where d.device_code={lit(d.code)}) and current_task_id is not null")=='0','Owned device is occupied'
    sql(f"update {SC}.device_agents set current_task_id=null,current_step_seq=null,work_status='IDLE' where device_id=(select id from {SC}.devices where device_code={lit(d.code)})")
   if existing=='0':self.cfg('/devices','POST',{'deviceCode':d.code,'deviceName':'Synthetic F018 '+str(n),'deviceTypeCode':'SIMULATOR','isSimulator':True,'simulatedDeviceType':'MOBILE_ROBOT','areaCode':'F2_TEST','positionX':0,'positionY':0,'accessEndpoint':f'http://127.0.0.1:{d.port}','statusReportInterval':5,'accessCredentialRef':'synthetic-f016'})
   d.token=self.cfg(f'/devices/{d.code}/device-token/rotate','POST')['accessToken']
   self.cfg(f'/devices/{d.code}/connection-test','POST')
   self.cfg(f'/devices/{d.code}/status','POST',{'status':'ACTIVE'})
   self.cfg(f'/devices/{d.code}/connection-test','POST')
   agents=self.cfg('/device-agents?page=1&size=100')['content'];d.agent=next(a['agentId'] for a in agents if a['deviceCode']==d.code)
   d.heartbeat();self.cfg(f'/devices/{d.code}/capabilities/CAP_NAVIGATION/test','POST');self.cfg(f'/devices/{d.code}/capabilities/CAP_NAVIGATION/status','POST',{'status':'ENABLED'})
   threading.Thread(target=d.loop,daemon=True).start();self.save()
  self.definitionBody={'taskName':'G164 F018 acceptance '+datetime.now().strftime('%H%M%S'),'goalTemplate':'Synthetic navigation','sceneParams':[{'name':'targetLocation','type':'String','required':True,'defaultValue':'F2_TEST_GATE'}],'availableCapabilityTypes':['CAP_NAVIGATION'],'constraintDescription':'Synthetic isolated navigation','completionCondition':'routeGenerated=true'}
  de=self.cfg('/task-definitions','POST',self.definitionBody);self.family=de['definitionCode'];self.definitions.append(de['id']);self.cfg(f"/task-definitions/{de['id']}/enable",'POST');self.save()
 def reset(self):
  for d in self.devices:
   sql(f"update {SC}.device_agents set agent_status='ENABLED',current_task_id=null,current_step_seq=null,work_status='IDLE' where agent_code={lit(d.agent)}")
   self.cfg(f'/devices/{d.code}/capabilities/CAP_NAVIGATION/status','POST',{'status':'ENABLED'});d.configure()
  self.devices[2].configure(online='OFFLINE')
 def submit(self,name,steps=None,high=False):
  marker='F164_'+name.upper().replace('-','_');self.cases[marker]={'steps':steps or [p.step(params={'targetLocation':'F2_TEST_GATE'})],'goalCompletion':(steps[0].get('completionCondition','routeGenerated=true') if steps else 'routeGenerated=true'),'confidence':.79 if high else .99,'diverse':high}
  (ROOT/'.local-test/f018-v164-cases.json').write_text(json.dumps(self.cases),encoding='utf-8')
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
  if status not in ['COMPLETED','FAILED','MANUAL_TERMINATED']:row['terminateResponse']=p.raw(self.op,f'/tasks/{tid}/terminate',{'reason':'Synthetic F018 cleanup','confirmed':True})
  time.sleep(.15)
  for d in self.devices:
   d.state.update(onlineStatus='ONLINE',workStatus='IDLE')
   try:d.heartbeat()
   except Exception:pass
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
  self.ev['cleanup']={'at':now(),'errors':errors,'ownedAgentRows':rows(f"select row_to_json(a)::text from {SC}.device_agents a join {SC}.devices d on d.id=a.device_id where d.device_code like 'G160_F016_%'"),'activeAssignments':sql(f"select count(*) from {SC}.task_step_assignments where task_id in ({','.join(map(str,self.tasks)) or '0'}) and step_status in ('PENDING_ASSIGNMENT','EXECUTING')")};self.save()
