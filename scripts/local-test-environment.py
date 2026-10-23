"""Reproducible local preparation; credentials remain in memory or Windows DPAPI storage.
Use the bundled Python: configure, start, status, smoke, or fault DEVICE MODE.
This is readiness verification, not the formal 95-case campaign.
"""
import argparse, base64, ctypes, datetime, json, os, pathlib, shutil, subprocess, sys, time
import urllib.request, urllib.error, winreg

ROOT=pathlib.Path(__file__).resolve().parents[1]
LOCAL=ROOT/'.local-test'; LOCAL.mkdir(exist_ok=True)
EVIDENCE=ROOT/'document/test-evidence'; EVIDENCE.mkdir(parents=True,exist_ok=True)
BASE='http://127.0.0.1:8080/api/v1'
FIXTURES=ROOT/'scripts/test-fixtures'

def load(path): return json.loads(path.read_text(encoding='utf-8'))
def save(path,data): path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def stamp(): return datetime.datetime.now().astimezone().isoformat()

class Blob(ctypes.Structure): _fields_=[('size',ctypes.c_ulong),('data',ctypes.POINTER(ctypes.c_ubyte))]
def protect(raw, decrypt=False):
    buf=ctypes.create_string_buffer(raw); source=Blob(len(raw),ctypes.cast(buf,ctypes.POINTER(ctypes.c_ubyte))); dest=Blob()
    if decrypt: ok=ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(source),None,None,None,None,0,ctypes.byref(dest))
    else: ok=ctypes.windll.crypt32.CryptProtectData(ctypes.byref(source),'TIP local simulators',None,None,None,0,ctypes.byref(dest))
    if not ok: raise RuntimeError('Windows credential encryption failed')
    try: return ctypes.string_at(dest.data,dest.size)
    finally: ctypes.windll.kernel32.LocalFree(dest.data)
def secrets():
    p=LOCAL/'device-credentials.dpapi'
    return json.loads(protect(base64.b64decode(p.read_bytes()),True)) if p.exists() else {}
def store_secrets(values): (LOCAL/'device-credentials.dpapi').write_bytes(base64.b64encode(protect(json.dumps(values).encode())))

def account(role='配置管理员'):
    rows=[[v.strip() for v in line.strip().strip('|').split('|')] for line in (ROOT/'user.md').read_text(encoding='utf-8-sig').splitlines() if line.strip().startswith('|')]
    row=next(row for row in rows[1:] if role in row[0]); return row[1],row[2]

def request(url,method='GET',data=None,token=None,timeout=75):
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    body=json.dumps(data,ensure_ascii=False).encode() if data is not None else None
    try:
        with urllib.request.urlopen(urllib.request.Request(url,body,headers,method=method),timeout=timeout) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as ex:
        try:
            error=json.loads(ex.read()); message=error.get('message',error.get('error','request failed'))
        except Exception: message='request failed'
        raise RuntimeError(f'HTTP {ex.code}: {message}') from None

class API:
    def __init__(self,role='配置管理员'):
        username,password=account(role)
        response=request(BASE+'/auth/login','POST',{'username':username,'password':password})
        self.token=response['data']['token']; self.role=response['data']['user']['role']
    def __call__(self,path,method='GET',data=None):
        result=request(BASE+path,method,data,self.token)
        if result.get('code') not in (0,200): raise RuntimeError(f"API {result.get('code')}: {result.get('message')}")
        return result.get('data')

def env():
    result=os.environ.copy()
    for name in ['MOONSHOT_API_KEY','MOONSHOT_MODEL','MOONSHOT_BASE_URL','PLANNING_MODEL_PROVIDER','DEVICE_CREDENTIAL_ENCRYPTION_KEY','DB_HOST','DB_PORT','DB_NAME','DB_USERNAME','DB_PASSWORD','REDIS_HOST','REDIS_PORT','REDIS_PASSWORD']:
        if result.get(name): continue
        for root,path in [(winreg.HKEY_CURRENT_USER,'Environment'),(winreg.HKEY_LOCAL_MACHINE,r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment')]:
            try:
                with winreg.OpenKey(root,path) as key: result[name]=str(winreg.QueryValueEx(key,name)[0])
                break
            except OSError: pass
    return result

def launch(key,command,environment):
    log=open(LOCAL/(key+'.log'),'ab',buffering=0)
    proc=subprocess.Popen(command,cwd=ROOT,env=environment,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    processes=load(LOCAL/'processes.json') if (LOCAL/'processes.json').exists() else {}
    processes[key]={'pid':proc.pid,'startedAt':stamp()};save(LOCAL/'processes.json',processes)

def wait_health(url,token=None):
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        try: return request(url,token=token,timeout=2)
        except Exception: time.sleep(1)
    raise RuntimeError('Service did not become ready; inspect .local-test logs')

def start_backend(provider='moonshot'):
    java=shutil.which('java'); jar=ROOT/'backend/target/airport-ai-app-1.0.0.jar'
    try:
        if request('http://127.0.0.1:8080/actuator/health',timeout=2).get('status')=='UP':
            print('Backend already healthy; use the profile switch action to restart it');return
    except Exception: pass
    runtime=LOCAL/'runtime';runtime.mkdir(exist_ok=True)
    runnable=runtime/'backend.jar';shutil.copy2(jar,runnable)
    environment=env()
    if provider=='fault': environment.update(PLANNING_MODEL_PROVIDER='external',PLANNING_MODEL_ENDPOINT='http://127.0.0.1:8099',PLANNING_MODEL_API_KEY='local-fixture')
    else: environment['PLANNING_MODEL_PROVIDER']='moonshot'
    launch('backend',[java,'-Xms128m','-Xmx384m','-XX:+UseSerialGC','-jar',str(runnable)],environment)
    health=wait_health('http://127.0.0.1:8080/actuator/health'); print('Backend health:',health.get('status'))

def start_simulator(device,token,agent=None):
    port=int(device['accessEndpoint'].rsplit(':',1)[1]); environment=env()
    try:
        result=request(device['accessEndpoint']+'/device-api/v1/health?nonce=local-preparation',token=token,timeout=2)
        if result['deviceCode']==device['deviceCode']: return
        raise RuntimeError('Simulator port already occupied by another identity')
    except urllib.error.URLError: pass
    environment.update(SIMULATOR_PORT=str(port),SIMULATOR_DEVICE_CODE=device['deviceCode'],SIMULATED_DEVICE_TYPE=device['simulatedDeviceType'],
        SIMULATOR_DEVICE_TOKEN=token,SIMULATOR_X=str(device['positionX']),SIMULATOR_Y=str(device['positionY']),SIMULATOR_ZONE=device['areaCode'],
        SIMULATOR_HEARTBEAT_INTERVAL_SECONDS='5',SIMULATOR_EXECUTION_DELAY_MS='1000')
    if device['simulatedDeviceType']=='BAGGAGE_SCANNER':
        environment.update(SIMULATOR_BAGGAGE_LENGTH_CM='80',SIMULATOR_BAGGAGE_WIDTH_CM='55',SIMULATOR_BAGGAGE_HEIGHT_CM='35',SIMULATOR_BAGGAGE_WEIGHT_KG='35')
    if agent:
        environment['SIMULATOR_AGENT_CODE']=agent
        environment['SIMULATOR_REPORT_URL']='http://127.0.0.1:8080/device-api/v1/agents/'+agent+'/report'
    launch(device['deviceCode'],[shutil.which('java'),'-Xms32m','-Xmx128m','-XX:MaxMetaspaceSize=128m','-XX:+UseSerialGC','-jar',str(ROOT/'simulator/target/device-simulator-runtime.jar')],environment)
    wait_health(device['accessEndpoint']+'/device-api/v1/health?nonce=local-preparation',token)

def configure():
    api=API(); values=secrets(); evidence={'recordedAt':stamp(),'configurationRole':api.role,'devices':[],'baselines':[]}
    current={d['deviceCode']:d for d in api('/devices?page=1&size=100')['content']}
    agents={a['deviceCode']:a['agentId'] for a in api('/device-agents?page=1&size=100')['content']}
    for device in load(FIXTURES/'devices.json'):
        code=device['deviceCode']
        if code not in current: api('/devices','POST',{k:v for k,v in device.items() if k!='capabilities'})
        if code not in values:
            values[code]=api('/devices/'+code+'/device-token/rotate','POST')['accessToken']; store_secrets(values)
        start_simulator(device,values[code],agents.get(code))
        connection=api('/devices/'+code+'/connection-test','POST')
        if connection.get('result')!='PASSED': raise RuntimeError(code+' connection test failed')
        if code not in agents: agents[code]=api('/device-agents','POST',{'deviceCode':code})['agentId']
        # Binding is idempotent and makes recovery after a process restart deterministic.
        request(device['accessEndpoint']+'/device-api/v1/agents/'+agents[code]+'/binding','POST',{
            'deviceCode':code,'agentCode':agents[code],'reportUrl':'http://127.0.0.1:8080/device-api/v1/agents/'+agents[code]+'/report',
            'heartbeatIntervalSeconds':5,'heartbeatTimeoutSeconds':30},values[code])
        request(device['accessEndpoint']+'/device-api/v1/control/online?value=true','POST',token=values[code])
        deadline=time.monotonic()+25
        while time.monotonic()<deadline:
            online=next(a for a in api('/device-agents?page=1&size=100')['content'] if a['deviceCode']==code)
            if online['onlineStatus']=='ONLINE': break
            time.sleep(1)
        else: raise RuntimeError(code+' did not report a heartbeat after binding')
        existing={c['capabilityCode']:c for c in api('/devices/'+code+'/capabilities')}
        tested=[]
        for capability in device['capabilities']:
            cap=capability['capabilityCode']; path='/devices/'+code+'/capabilities'
            if cap not in existing: api(path,'POST',capability)
            result=api(path+'/'+cap+'/test','POST')
            if result['capabilityStatus']!='TESTED_PASSED': raise RuntimeError(code+'/'+cap+' failed actual device test: '+str(result.get('testResult')))
            api(path+'/'+cap+'/status','POST',{'status':'ENABLED'})
            tested.append({'capabilityType':cap,'result':result['capabilityStatus'],'testResult':result.get('testResult')})
        evidence['devices'].append({'deviceCode':code,'simulatedDeviceType':device['simulatedDeviceType'],'agentId':agents[code],'connection':connection,'capabilities':tested})
        save(EVIDENCE/'20261022-environment-preparation.json',evidence)
        print(code+': connected, bound, '+str(len(tested))+' actual capability tests passed',flush=True)
    for fixture in load(FIXTURES/'baselines.json'):
        template=next(t for t in api('/baseline-templates') if t['templateIntent']==fixture['taskFamily'] and t['isPreset'])
        body={k:fixture[k] for k in ['inputParams','steps']}
        template=api('/baseline-templates/'+str(template['id']),'PUT',body)
        result=run_baseline(api,template,fixture,agents)
        if result['result']!='SUCCESS': raise RuntimeError(template['templateName']+' actual dry run failed')
        api('/baseline-templates/'+str(template['id'])+'/enable','POST')
        evidence['baselines'].append({'templateId':template['id'],'templateName':template['templateName'],'version':template['templateVersion'],'status':'ENABLED','trial':result})
        print(template['templateName']+': actual dry run passed and enabled',flush=True)
    save(EVIDENCE/'20261022-environment-preparation.json',evidence)

def run_baseline(api,template,fixture,agents,timeout=100):
    inputs={p['name']:p.get('defaultValue') for p in fixture['inputParams']}
    result=api('/baseline-templates/'+str(template['id'])+'/dry-run','POST',{'inputParams':inputs,
        'simulatedDevices':[{'stepSeq':i+1,'agentId':agents[code]} for i,code in enumerate(fixture['devices'])]})
    deadline=time.monotonic()+timeout
    while result['result']=='RUNNING' and time.monotonic()<deadline:
        time.sleep(1);result=api(f"/baseline-templates/{template['id']}/dry-runs/{result['taskId']}")
    return result

def control(code,mode):
    device=next(d for d in load(FIXTURES/'devices.json') if d['deviceCode']==code)
    token=secrets()[code]; endpoint=device['accessEndpoint']+'/device-api/v1/control/'
    if mode in ('offline','online'): return request(endpoint+'online?value='+str(mode=='online').lower(),'POST',token=token)
    if mode in ('silent','heartbeat'): return request(endpoint+'heartbeat?value='+str(mode=='heartbeat').lower(),'POST',token=token)
    if mode.startswith('delay:'): return request(endpoint+'delay?milliseconds='+mode.split(':')[1],'POST',token=token)
    return request(endpoint+'scenario','POST',{'scenarioResult':mode.upper()},token)

def status():
    api=API(); devices=api('/devices?page=1&size=100'); agents=api('/device-agents?page=1&size=100')
    summary={'recordedAt':stamp(),'devices':devices,'agents':agents,'templates':api('/baseline-templates')}
    save(EVIDENCE/'20261022-environment-status.json',summary)
    print(json.dumps({'devices':len(devices['content']),'agents':[{k:a[k] for k in ['agentId','deviceCode','onlineStatus','workStatus']} for a in agents['content']],
        'baselines':[{k:t[k] for k in ['id','templateName','templateStatus','templateVersion']} for t in summary['templates']]},ensure_ascii=False,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=['configure','backend','start','status','fault','frontend','model-fixture']);parser.add_argument('device',nargs='?');parser.add_argument('mode',nargs='?');parser.add_argument('--provider',choices=['moonshot','fault'],default='moonshot');args=parser.parse_args()
    try:
        if args.action=='configure': configure()
        elif args.action=='backend': start_backend(args.provider)
        elif args.action=='frontend':
            node=shutil.which('node') or str(pathlib.Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe')
            launch('frontend',[node,str(ROOT/'frontend/node_modules/vite/bin/vite.js'),str(ROOT/'frontend'),'--host','127.0.0.1','--port','5173','--strictPort'],env())
        elif args.action=='model-fixture': launch('planning-fixture',[sys.executable,'-X','utf8',str(ROOT/'scripts/planning-fault-server.py')],env())
        elif args.action=='status': status()
        elif args.action=='fault': print(control(args.device,args.mode))
        elif args.action=='start':
            api=API(); agents={a['deviceCode']:a['agentId'] for a in api('/device-agents?page=1&size=100')['content']};values=secrets()
            for device in load(FIXTURES/'devices.json'): start_simulator(device,values[device['deviceCode']],agents.get(device['deviceCode']))
    except Exception as ex:
        print('Preparation stopped: '+str(ex),file=sys.stderr);sys.exit(1)
