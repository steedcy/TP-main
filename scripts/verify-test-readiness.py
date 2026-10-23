"""Limited preparation checks with real HTTP commands; does not execute or score the 95 cases."""
import importlib.util,pathlib,time,copy,json
p=pathlib.Path(__file__).with_name('local-test-environment.py')
spec=importlib.util.spec_from_file_location('localenv',p);env=importlib.util.module_from_spec(spec);spec.loader.exec_module(env)
api=env.API();evidence={'recordedAt':env.stamp(),'scope':'PREPARATION_SMOKE_ONLY','checks':[]}
path=env.EVIDENCE/'20261022-readiness-smoke.json'

def check(name,action):
    started=time.monotonic()
    try:
        detail=action();result={'name':name,'result':'PASS','detail':detail}
    except Exception as ex: result={'name':name,'result':'FAIL','detail':str(ex)}
    result['elapsedSeconds']=round(time.monotonic()-started,3);evidence['checks'].append(result);env.save(path,evidence)
    print(name+': '+result['result'],flush=True)
    return result

def agents(): return {a['deviceCode']:a for a in api('/device-agents?page=1&size=100')['content']}
def wait_agent(code,status):
    deadline=time.monotonic()+50
    while time.monotonic()<deadline:
        a=agents()[code]
        if a['onlineStatus']==status:return a
        time.sleep(1)
    raise RuntimeError('Expected '+status+' heartbeat state was not observed')

def offline():
    code='SIM_F2_DISPLAY'
    try:
        started=time.monotonic();env.control(code,'offline');off=wait_agent(code,'OFFLINE')
        assert time.monotonic()-started<5,'Explicit offline report was not committed immediately'
        env.control(code,'online');on=wait_agent(code,'ONLINE')
        return {'offline':off,'recovered':on}
    finally: env.control(code,'online')

def silent():
    code='SIM_F2_BAGGAGE_B'
    try:
        started=time.monotonic();env.control(code,'silent');off=wait_agent(code,'OFFLINE')
        elapsed=time.monotonic()-started;env.control(code,'heartbeat');on=wait_agent(code,'ONLINE')
        return {'detectionSeconds':round(elapsed,3),'offline':off,'recovered':on}
    finally: env.control(code,'heartbeat')

fixtures=env.load(env.FIXTURES/'baselines.json');fixture=fixtures[2]
def template_for(f):return next(t for t in api('/baseline-templates') if t['templateIntent']==f['taskFamily'] and t['isPreset'])
def edit(f):
    t=template_for(f)
    return api('/baseline-templates/'+str(t['id']),'PUT',{k:f[k] for k in ['inputParams','steps']})
def run(f,t):return env.run_baseline(api,t,f,{code:a['agentId'] for code,a in agents().items()})

def failure(mode):
    f=copy.deepcopy(fixture)
    if mode=='no_feedback':f['steps'][0]['stepTimeout']=10
    t=edit(f);code='SIM_F2_FLIGHT'
    try:
        env.control(code,mode);result=run(f,t)
        assert result['result']=='FAILED',result
        assert template_for(f)['templateStatus']=='DRAFT'
        if mode=='no_feedback':assert any(e['eventType']=='STEP_TIMEOUT_DETECTED' for e in result['events'])
        else:assert any(e['eventType']=='EXECUTION_FEEDBACK_RECEIVED' for e in result['events'])
        return result
    finally:env.control(code,'success')

def cancel():
    t=edit(fixture);code='SIM_F2_FLIGHT'
    try:
        env.control(code,'delay:10000')
        result=api(f"/baseline-templates/{t['id']}/dry-run",'POST',{
          'inputParams':{p['name']:p.get('defaultValue') for p in fixture['inputParams']},
          'simulatedDevices':[{'stepSeq':i+1,'agentId':agents()[c]['agentId']}for i,c in enumerate(fixture['devices'])]})
        time.sleep(2)
        result=api(f"/baseline-templates/{t['id']}/dry-runs/{result['taskId']}/cancel",'POST')
        assert result['result']=='CANCELLED',result
        time.sleep(10)
        result=api(f"/baseline-templates/{t['id']}/dry-runs/{result['taskId']}")
        assert result['result']=='CANCELLED'
        return result
    finally:env.control(code,'delay:1000')

def restore_templates():
    results=[]
    for f in fixtures:
        t=edit(f);result=run(f,t);assert result['result']=='SUCCESS',result
        api(f"/baseline-templates/{t['id']}/enable",'POST');results.append(result)
    return results

def kimi():
    operator=env.API('运行操作员')
    request={'taskGoal':'测试准备冒烟：测试航班TEST1022登机口变更，请先发布变更信息，再引导旅客前往F2_TEST_GATE。全部为虚构场景。',
      'taskFamily':'FLIGHT_CHANGE_RESPONSE','sceneParams':{p['name']:p.get('defaultValue') for p in fixture['inputParams']}}
    task=operator('/tasks','POST',request);deadline=time.monotonic()+100
    while task['status'] not in ['COMPLETED','FAILED','PENDING_MANUAL','MANUAL_TERMINATED'] and time.monotonic()<deadline:
        time.sleep(1);task=operator('/tasks/'+str(task['id']))
    detail={'task':task,'plans':operator(f"/tasks/{task['id']}/plan-versions"),'steps':operator(f"/tasks/{task['id']}/step-assignments"),'events':operator(f"/tasks/{task['id']}/events")}
    env.save(env.EVIDENCE/'20261022-kimi-task-smoke.json',detail)
    assert task['status']=='COMPLETED',task
    return {'taskId':task['id'],'taskCode':task['taskCode'],'status':task['status'],'isDryRun':task['isDryRun'],'evidence':'20261022-kimi-task-smoke.json'}

check('Explicit device offline and recovery',offline)
check('Silent heartbeat loss and automatic detection',silent)
check('Actual failed feedback stops trial and retains draft',lambda:failure('failed'))
check('Actual timeout feedback stops trial',lambda:failure('timeout'))
check('Missing feedback triggers platform step timeout',lambda:failure('no_feedback'))
check('Cancel running trial prevents late completion',cancel)
check('Restore three successful enabled baseline versions',restore_templates)
check('Real Kimi planning to simulator execution',kimi)
env.status()
if any(c['result']=='FAIL' for c in evidence['checks']):raise SystemExit(1)
