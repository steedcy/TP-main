"""F024 independent real HTTP/SQL/protocol round. GPT-owned schema/Redis10.
Synthetic model and protocol devices, production packaged JAR/dist; no hardware claim.
serve owns devices/model/proxy. Control endpoints run observations and preserve raw evidence.
"""
import importlib.util,json,time,threading,copy,sys,traceback,mimetypes,urllib.request,urllib.error,socket
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
R=Path(__file__).resolve().parents[2];L=R/'.local-test';E=R/'acceptance/stage3/evidence'
def mod(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
b=mod('b',R/'acceptance/stage3/probe-f022-v179-base.py');SC=b.SC;sql=b.sql;rows=b.rows;lit=b.lit;now=b.now
SHA='fc55f713e5d74d6fb41761f53fed84b4bc4efd7b';OUT=E/'SRS_F024-V1.183-http-sql-protocol-20261108.json';CONFIG=L/'f024-v183-cases.json'
def raw(api,path,body=None,method='POST'):
 req=urllib.request.Request(b.l.BASE+path,json.dumps(body).encode() if body is not None else None,{'Content-Type':'application/json',**({'Authorization':'Bearer '+api.token} if api else {})},method=method)
 try:
  with urllib.request.urlopen(req,timeout=90) as r:return {'http':r.status,'body':json.load(r)}
 except urllib.error.HTTPError as ex:return {'http':ex.code,'body':json.load(ex)}
class Round:
 def __init__(self):
  self.cfg=b.l.API('配置管理员');self.op=b.l.API('运行操作员');self.devices=[];self.tasks=[];self.cases={};self.original={};self.templates=[];self.net=[]
  self.ev={'productSha':SHA,'tag':'V1.183','handoffSha':'c7cd6b3696cfc8d18813778d2b9bf74d7f27286b','baseline':'V2.4','startedAt':now(),'schema':SC,'redisDb':10,'cases':[],'diagnostics':[]}
  if OUT.exists():
   self.ev=json.loads(OUT.read_text(encoding='utf8'));self.original=self.ev.get('originalDevices',{});self.tasks=self.ev.get('taskIds',[]);self.ev['diagnostics'].append({'at':now(),'kind':'fixture-resume','reason':'setup attempted new device beyond existing 20-device limit; use an owned inactive scanner instead, preserve partial setup and original restore values'})
  self.save()
 def save(self):
  self.ev.update(taskIds=self.tasks,templateIds=self.templates);OUT.write_text(json.dumps(self.ev,ensure_ascii=False,indent=2),encoding='utf8')
  (L/'f024-v183-state.json').write_text(json.dumps({'taskIds':self.tasks,'cases':{r['name']:r.get('taskId') for r in self.ev['cases']},'devices':[{'code':d.code,'agent':d.agent,'port':d.port} for d in self.devices]}),encoding='utf8')
 def record(self,name,values,checks=None):
  row={'name':name,'at':now(),**values}
  if checks is not None:row.update(checks=checks,result='P' if all(checks.values()) else 'F')
  self.ev['cases'].append(row);self.save();print(name,row.get('taskId'),row.get('result'),flush=True);return row
 def observe(self,tid):
  o=b.p.observe(self.op,tid)
  for k,t in [('commandRows','device_commands'),('exceptions','task_exceptions')]:o[k]=rows(f'select * from {SC}.{t} where task_id={tid} order by id')
  o['transport']={d.code:copy.deepcopy(d.messages_for(o['task']['taskCode'])) for d in self.devices};return o
 def setup(self):
  self.ev['initialPendingRows']=rows(f"select id,task_id,step_status from {SC}.task_step_assignments where step_status in ('PENDING_ASSIGNMENT','EXECUTING') order by id")
  self.ev['initialOccupied']=rows(f'select agent_code,current_task_id from {SC}.device_agents where current_task_id is not null')
  assert not self.ev['initialOccupied'],'schema actively occupied'
  if 'riskBefore' not in self.ev:self.ev['riskBefore']=self.cfg('/risk-rules')
  self.save()
  self.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
  specs=[('G160_F016_A',18132,'MOBILE_ROBOT',['CAP_NAVIGATION']),('G145_F013_SCAN',18133,'BAGGAGE_SCANNER',['CAP_BAGGAGE_MEASURE','CAP_OVERSIZE_ALERT']),('G145_F013_DISPLAY',18134,'SMART_DISPLAY',['CAP_INFO_DISPLAY']),('G160_F016_B',18136,'MOBILE_ROBOT',['CAP_NAVIGATION']),('G183_F024_SCAN2',18137,'BAGGAGE_SCANNER',['CAP_BAGGAGE_MEASURE','CAP_OVERSIZE_ALERT'])]
  self.caps={}
  for code,port,typ,caps in specs:
   d=b.Device(code,port);d.simtype=typ;d.healthcaps=caps;self.devices.append(d)
   body={'deviceCode':code,'deviceName':'F183 '+typ,'deviceTypeCode':'SIMULATOR','isSimulator':True,'simulatedDeviceType':typ,'areaCode':'F2_TEST','positionX':0,'positionY':0,'accessEndpoint':f'http://127.0.0.1:{port}','statusReportInterval':5,'accessCredentialRef':'synthetic-f024'}
   if sql(f'select count(*) from {SC}.devices where device_code={lit(code)}')=='0':self.cfg('/devices','POST',body)
   old=self.cfg('/devices/'+code)
   if code not in self.original:self.original[code]={'body':{k:old.get(k) for k in ['deviceName','areaCode','positionX','positionY','accessEndpoint','statusReportInterval','remark']},'capabilities':self.cfg('/devices/'+code+'/capabilities')}
   self.ev['originalDevices']=copy.deepcopy(self.original);self.save()
   self.cfg('/devices/'+code,'PUT',{k:v for k,v in body.items() if k in self.original[code]['body']})
   d.token=self.cfg(f'/devices/{code}/device-token/rotate','POST')['accessToken'];self.cfg(f'/devices/{code}/connection-test','POST');self.cfg(f'/devices/{code}/status','POST',{'status':'ACTIVE'});self.cfg(f'/devices/{code}/connection-test','POST')
   d.agent=next(a['agentId'] for a in self.cfg('/device-agents?page=1&size=100')['content'] if a['deviceCode']==code);d.heartbeat()
   for cap in caps:self.cfg(f'/devices/{code}/capabilities/{cap}/test','POST');self.cfg(f'/devices/{code}/capabilities/{cap}/status','POST',{'status':'ENABLED'})
   self.caps.update({c['capabilityType']:c for c in self.cfg('/devices/'+code+'/capabilities') if c['capabilityType'] in caps})
   threading.Thread(target=d.loop,daemon=True).start()
  self.ev['presetBefore']=rows(f"select * from {SC}.task_definitions where definition_code='OVERSIZE_BAGGAGE_HANDLING'")
  self.record('resources-ready',{'capabilities':self.caps,'health':b.l.request('http://127.0.0.1:18129/actuator/health')},{'fiveSyntheticDevices':len(self.devices)==5})
 def steps(self,count=4):
  types=['CAP_BAGGAGE_MEASURE','CAP_OVERSIZE_ALERT','CAP_INFO_DISPLAY','CAP_NAVIGATION'];conditions=['measureStatus=SUCCESS','reportStatus=SUCCESS','displayStatus=SUCCESS','routeGenerated=true'];out=[]
  for seq,cap in enumerate(types[:count],1):
   vals={}
   for p in self.caps[cap]['inputParams']:
    v=p.get('defaultValue')
    if v is None or v=='':continue
    if p['type'] in ['Integer','Long']:v=int(v)
    elif p['type'] in ['Double','Float','Number']:v=float(v)
    elif p['type']=='Boolean':v=str(v).lower()=='true'
    vals[p['name']]=v
   out.append({'stepSeq':seq,'stepGoal':'F183 synthetic '+cap,'capabilityType':cap,'inputParams':vals,'precondition':'device online','completionCondition':conditions[seq-1],'failureHandling':'失败重试一次后候选切换，仍失败局部重规划','stepTimeout':180})
  return out
 def config(self,marker,**kwargs):
  self.cases[marker]={'steps':self.steps(),'goalCompletion':'routeGenerated=true',**kwargs};CONFIG.write_text(json.dumps(self.cases),encoding='utf8')
 def submit(self,name,scene=None,**kwargs):
  marker='F183_'+name.upper().replace('-','_');self.config(marker,**kwargs)
  body={'taskGoal':marker+' 处理位于F2_TEST_SERVICE的行李并引导至超规柜台','taskFamily':'OVERSIZE_BAGGAGE_HANDLING','sceneParams':{'baggageLocation':'F2_TEST_SERVICE','targetCounter':'F2_TEST_GATE','targetLocation':'F2_TEST_GATE','baggageId':marker,'tempBusinessId':marker,'dimensionThresholdCm':158,'weightThresholdKg':32,'thresholdSource':'SYNTHETIC_DEPLOYMENT_F024_158CM_32KG','routePreference':'BARRIER_FREE','alertLevel':'WARNING','contentType':'TEXT','contentData':'超规行李办理提示','handlingInstructions':'虚构部署办理说明：前往超规柜台核验，费用以承运人现场政策为准，完成托运并遵守安全须知。',**(scene or {})}}
  response=raw(self.op,'/tasks',body);tid=int(sql(f'select id from {SC}.tasks where task_goal={lit(body["taskGoal"])} order by id desc limit 1'));self.tasks.append(tid);row=self.record(name,{'taskId':tid,'request':body,'response':response});return row
 def event(self,name,body,api=None,path='/tasks/measurement-event'):
  response=raw(api or self.op,path,body);tid=response.get('body',{}).get('data',{}).get('id')
  if tid is not None:self.tasks.append(tid)
  return self.record(name,{'taskId':tid,'request':body,'response':response})
 def drive(self,row,oversize=True,failcap=None,failures=0,maxsteps=20):
  tid=row['taskId'];code=self.op(f'/tasks/{tid}')['taskCode'];seen=set();actions=[];end=time.monotonic()+40
  while time.monotonic()<end and len(actions)<maxsteps:
   status=self.op(f'/tasks/{tid}')['status']
   if status in ['COMPLETED','FAILED','PENDING_MANUAL','MANUAL_TERMINATED']:break
   did=False
   for d in self.devices:
    for envelope in list(d.messages_for(code)):
     msg=envelope['message'];key=(msg['commandId'],msg['commandType'],msg.get('attemptNo'))
     if key in seen or msg['commandType'] not in ['TASK_ACCEPT','EXECUTE_CAPABILITY']:continue
     seen.add(key);did=True
     with d.guard:
      if msg['commandType']=='TASK_ACCEPT':
       d.state['workStatus']='BUSY';ret=d.report('TASK_RESPONSE',{'commandId':msg['commandId'],'accepted':True})
      else:
       cap=msg.get('capabilityType');failed=cap==failcap and failures>0
       if failed:failures-=1
       output={'measureStatus':'SUCCESS','length':80.0 if oversize else 55.0,'width':55.0 if oversize else 40.0,'height':35.0 if oversize else 20.0,'weight':35.0 if oversize else 10.0,'isOversize':oversize,'baggageInfo':'synthetic baggage F183','reportStatus':'SUCCESS','alertId':'F183-ALERT','displayStatus':'SUCCESS','routeGenerated':True}
       ret=d.report('EXECUTION_FEEDBACK',{'commandId':msg['commandId'],'attemptNo':msg['attemptNo'],'executionResult':'FAILED' if failed else 'SUCCESS',**({'reasonCode':'ERR_F183_SYNTHETIC_FAILURE'} if failed else {}),'outputParams':{} if failed else output});d.state['workStatus']='IDLE'
     actions.append({'deviceCode':d.code,'message':msg,'response':ret});row['actions']=actions;self.save();time.sleep(.15)
   if not did:time.sleep(.2)
  row['after']=self.observe(tid);self.save();return row['after']
 def terminate(self,tid):
  if self.op(f'/tasks/{tid}')['status'] not in ['COMPLETED','FAILED','MANUAL_TERMINATED']:raw(self.op,f'/tasks/{tid}/terminate',{'confirmed':True,'reason':'Synthetic F024 cleanup'})
  for d in self.devices:
   with d.guard:d.state.update(onlineStatus='ONLINE',workStatus='IDLE');d.heartbeat()
 def state(self):return {'tasks':rows(f"select id,task_code,status,scene_params from {SC}.tasks where id in ({','.join(map(str,self.tasks)) or '0'}) order by id"),'cases':[(r['name'],r.get('taskId'),r.get('result')) for r in self.ev['cases']]}
 def cleanup(self):
  for tid in self.tasks:self.terminate(tid)
  for d in self.devices:
   d.paused=True;d.stop=True;self.cfg(f'/devices/{d.code}/status','POST',{'status':'INACTIVE'});self.cfg('/devices/'+d.code,'PUT',self.original[d.code]['body'])
   for c in self.original[d.code]['capabilities']:sql(f"update {SC}.device_capabilities set capability_status={lit(c['capabilityStatus'])} where device_id=(select id from {SC}.devices where device_code={lit(d.code)}) and capability_code={lit(c['capabilityCode'])}")
  for rule in self.ev['riskBefore']:self.cfg('/risk-rules/'+rule['ruleCode']+'/update','POST',{'enabled':rule['enabled']})
  final=rows(f"select id,task_id,step_status from {SC}.task_step_assignments where step_status in ('PENDING_ASSIGNMENT','EXECUTING') order by id")
  return self.record('cleanup',{'finalPendingRows':final,'occupied':rows(f'select agent_code,current_task_id from {SC}.device_agents where current_task_id is not null')},{'historicalPendingUnchanged':final==self.ev['initialPendingRows'],'noOccupied':sql(f'select count(*) from {SC}.device_agents where current_task_id is not null')=='0'})
def serve():
 q=Round();q.setup();model=mod('model',R/'acceptance/stage3/fixtures/f024-v183-controlled-model.py');ms=ThreadingHTTPServer(('127.0.0.1',18117),model.Handler);threading.Thread(target=ms.serve_forever,daemon=True).start()
 class Control(BaseHTTPRequestHandler):
  def log_message(self,*a):pass
  def do_POST(self):self.handle_control()
  def do_GET(self):self.handle_control()
  def handle_control(self):
   cmd=self.path.strip('/');status=200
   try:
    if cmd=='exec':
     body=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))));ns={'q':q,'b':b,'raw':raw,'rows':rows,'sql':sql,'SC':SC,'lit':lit,'time':time,'json':json,'copy':copy,'R':R,'E':E,'L':L};exec(body['code'],ns);out=ns.get('result',{})
    else:out=getattr(q,cmd)()
   except Exception as ex:
    status=500;out={'error':str(ex),'traceback':traceback.format_exc()};q.ev['diagnostics'].append({'at':now(),'command':cmd,**out});q.save()
   data=json.dumps(out,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(data)
 cs=ThreadingHTTPServer(('127.0.0.1',18135),Control);threading.Thread(target=cs.serve_forever,daemon=True).start()
 class Proxy(BaseHTTPRequestHandler):
  def log_message(self,*a):pass
  def do_GET(self):self.handle_proxy()
  def do_POST(self):self.handle_proxy()
  def do_PUT(self):self.handle_proxy()
  def do_DELETE(self):self.handle_proxy()
  def handle_proxy(self):
   status=200;ctype='application/json'
   if self.path.startswith('/api/'):
    payload=self.rfile.read(int(self.headers.get('Content-Length','0'))) or None;req=urllib.request.Request('http://127.0.0.1:18129'+self.path,payload,{k:v for k,v in self.headers.items() if k.lower() in ['authorization','content-type']},method=self.command)
    try:
     with urllib.request.urlopen(req,timeout=90) as res:data=res.read();status=res.status
    except urllib.error.HTTPError as ex:data=ex.read();status=ex.code
    q.net.append({'at':now(),'method':self.command,'path':self.path,'http':status})
   else:
    path=R/'frontend/dist'/self.path.split('?')[0].lstrip('/')
    if not path.is_file():path=R/'frontend/dist/index.html'
    data=path.read_bytes();ctype=mimetypes.guess_type(path)[0] or 'application/octet-stream'
   self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 print('F024 fixture READY',flush=True);(L/'f024-v183-ready').write_text(now());ThreadingHTTPServer(('127.0.0.1',15179),Proxy).serve_forever()
if __name__=='__main__':serve()
