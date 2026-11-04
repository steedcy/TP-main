"""Current live deterministic rule pairs and core passenger/flight plans, GPT schema only."""
import importlib.util,json,time,copy
from pathlib import Path
r=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('p',r/'acceptance/stage3/probe-f014-v151.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
cfg=p.l.API('配置管理员');op=p.l.API('运行操作员');ev=p.metadata();ev['cases']=[]
ev['rulesBefore']=cfg('/risk-rules');ev['definitionBefore']=cfg('/task-definitions/17');cfg('/task-definitions/17/enable','POST')
cases={}
def setcase(marker,steps,completion='routeGenerated=true'):
 cases[marker]={'steps':steps,'goalCompletion':completion};(r/'.local-test/f014-v151-cases.json').write_bytes(json.dumps(cases).encode())
def submit(marker,steps,family='EXT_0FA30230',scene=None,completion='routeGenerated=true'):
 setcase(marker,steps,completion)
 req={'taskGoal':marker+' synthetic service to F2_TEST_GATE','taskFamily':family,'sceneParams':scene or {'targetLocation':'F2_TEST_GATE'}}
 task=op('/tasks','POST',req);tid=task['id']
 for _ in range(60):
  o=p.observe(op,tid)
  if o['task']['status'] in ['COMPLETED','FAILED','PENDING_MANUAL']:break
  time.sleep(.3)
 v=o['plans'][0] if o['plans'] else {};events=[e for e in o['events'] if e['eventType']=='SUPERVISION_JUDGED']
 row={'name':marker,'request':req,'controlledResponse':cases[marker],'observed':o,'checks':{'threePass':all(v.get(k)=='PASS' for k in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']),'supervised':bool(events)}}
 row['ruleSnapshot']=cfg('/risk-rules')
 if events:row['checks']['sixFieldsInEvent']=all(k in events[0].get('detailSummary','') for k in ['风险等级=','原因码=','判定依据=','置信度=','规则集版本=','推荐处置='])
 if o['task']['status'] not in ['COMPLETED','FAILED','MANUAL_TERMINATED']:row['cleanupTerminate']=p.raw(op,f'/tasks/{tid}/terminate',{'reason':'F014 V151 deterministic fixture cleanup','confirmed':True})
 ev['cases'].append(row);p.save('deterministic-pairs',ev)
 print(marker,tid,o['task']['status'],v.get('riskLevel'),v.get('riskReasonCode'),row['checks'],flush=True)
 return row
def toggle(code,value):return cfg('/risk-rules/'+code+'/update','POST',{'enabled':value})
try:
 toggle('RULE_RESOURCE_CRITICAL',True);high=submit('F151_RESOURCE_ON',[p.step()])
 toggle('RULE_RESOURCE_CRITICAL',False);low=submit('F151_RESOURCE_OFF',[p.step()])
 ev['resourcePairChecks']={'sameCandidate':high['observed']['plans'][0]['planSteps']==low['observed']['plans'][0]['planSteps'],'onHigh':high['observed']['plans'][0]['riskReasonCode']=='RULE_RESOURCE_CRITICAL','offLow':low['observed']['plans'][0]['riskLevel']=='LOW','versionChanged':high['observed']['plans'][0]['ruleSetVersion']!=low['observed']['plans'][0]['ruleSetVersion']}
 # Explicit optional business zone input enables a valid plan to exercise cross-zone policy.
 ev['navigationSchemaBefore']=p.sql(f"select input_params::text from {p.SC}.device_capabilities c join {p.SC}.devices d on d.id=c.device_id where d.device_code='G126_ROBOT' and capability_code='CAP_NAVIGATION'")
 if not any(x['name']=='targetZone' for x in json.loads(ev['navigationSchemaBefore'])):
  p.sql(f"update {p.SC}.device_capabilities set input_params=(input_params::jsonb || '[{{\"name\":\"targetZone\",\"type\":\"String\",\"required\":false}}]'::jsonb)::json where device_id=(select id from {p.SC}.devices where device_code='G126_ROBOT') and capability_code='CAP_NAVIGATION'")
 cross=[p.step(seq=1,params={'targetLocation':'F2_TEST_GATE','targetZone':'F2_ZONE_A'}),p.step(seq=2,params={'targetLocation':'F2_TEST_GATE','targetZone':'F2_ZONE_B'})]
 toggle('RULE_CROSS_ZONE',True);ch=submit('F151_CROSS_ON',cross)
 toggle('RULE_CROSS_ZONE',False);cl=submit('F151_CROSS_OFF',cross);toggle('RULE_CROSS_ZONE',True)
 ev['crossPairChecks']={'sameCandidate':ch['observed']['plans'][0]['planSteps']==cl['observed']['plans'][0]['planSteps'],'onHigh':ch['observed']['plans'][0]['riskReasonCode']=='RULE_CROSS_ZONE','offLow':cl['observed']['plans'][0]['riskLevel']=='LOW','versionChanged':ch['observed']['plans'][0]['ruleSetVersion']!=cl['observed']['plans'][0]['ruleSetVersion']}
 # Business input values follow the actual enabled capability schemas/defaults.
 def action(cap,seq,code,completion):
  schema=next(x for x in cfg(f'/devices/{code}/capabilities') if x['capabilityCode']==cap)
  inputs={}
  for f in schema['inputParams']:
   if not f.get('required') and f.get('defaultValue') is None:continue
   value=f.get('defaultValue')
   if value is None:value={'targetLocation':'F2_TEST_GATE','notificationContent':'Synthetic service notification','displayContent':'Synthetic public flight information','flightNumber':'ZZ151'}.get(f['name'],'Synthetic fixture')
   if f.get('type') in ['Integer','Long']:value=int(value)
   if f.get('type') in ['Double','Float']:value=float(value)
   inputs[f['name']]=value
  q=p.step(cap,seq,inputs);q['completionCondition']=completion;return q
 display=action('CAP_INFO_DISPLAY',1,'G145_F013_DISPLAY','displayStatus=SUCCESS')
 notice=action('CAP_NOTIFICATION',2,'G126_ROBOT','notificationStatus=SUCCESS')
 escort=action('CAP_ESCORT',3,'G126_ROBOT','arrivalStatus=ARRIVED')
 special=[display,notice,escort]
 scene={'assistanceType':'WHEELCHAIR','serviceLocation':'F2_SERVICE_POINT','targetLocation':'F2_TEST_GATE','notificationRequired':True}
 toggle('RULE_ESCORT_SPECIAL_PASSENGER',True);eh=submit('F151_ESCORT_ON',special,'SPECIAL_PASSENGER_SERVICE',scene,'旅客已到达目标地点')
 toggle('RULE_ESCORT_SPECIAL_PASSENGER',False);el=submit('F151_ESCORT_OFF',special,'SPECIAL_PASSENGER_SERVICE',scene,'旅客已到达目标地点')
 toggle('RULE_ESCORT_SPECIAL_PASSENGER',True)
 ev['escortPairChecks']={'sameCandidate':eh['observed']['plans'][0]['planSteps']==el['observed']['plans'][0]['planSteps'],'onHigh':eh['observed']['plans'][0]['riskReasonCode']=='RULE_ESCORT_SPECIAL_PASSENGER','offLow':el['observed']['plans'][0]['riskLevel']=='LOW','versionChanged':eh['observed']['plans'][0]['ruleSetVersion']!=el['observed']['plans'][0]['ruleSetVersion']}
 rendezvous=[p.step(seq=1),copy.deepcopy(display),copy.deepcopy(notice),copy.deepcopy(escort)]
 for i,q in enumerate(rendezvous,1):q['stepSeq']=i
 submit('F151_RENDEZVOUS',rendezvous,'SPECIAL_PASSENGER_SERVICE',scene,'旅客已到达目标地点')
 flight=action('CAP_FLIGHT_UPDATE',1,'G151_F014_FLIGHT','publishStatus=SUCCESS');flight['inputParams']['flightNumber']='ZZ151';fd=copy.deepcopy(display);fd['stepSeq']=2;fn=copy.deepcopy(notice);fn['stepSeq']=3;fn['inputParams']['notificationContent']='Synthetic public flight ZZ151 gate information'
 submit('F151_PUBLIC_FLIGHT',[flight,fd,fn],'FLIGHT_CHANGE_RESPONSE',{'flightNumber':'ZZ151','targetLocation':'F2_TEST_GATE','newGate':'F2_TEST_GATE'},'航班变更信息已送达且旅客后续引导（如需）已完成')
 ev['ruleAudit']=p.sql(f"select operation_type,operation_target,operation_result,detail::text from {p.SC}.operation_logs where operation_type='RISK_RULE_CHANGE' order by id desc limit 12")
finally:
 if 'navigationSchemaBefore' in ev:
  encoded=ev['navigationSchemaBefore'].replace("'","''");p.sql(f"update {p.SC}.device_capabilities set input_params='{encoded}'::json where device_id=(select id from {p.SC}.devices where device_code='G126_ROBOT') and capability_code='CAP_NAVIGATION'")
 for rule in ev['rulesBefore']:
  if rule['ruleCode'].startswith('RULE_'):toggle(rule['ruleCode'],rule['enabled'])
 if ev['definitionBefore']['definitionStatus']=='DISABLED':cfg('/task-definitions/17/disable','POST')
 ev['fixturesRestored']=True;p.save('deterministic-pairs',ev)
