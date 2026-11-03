import importlib.util,json,time
from pathlib import Path
r=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('p',r/'acceptance/stage3/probe-f013-v145.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
op=p.l.API('运行操作员');cfg=p.l.API('配置管理员');ev=p.metadata();tid=None
secret=json.loads(p.l.protect((p.OLD/'.local-test/gpt-f007-v126-robot.dpapi').read_bytes(),True))['token']
def sim(value):return p.l.request('http://127.0.0.1:18132/device-api/v1/control/scenario','POST',{'scenarioResult':value},token=secret)
try:
 sim('TIMEOUT');cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
 task=op('/tasks','POST',{'taskGoal':'F013_GOOD actual simulator timeout replan V145','taskFamily':'EXT_2AD8B934','sceneParams':{'targetLocation':'F2_TEST_GATE'}});tid=task['id'];ev['taskId']=tid;ev['initial']=p.observe(op,tid)
 for _ in range(50):
  after=p.observe(op,tid)
  if len(after['plans'])>=2 or (after['task']['status']=='PENDING_MANUAL' and after['task'].get('replanUsed')):break
  time.sleep(0.5)
 ev['after']=after;ev['snapshots']=op(f'/tasks/{tid}/context-snapshots')
 ev['checks']={'realTimeoutEvents':any(e.get('reasonCode')=='SIMULATED_TIMEOUT' for e in after['events']), 'newLocalVersion':len(after['plans'])>=2,
 'newVersionFrozen':len(after['plans'])>=2 and bool(after['plans'][-1]['frozenAt']),
 'oldFrozenVersionUnchanged':ev['initial']['plans'][0]==after['plans'][0],
 'newVersionNoResourceConflict':len(after['plans'])>=2 and not any(e['reasonCode']=='ERR_RESOURCE_CONFLICT' for e in after['plans'][-1]['validationErrors'])}
 print(json.dumps({'taskId':tid,'status':after['task']['status'],'checks':ev['checks']}),flush=True)
finally:
 sim('SUCCESS');cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':True})
 if tid and op(f'/tasks/{tid}')['status'] not in ['COMPLETED','FAILED','MANUAL_TERMINATED']:
  ev['cleanupTerminate']=p.raw(op,f'/tasks/{tid}/terminate',{'reason':'F013 actual-timeout fixture cleanup','confirmed':True})
 p.save('real-timeout-replan',ev)
