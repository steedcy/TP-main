import importlib.util,json,time
from pathlib import Path
r=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('p',r/'acceptance/stage3/probe-f013-v149.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
op=p.l.API('运行操作员');cfg=p.l.API('配置管理员');ev=p.metadata();tid=None
old=json.loads((r/'acceptance/stage3/evidence/SRS_F013-V1.145-baseline-and-manual-actions-20261103.json').read_text(encoding='utf-8'))
secret=json.loads(p.l.protect((p.OLD/'.local-test/gpt-f007-v126-robot.dpapi').read_bytes(),True))['token']
def sim(value):return p.l.request('http://127.0.0.1:18132/device-api/v1/control/scenario','POST',{'scenarioResult':value},token=secret)
try:
 sim('TIMEOUT');cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
 req={'taskGoal':'F149_REPLAN_BAD synthetic timeout navigation to F2_TEST_GATE','taskFamily':old['definition']['definitionCode'],'sceneParams':{'targetLocation':'F2_TEST_GATE'}}
 task=op('/tasks','POST',req);tid=task['id'];ev['request']=req;ev['taskId']=tid;ev['initial']=p.observe(op,tid)
 for _ in range(60):
  after=p.observe(op,tid)
  if len(after['plans'])>=2 and after['task']['status']=='PENDING_MANUAL':break
  time.sleep(0.5)
 ev['after']=after;ev['snapshots']=op(f'/tasks/{tid}/context-snapshots');v=after['plans'][-1]
 ev['checks']={'realTimeoutEvents':any(e.get('reasonCode')=='SIMULATED_TIMEOUT' for e in after['events']),
 'newLocalVersion':len(after['plans'])==2,'conflictRejected':v['constraintCheckResult']=='FAIL' and any(e['reasonCode']=='ERR_COMPLETION_CONDITION_CONFLICT' for e in v['validationErrors']),
 'newVersionUnfrozen':not v['frozenAt'],'pendingManual':after['task']['status']=='PENDING_MANUAL',
 'oldFrozenVersionUnchanged':ev['initial']['plans'][0]==after['plans'][0]}
 print(json.dumps({'taskId':tid,'status':after['task']['status'],'checks':ev['checks']}),flush=True)
finally:
 sim('SUCCESS');cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':True})
 if tid and op(f'/tasks/{tid}')['status'] not in ['COMPLETED','FAILED','MANUAL_TERMINATED']:
  ev['cleanupTerminate']=p.raw(op,f'/tasks/{tid}/terminate',{'reason':'F013 V149 actual-timeout fixture cleanup','confirmed':True})
 p.save('real-timeout-replan',ev)
