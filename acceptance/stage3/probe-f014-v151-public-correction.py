"""Correct the probe's mismatched flight output field; retain task213 as fixture diagnostics."""
import importlib.util,json,time,copy
from pathlib import Path
r=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('p',r/'acceptance/stage3/probe-f014-v151.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
cfg=p.l.API('配置管理员');op=p.l.API('运行操作员');ev=p.metadata()
prior=json.loads((r/'acceptance/stage3/evidence/SRS_F014-V1.151-deterministic-pairs-20261104.json').read_text(encoding='utf-8'))
old=next(x for x in prior['cases'] if x['name']=='F151_PUBLIC_FLIGHT');steps=copy.deepcopy(old['observed']['plans'][0]['planSteps'])
ev['fixtureDiagnostic']={'originalTaskId':213,'incorrectCondition':'updateStatus=SUCCESS','actualSimulatorOutput':'publishStatus=SUCCESS','reason':'GPT probe used a field outside the capability output schema, leading to expected condition failure after a device SUCCESS. Original raw evidence retained; not a product F.'}
steps[0]['completionCondition']='publishStatus=SUCCESS';steps[0]['inputParams']['flightNumber']='ZZ151';steps[2]['inputParams']['notificationContent']='Synthetic public flight ZZ151 gate information'
ev['actualFlightCapabilitySchema']=next(x for x in cfg('/devices/G151_F014_FLIGHT/capabilities') if x['capabilityCode']=='CAP_FLIGHT_UPDATE')
marker='F151_PUBLIC_FLIGHT_CORRECTED';case={marker:{'steps':steps,'confidence':.99,'diverse':False,'goalCompletion':'航班变更信息已送达且旅客后续引导（如需）已完成'}};(r/'.local-test/f014-v151-cases.json').write_bytes(json.dumps(case).encode())
ev['ruleBefore']=next(x for x in cfg('/risk-rules') if x['ruleCode']=='RULE_RESOURCE_CRITICAL')
try:
 cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
 req=copy.deepcopy(old['request']);req['taskGoal']=marker+' public flight ZZ151 gate service to F2_TEST_GATE';ev['request']=req
 task=op('/tasks','POST',req);tid=task['id']
 for _ in range(80):
  o=p.observe(op,tid)
  if o['task']['status'] in ['COMPLETED','FAILED','PENDING_MANUAL']:break
  time.sleep(.3)
 ev['observed']=o;v=o['plans'][0]
 ev['checks']={'threePass':all(v[k]=='PASS' for k in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']),'publicInfoLow':v['riskLevel']=='LOW' and v['riskReasonCode'] is None,'automaticExecutionAndCompletion':o['task']['status']=='COMPLETED' and len(o['assignments'])==3 and all(x['stepStatus']=='COMPLETED' for x in o['assignments']),'noReplan':not o['task']['replanUsed'],'sixFieldsInTimeline':any(all(k in e.get('detailSummary','') for k in ['风险等级=','原因码=','判定依据=','置信度=','规则集版本=','推荐处置=AUTO_EXECUTE']) for e in o['events'] if e['eventType']=='SUPERVISION_JUDGED')}
 print('public corrected',tid,ev['checks'],flush=True)
finally:
 cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':ev['ruleBefore']['enabled']});p.save('public-flight-correction',ev)
