"""Real, isolated occupied-resource fixture: a live task owns GPT robot, then a second plan uses it."""
import importlib.util,json,time
from pathlib import Path
r=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('p',r/'acceptance/stage3/probe-f013-v143.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
op=p.l.API('运行操作员');cfg=p.l.API('配置管理员');ev=p.metadata();ev['ownerTaskId']=None
secret=json.loads(p.l.protect((p.OLD/'.local-test/gpt-f007-v126-robot.dpapi').read_bytes(),True))['token']
def sim(body):return p.l.request('http://127.0.0.1:18132/device-api/v1/control/scenario','POST',body,token=secret)
ev['fixtureCorrection']='First attempt omitted simulator /device-api/v1 prefix and got404 before creating any task; corrected endpoint and re-ran. Initial fixture error is not a product F.'
ev['resourceRuleBefore']=p.sql(f"select enabled from {p.SC}.risk_rules where rule_code='RULE_RESOURCE_CRITICAL'")
assert ev['resourceRuleBefore']=='t'
try:
 ev['simulatorNoFeedback']=sim({'scenarioResult':'NO_FEEDBACK'})
 cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
 owner=op('/tasks','POST',{'taskGoal':'F013_GOOD owner occupies exclusive robot V143','taskFamily':'EXT_2AD8B934','sceneParams':{'targetLocation':'F2_TEST_GATE'}});tid=owner['id'];ev['ownerTaskId']=tid
 for _ in range(20):
  ownerObs=p.observe(op,tid)
  if ownerObs['task']['status']=='EXECUTING' and any(a['stepStatus']=='EXECUTING' for a in ownerObs['assignments']):break
  time.sleep(0.5)
 assert ownerObs['task']['status']=='EXECUTING' and ownerObs['assignments'],'Owner fixture did not acquire resource'
 ev['ownerBeforeSecond']=ownerObs
 cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':True})
 ev['occupiedAgentBeforeSecond']=p.sql(f"select agent_code,online_status,work_status,current_task_id,current_step_seq from {p.SC}.device_agents where agent_code='AGT-803437A3'")
 second=op('/tasks','POST',{'taskGoal':'F013_GOOD competing plan for occupied exclusive robot V143','taskFamily':'EXT_2AD8B934','sceneParams':{'targetLocation':'F2_TEST_GATE'}});tid2=second['id'];ev['secondTaskId']=tid2
 ev['second']=p.observe(op,tid2);ev['secondSnapshots']=op(f'/tasks/{tid2}/context-snapshots')
 ev['ownerAfterSecond']=p.observe(op,tid)
 ev['checks']={'ownerReallyExecuting':ownerObs['task']['status']=='EXECUTING',
  'competingConstraintFails':any(v['constraintCheckResult']=='FAIL' for v in ev['second']['plans']),
  'competingNotFrozen':all(not v['frozenAt'] for v in ev['second']['plans']),
  'competingNeverSupervised':not any(e['eventType']=='SUPERVISION_JUDGED' for e in ev['second']['events']),
  'noCompetingAllocationOrCommands':not ev['second']['assignments'] and not ev['second']['commands'],
  'ownerContinuesUnchanged':ev['ownerAfterSecond']['task']['status']=='EXECUTING' and ev['ownerAfterSecond']['plans']==ownerObs['plans']}
 print(json.dumps({'ownerTaskId':tid,'secondTaskId':tid2,'occupiedAgent':ev['occupiedAgentBeforeSecond'],'checks':ev['checks']}),flush=True)
finally:
 cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':True})
 ev['simulatorRestored']=sim({'scenarioResult':'SUCCESS'})
 if ev['ownerTaskId']:
  ev['ownerTermination']=p.raw(op,f"/tasks/{ev['ownerTaskId']}/terminate",{'reason':'F013 synthetic occupied-resource fixture cleanup','confirmed':True})
  ev['ownerAfterCleanup']=p.observe(op,ev['ownerTaskId'])
 ev['resourceRuleAfter']=p.sql(f"select enabled from {p.SC}.risk_rules where rule_code='RULE_RESOURCE_CRITICAL'")
 ev['robotAfterCleanup']=p.sql(f"select agent_status,online_status,work_status,coalesce(current_task_id::text,'NULL') from {p.SC}.device_agents where agent_code='AGT-803437A3'")
 p.save('resource-conflict',ev)
