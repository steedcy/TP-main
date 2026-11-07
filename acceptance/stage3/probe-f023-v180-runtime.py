"""GPT-owned V1.180 runtime: production JAR, production dist, controlled model.
No product edits. Proxy fault modes are renderer contract tests, not device E2E.
Commands: start | serve | state | offline | recover | task | complete | cleanup.
The serve process owns protocol adapters; other commands call its localhost control.
"""
import importlib.util,json,time,threading,subprocess,socket,sys,copy,mimetypes,urllib.request,urllib.error
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
R=Path(__file__).resolve().parents[2];L=R/'.local-test';E=R/'acceptance/stage3/evidence'
SHA='1c612d55c9e228b2bdbea1375101648060c9dfc7';PREFIX='SRS_F023-V1.180-'
def mod(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
b=mod('b',Path(__file__).with_name('probe-f022-v179-base.py'))
SC=b.SC;sql=b.sql;rows=b.rows;lit=b.lit;now=b.now
def save(name,value):
 path=E/(PREFIX+name+'-20261108.json');path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8');return path
def raw(api,path,body=None,method='GET'):
 req=urllib.request.Request(b.l.BASE+path,json.dumps(body).encode() if body is not None else None,{'Content-Type':'application/json','Authorization':'Bearer '+api.token},method=method)
 try:
  with urllib.request.urlopen(req,timeout=90) as r:return {'http':r.status,'body':json.load(r)}
 except urllib.error.HTTPError as ex:return {'http':ex.code,'body':json.load(ex)}
def start():
 db=b.prior.p.base.d
 for port in [18129,18117,15179,18132,18133,18134,18135]:
  with socket.socket() as s:assert s.connect_ex(('127.0.0.1',port))!=0,f'occupied {port}'
 env=db.variables.copy();env.update(SPRING_DATASOURCE_URL=f"jdbc:postgresql://{env.get('DB_HOST','localhost')}:{env.get('DB_PORT','5432')}/{db.shared}?currentSchema={SC}",SPRING_FLYWAY_SCHEMAS=SC,SERVER_ADDRESS='127.0.0.1',SERVER_PORT='18129',SPRING_DATA_REDIS_DATABASE='10',PLANNING_MODEL_PROVIDER='external',PLANNING_MODEL_ENDPOINT='http://127.0.0.1:18117',APP_DEVICE_ADAPTER_PUBLIC_BASE_URL='http://127.0.0.1:18129',APP_DEVICE_PRESET_AREAS='F2_TEST,F2_ZONE_A,F2_ZONE_B',APP_CONTEXT_FAULT_INJECTION_FAILED_AGENT_CODES='')
 log=(L/'f023-v180-backend.log').open('ab',buffering=0)
 p=subprocess.Popen(['java','-Xms32m','-Xmx256m','-XX:TieredStopAtLevel=1','-XX:+UseSerialGC','-jar',str(R/'backend/target/airport-ai-app-1.0.0.jar')],cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 (L/'f023-v180-runtime.json').write_text(json.dumps({'backendPid':p.pid,'schema':SC,'redisDb':10,'tag':'V1.180','productSha':SHA}))
 for _ in range(120):
  if p.poll() is not None:raise RuntimeError('JAR exited; inspect local log')
  try:
   if b.l.request('http://127.0.0.1:18129/actuator/health',timeout=2)['status']=='UP':print('JAR healthy',p.pid);return
  except Exception:pass
  time.sleep(1)
 raise TimeoutError('JAR health')

class Fixture:
 def __init__(self):
  self.cfg=b.l.API('配置管理员');self.op=b.l.API('运行操作员');self.devices=[];self.original=[];self.task=None;self.definition=None;self.mode='live';self.net=[]
  self.ev={'tag':'V1.180','productSha':SHA,'handoffSha':'605de7e4fef9343c74d50d498f293280734320e4','at':now(),'schema':SC,'redisDb':10,'cases':[],'diagnostics':[]}
 def record(self,name,values,checks=None):
  x={'name':name,'at':now(),**values}
  if checks is not None:x.update(checks=checks,result='P' if all(checks.values()) else 'F')
  self.ev['cases'].append(x);save('http-sql-protocol',self.ev);return x
 def snapshot(self):return self.op('/situation/snapshot')
 def setup(self):
  for i,(typ,x,y) in enumerate([('MOBILE_ROBOT',450,260),('SMART_DISPLAY',450,260),('FLIGHT_DELAY_BOARD',850,360)]):
   d=b.Device(['G180_F023_0','G145_F013_DISPLAY','G175_F022_FLIGHT'][i],18132+i);d.simtype=typ;d.healthcaps=['CAP_NAVIGATION'] if i==0 else (['CAP_INFO_DISPLAY'] if i==1 else ['CAP_FLIGHT_UPDATE'])
   self.devices.append(d)
   body={'deviceCode':d.code,'deviceName':'G180 '+typ,'deviceTypeCode':'SIMULATOR','isSimulator':True,'simulatedDeviceType':typ,'areaCode':'F2_TEST','positionX':x,'positionY':y,'accessEndpoint':f'http://127.0.0.1:{d.port}','statusReportInterval':5,'accessCredentialRef':'synthetic-f023'}
   if sql(f"select count(*) from {SC}.devices where device_code={lit(d.code)}")=='0':self.cfg('/devices','POST',body)
   old=self.cfg(f'/devices/{d.code}');restore={k:old.get(k) for k in ['deviceName','areaCode','positionX','positionY','accessEndpoint','statusReportInterval','remark']};self.original.append({'code':d.code,'body':restore,'capabilities':rows(f"select id,capability_status from {SC}.device_capabilities where device_id=(select id from {SC}.devices where device_code={lit(d.code)})")});self.ev['originalConfiguration']=self.original;save('http-sql-protocol',self.ev)
   self.cfg(f'/devices/{d.code}','PUT',{k:v for k,v in body.items() if k not in ['deviceCode','deviceTypeCode','isSimulator','simulatedDeviceType','accessCredentialRef']})
   d.token=self.cfg(f'/devices/{d.code}/device-token/rotate','POST')['accessToken'];self.cfg(f'/devices/{d.code}/connection-test','POST');self.cfg(f'/devices/{d.code}/status','POST',{'status':'ACTIVE'});self.cfg(f'/devices/{d.code}/connection-test','POST')
   d.agent=next(a['agentId'] for a in self.cfg('/device-agents?page=1&size=100')['content'] if a['deviceCode']==d.code)
   d.configure(x=x,y=y);cap=d.healthcaps[0];self.cfg(f'/devices/{d.code}/capabilities/{cap}/test','POST');self.cfg(f'/devices/{d.code}/capabilities/{cap}/status','POST',{'status':'ENABLED'});threading.Thread(target=d.loop,daemon=True).start()
  snap=self.snapshot();self.record('initial-live-snapshot',{'snapshot':snap,'agentRows':self.agentrows(),'health':b.l.request('http://127.0.0.1:18129/actuator/health')},{'threeOwnedEnabled':len([a for a in snap['agents'] if a['deviceCode'] in [d.code for d in self.devices]])==3,'allOwnedOnline':all(a['onlineStatus']=='ONLINE' and a.get('offline') is None for a in snap['agents'] if a['deviceCode'] in [d.code for d in self.devices]),'refresh5':snap['refreshIntervalSeconds']==5})
 def agentrows(self):return rows(f"select a.*,d.device_code,d.position_x,d.position_y from {SC}.device_agents a join {SC}.devices d on d.id=a.device_id where d.device_code in ('G180_F023_0','G145_F013_DISPLAY','G175_F022_FLIGHT') order by a.id")
 def state(self):return {'at':now(),'mode':self.mode,'taskId':self.task,'snapshot':self.snapshot(),'agentRows':self.agentrows()}
 def offline(self,index=1):
  d=self.devices[index];d.paused=True;before=self.snapshot();start=time.monotonic()
  while time.monotonic()-start<50:
   snap=self.snapshot();a=next(a for a in snap['agents'] if a['deviceCode']==d.code)
   if a['onlineStatus']=='OFFLINE':break
   time.sleep(1)
  events=rows(f"select * from {SC}.device_events where device_agent_id=(select id from {SC}.device_agents where agent_code={lit(d.agent)}) order by id")
  expected=next(a for a in before['agents'] if a['deviceCode']==d.code)
  return self.record('heartbeat-timeout-'+str(index),{'elapsedSeconds':time.monotonic()-start,'before':before,'after':snap,'events':events,'agentRows':self.agentrows()},{'offline':a['onlineStatus']=='OFFLINE','lastPositionKept':a['location']==expected['location'],'lastReportKept':a['lastReportedAt']==expected['lastReportedAt'],'reason':a['offline'] is not None and a['offline']['reasonCode']=='ERR_HEARTBEAT_TIMEOUT','offlineTime':bool((a['offline'] or {}).get('offlineAt')),'taskImpact':(a['offline'] or {}).get('affectsTask')==(a['currentTaskId'] is not None)})
 def recover(self,index=1):
  d=self.devices[index];d.paused=False;ret=d.heartbeat();snap=self.snapshot();a=next(a for a in snap['agents'] if a['deviceCode']==d.code)
  return self.record('heartbeat-recovery-'+str(index),{'report':ret,'snapshot':snap,'agentRows':self.agentrows()},{'online':a['onlineStatus']=='ONLINE','offlineNull':a['offline'] is None,'report200':ret['http']==200})
 def create_task(self):
  if self.definition is None:
   self.definition=self.cfg('/task-definitions','POST',{'taskName':'G180 F023 task link','goalTemplate':'Synthetic navigation','sceneParams':[{'name':'targetLocation','type':'String','required':True}],'availableCapabilityTypes':['CAP_NAVIGATION'],'constraintDescription':'Synthetic navigation within F2_TEST','completionCondition':'routeGenerated=true'})
   self.cfg(f"/task-definitions/{self.definition['id']}/enable",'POST')
  ret=raw(self.op,'/tasks',{'taskGoal':'F180 synthetic navigation F2_TEST_GATE','taskFamily':self.definition['definitionCode'],'sceneParams':{'targetLocation':'F2_TEST_GATE'}},'POST');assert ret['http']==200,ret
  self.task=int(sql(f"select max(id) from {SC}.tasks where task_goal='F180 synthetic navigation F2_TEST_GATE'"));d=self.devices[0];msg=None
  for _ in range(100):
   msgs=[v['message'] for v in d.messages if v['message']['commandType']=='TASK_ACCEPT' and v['message']['taskId']==self.op(f'/tasks/{self.task}')['taskCode']]
   if msgs:msg=msgs[-1];break
   time.sleep(.1)
  assert msg,'no TASK_ACCEPT';d.state['workStatus']='BUSY';accept=d.report('TASK_RESPONSE',{'commandId':msg['commandId'],'accepted':True});snap=self.snapshot();a=next(a for a in snap['agents'] if a['deviceCode']==d.code)
  return self.record('busy-task-link',{'submit':ret,'accept':accept,'taskId':self.task,'snapshot':snap,'task':self.op(f'/tasks/{self.task}'),'assignments':self.op(f'/tasks/{self.task}/step-assignments')},{'busy':a['workStatus']=='BUSY','currentTask':a['currentTaskId']==self.task,'capabilitySummary':'CAP_NAVIGATION' in a['capabilityTypes']})
 def complete(self):
  d=self.devices[0];task=self.op(f'/tasks/{self.task}');msgs=[v['message'] for v in d.messages if v['message']['commandType']=='EXECUTE_CAPABILITY' and v['message']['taskId']==task['taskCode']];msg=msgs[-1];time.sleep(.3)
  ret=d.report('EXECUTION_FEEDBACK',{'commandId':msg['commandId'],'attemptNo':msg['attemptNo'],'executionResult':'SUCCESS','outputParams':{'routeGenerated':True}});d.state['workStatus']='IDLE';d.heartbeat();task=self.op(f'/tasks/{self.task}')
  return self.record('core-task-completion',{'feedback':ret,'task':task,'snapshot':self.snapshot(),'events':self.op(f'/tasks/{self.task}/events'),'commands':rows(f'select * from {SC}.device_commands where task_id={self.task}')},{'completed':task['status']=='COMPLETED','feedback200':ret['http']==200})
 def cleanup(self):
  self.mode='live'
  if self.task and self.op(f'/tasks/{self.task}')['status'] not in ['COMPLETED','FAILED','MANUAL_TERMINATED']:self.op(f'/tasks/{self.task}/terminate','POST',{'confirmed':True,'reason':'Synthetic F023 cleanup'})
  if self.definition:self.cfg(f"/task-definitions/{self.definition['id']}/disable",'POST')
  for d in self.devices:
   d.stop=True;d.paused=True;d.state.update(onlineStatus='ONLINE',workStatus='IDLE');d.heartbeat();self.cfg(f'/devices/{d.code}/status','POST',{'status':'INACTIVE'});d.server.shutdown();d.server.server_close()
  for item in self.original:
   self.cfg('/devices/'+item['code'],'PUT',item['body'])
   for c in item['capabilities']:sql(f"update {SC}.device_capabilities set capability_status={lit(c['capability_status'])} where id={c['id']}")
  return self.record('cleanup',{'agentRows':self.agentrows(),'activeAssignments':sql(f"select count(*) from {SC}.task_step_assignments where step_status in ('PENDING_ASSIGNMENT','EXECUTING')"),'occupiedAgents':sql(f'select count(*) from {SC}.device_agents where current_task_id is not null'),'network':self.net})

def serve():
 f=Fixture();f.setup()
 model=mod('controlled',R/'acceptance/stage3/fixtures/f013-v142-controlled-model.py');model.JOURNAL=L/'f023-v180-model-requests.jsonl'
 original=model.plan
 def plan(goal):
  steps=original(goal)
  for s in steps:s['stepTimeout']=600
  return steps
 model.plan=plan
 ms=ThreadingHTTPServer(('127.0.0.1',18117),model.Handler);threading.Thread(target=ms.serve_forever,daemon=True).start()
 class Control(BaseHTTPRequestHandler):
  def log_message(self,*a):pass
  def do_GET(self):
   cmd=self.path.strip('/').split('?')[0]
   try:
    if cmd.startswith('mode-'):f.mode=cmd[5:];out={'mode':f.mode}
    elif cmd=='offline0':out=f.offline(0)
    elif cmd=='recover0':out=f.recover(0)
    else:out=getattr(f,{'task':'create_task'}.get(cmd,cmd))()
    data=json.dumps(out,ensure_ascii=False).encode();self.send_response(200)
   except Exception as ex:
    import traceback
    data=json.dumps({'error':str(ex),'trace':traceback.format_exc()}).encode();self.send_response(500)
   self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(data)
 cs=ThreadingHTTPServer(('127.0.0.1',18135),Control);threading.Thread(target=cs.serve_forever,daemon=True).start()
 class Proxy(BaseHTTPRequestHandler):
  def log_message(self,*a):pass
  def do_GET(self):self.handle_request()
  def do_POST(self):self.handle_request()
  def do_PUT(self):self.handle_request()
  def do_DELETE(self):self.handle_request()
  def handle_request(self):
   status=200;ctype='application/json';data=b''
   if self.path.startswith('/api/'):
    start=time.time();payload=self.rfile.read(int(self.headers.get('Content-Length','0'))) or None
    req=urllib.request.Request('http://127.0.0.1:18129'+self.path,payload,{k:v for k,v in self.headers.items() if k.lower() in ['authorization','content-type']},method=self.command)
    if self.path.startswith('/api/v1/situation/snapshot') and f.mode=='refresh-fail':status=503;data=b'{"message":"synthetic proxy unavailable"}'
    else:
     try:
      with urllib.request.urlopen(req,timeout=90) as res:data=res.read();status=res.status
     except urllib.error.HTTPError as ex:data=ex.read();status=ex.code
    if self.path.startswith('/api/v1/situation/snapshot') and status==200 and f.mode in ['contract','empty']:
     obj=json.loads(data)
     if f.mode=='empty':obj['data']['agents']=[]
     else:
      source=next(a for a in obj['data']['agents'] if a['deviceCode'].startswith('G180_'));extra=[]
      for label,x,y in [('NULL_X',None,250),('NULL_Y',250,None),('EMPTY','',250),('NEGATIVE',-1,250),('OVER_X',1261,250),('OVER_Y',250,6896),('ORIGIN',0,0),('MAX',1260,6895)]:
       a=copy.deepcopy(source);a.update(deviceCode='CONTRACT_'+label,deviceName='CONTRACT_'+label,location={'x':x,'y':y,'zone':'F2_TEST'},currentTaskId=None,workStatus='IDLE');extra.append(a)
      obj['data']['agents']=extra
     data=json.dumps(obj,ensure_ascii=False).encode()
    f.net.append({'at':now(),'method':self.command,'path':self.path,'http':status,'startEpoch':start,'mode':f.mode})
   else:
    path=R/'frontend/dist'/self.path.split('?')[0].lstrip('/')
    if self.path.split('?')[0]=='/F2.jpg' and f.mode=='map-fail':status=404;data=b'synthetic map missing';ctype='text/plain'
    else:
     if not path.is_file():path=R/'frontend/dist/index.html'
     data=path.read_bytes();ctype=mimetypes.guess_type(path)[0] or 'application/octet-stream'
   self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 ps=ThreadingHTTPServer(('127.0.0.1',15179),Proxy);print('F023 fixture READY',flush=True);(L/'f023-v180-ready').write_text(now());ps.serve_forever()

if __name__=='__main__':
 command=sys.argv[1]
 if command=='start':start()
 elif command=='serve':serve()
 else:
  with urllib.request.urlopen('http://127.0.0.1:18135/'+command,timeout=100) as res:out=json.load(res)
  print(json.dumps(out,ensure_ascii=False) if command=='mode-live' else str({'command':command,'result':out.get('result'),'checks':out.get('checks'),'taskId':out.get('taskId')}))
