"""Core baggage plan, ordering, required channel and offline hard-gate observations."""
import importlib.util,json,copy,time
from pathlib import Path
r=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('p',r/'acceptance/stage3/probe-f013-v145.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
op=p.l.API('运行操作员');cfg=p.l.API('配置管理员');ev=p.metadata();ev['cases']=[]
fixture=json.loads((r/'acceptance/stage3/evidence/SRS_F013-V1.145-core-device-fixture-20261103.json').read_text(encoding='utf-8'))
caps={c['capabilityType']:c for d in fixture['devices'] for c in d['enabledCapabilities']}
def values(schema):
 out={}
 for d in schema:
  v=d.get('defaultValue')
  if v is None or v=='':continue
  if d['type'] in ['Integer','Long']:v=int(v)
  elif d['type'] in ['Double','Float','Number']:v=float(v)
  elif d['type']=='Boolean':v=str(v).lower()=='true'
  out[d['name']]=v
 return out
types=['CAP_BAGGAGE_MEASURE','CAP_OVERSIZE_ALERT','CAP_INFO_DISPLAY','CAP_NAVIGATION']
steps=[]
for n,cap in enumerate(types,1):
 inputs={'targetLocation':'F2_TEST_GATE'} if cap=='CAP_NAVIGATION' else values(caps[cap]['inputParams'])
 steps.append({'stepSeq':n,'stepGoal':'Synthetic baggage action '+cap,'capabilityType':cap,'inputParams':inputs,'precondition':'device online','completionCondition':'status=SUCCESS','failureHandling':'manual handling','stepTimeout':60})
order=[copy.deepcopy(steps[i]) for i in [2,0,1,3]]
for n,step in enumerate(order,1):step['stepSeq']=n
missing=[copy.deepcopy(x) for x in steps if x['capabilityType']!='CAP_INFO_DISPLAY']
for n,step in enumerate(missing,1):step['stepSeq']=n
(r/'.local-test/f013-v145-model-cases.json').write_bytes(json.dumps({'F013_BAG_GOOD':steps,'F013_BAG_ORDER':order,'F013_BAG_NO_DISPLAY':missing,'F013_BAG_OFFLINE':steps},ensure_ascii=False).encode('utf-8'))
ev['controlledPlans']={'good':steps,'order':order,'noDisplay':missing}
rows=p.sql(f"select id,template_status from {p.SC}.baseline_templates where task_family='OVERSIZE_BAGGAGE_HANDLING' and template_status='ENABLED'")
ev['enabledPresetBaselinesBefore']=rows.splitlines()
secret=json.loads(p.l.protect((r/'.local-test/G145_F013_SCAN.dpapi').read_bytes(),True))['token']
def scanner_online(online):return p.l.request('http://127.0.0.1:18133/device-api/v1/control/online?value='+str(online).lower(),'POST',token=secret)
def observe(name):
 task=op('/tasks','POST',{'taskGoal':name+' synthetic oversize baggage to F2_TEST_GATE','taskFamily':'OVERSIZE_BAGGAGE_HANDLING','sceneParams':{'targetLocation':'F2_TEST_GATE','dimensionThresholdCm':158,'weightThresholdKg':23,'baggageInfo':'synthetic baggage fixture'}})
 c={'name':name,'observed':p.observe(op,task['id'])};ev['cases'].append(c);p.save('baggage-core',ev);return c['observed']
try:
 for row in ev['enabledPresetBaselinesBefore']:
  ident,_=row.split('|');p.sql(f"update {p.SC}.baseline_templates set template_status='DISABLED' where id={int(ident)}")
 good=observe('F013_BAG_GOOD');ordered=observe('F013_BAG_ORDER');gap=observe('F013_BAG_NO_DISPLAY')
 ev['scannerOfflineResponse']=scanner_online(False)
 for _ in range(30):
  a=next(a for a in cfg('/device-agents?page=1&size=100')['content'] if a['deviceCode']=='G145_F013_SCAN')
  if a['onlineStatus']=='OFFLINE':break
  time.sleep(0.5)
 assert a['onlineStatus']=='OFFLINE';ev['offlineAgent']=a;offline=observe('F013_BAG_OFFLINE')
 def errors(o):return [x['reasonCode'] for v in o['plans'] for x in v['validationErrors']]
 ev['checks']={'goodFourChannels':set(x['capabilityType'] for x in good['plans'][0]['planSteps'])==set(types),
 'goodThreeChecksAndFreeze':all(good['plans'][0][k]=='PASS' for k in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']) and bool(good['plans'][0]['frozenAt']),
 'goodEnteredSupervision':any(e['eventType']=='SUPERVISION_JUDGED' for e in good['events']),
 'orderRejected': 'ERR_BAGGAGE_BRANCH_ORDER' in errors(ordered),
 'missingChannelRejected':'ERR_REQUIRED_CHANNEL_MISSING' in errors(gap),
 'offlineNoCandidateRejected':'ERR_NO_ONLINE_CANDIDATE' in errors(offline),
 'invalidPlansUnfrozenAndNeverSupervised':all(all(not v['frozenAt'] for v in o['plans']) and not any(e['eventType']=='SUPERVISION_JUDGED' for e in o['events']) for o in [ordered,gap,offline]),
 'invalidNoAssignmentsOrCommands':all(not o['assignments'] and not o['commands'] for o in [ordered,gap,offline])}
 print(json.dumps({'tasks':[c['observed']['task']['id'] for c in ev['cases']],'checks':ev['checks']}),flush=True)
finally:
 ev['scannerRestored']=scanner_online(True)
 cfg('/devices/G145_F013_SCAN/connection-test','POST')
 for row in ev['enabledPresetBaselinesBefore']:
  ident,status=row.split('|');p.sql(f"update {p.SC}.baseline_templates set template_status='{status}' where id={int(ident)}")
 ev['presetBaselineStatesRestored']=True;p.save('baggage-core',ev)
