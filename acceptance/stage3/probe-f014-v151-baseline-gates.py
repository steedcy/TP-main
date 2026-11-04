"""Actual baseline success/failure and hard supervision gates; only own GPT fixtures."""
import importlib.util,json,time,copy
from pathlib import Path
r=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('p',r/'acceptance/stage3/probe-f014-v151.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
cfg=p.l.API('配置管理员');op=p.l.API('运行操作员');ev=p.metadata();ev['cases']=[]
old=json.loads((r/'acceptance/stage3/evidence/SRS_F013-V1.145-baseline-and-manual-actions-20261103.json').read_text(encoding='utf-8'))
templateId=old['validTemplateBefore']['id'];family=old['definition']['definitionCode']
ev['definitionBefore']=cfg('/task-definitions/17');ev['rulesBefore']=cfg('/risk-rules');ev['templateBefore']=cfg(f'/baseline-templates/{templateId}')
secret=json.loads(p.l.protect((r.parent/'tip/.local-test/gpt-f007-v126-robot.dpapi').read_bytes(),True))['token']
def sim(value):return p.l.request('http://127.0.0.1:18132/device-api/v1/control/scenario','POST',{'scenarioResult':value},token=secret)
cases={}
def submit(marker,steps):
 cases[marker]={'steps':steps,'confidence':1.0,'diverse':False};(r/'.local-test/f014-v151-cases.json').write_bytes(json.dumps(cases).encode())
 req={'taskGoal':marker+' synthetic navigation to F2_TEST_GATE','taskFamily':family,'sceneParams':{'targetLocation':'F2_TEST_GATE'}}
 task=op('/tasks','POST',req);tid=task['id'];initial=p.observe(op,tid)
 for _ in range(100):
  o=p.observe(op,tid)
  if o['task']['status'] in ['COMPLETED','FAILED','PENDING_MANUAL']:break
  time.sleep(.3)
 row={'name':marker,'request':req,'initial':initial,'observed':o};ev['cases'].append(row);p.save('baseline-and-hard-gates',ev);return row
try:
 cfg('/task-definitions/17/enable','POST')
 cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':True})
 p.sql(f"update {p.SC}.baseline_templates set template_status='ENABLED' where id={templateId}")
 ev['templateFixtureScope']='Only own earlier validated template is seeded ENABLED to test runtime downgrade routing; this is not template publication/dry-run acceptance.'
 sim('SUCCESS');good=submit('F151_BASELINE_SUCCESS',[p.step()]);o=good['observed'];v=o['plans']
 good['assignmentPlanIds']=p.sql(f"select plan_version_id from {p.SC}.task_step_assignments where task_id={o['task']['id']} order by id").splitlines()
 good['checks']={'autonomousHigh':v[0]['riskLevel']=='HIGH','separateBaselineFrozen':len(v)==2 and v[-1]['source']=='BASELINE_TEMPLATE' and bool(v[-1]['frozenAt']),'completed':o['task']['status']=='COMPLETED','originalHighNotExecuted':bool(good['assignmentPlanIds']) and all(int(a)==v[-1]['id'] for a in good['assignmentPlanIds'])}
 print(good['name'],o['task']['id'],good['checks'],flush=True);p.save('baseline-and-hard-gates',ev)
 sim('TIMEOUT');failed=submit('F151_BASELINE_FAILURE',[p.step()]);o=failed['observed'];v=o['plans']
 failed['checks']={'actualTimeout':any(e.get('reasonCode')=='SIMULATED_TIMEOUT' or 'TIMEOUT' in str(e.get('detailSummary','')) for e in o['events']),'pendingManual':o['task']['status']=='PENDING_MANUAL','baselineSource':v[-1]['source']=='BASELINE_TEMPLATE','noReplan':not o['task']['replanUsed'] and not any(e['eventType']=='REPLANNING_TRIGGERED' for e in o['events']),'onlyAutonomousAndBaseline':len(v)==2}
 print(failed['name'],o['task']['id'],failed['checks'],flush=True);p.save('baseline-and-hard-gates',ev);sim('SUCCESS')
 p.sql(f"update {p.SC}.baseline_templates set template_status='DISABLED' where id={templateId}")
 cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
 structure=p.step();structure.pop('precondition');capability=p.step('CAP_NONEXISTENT_F014');constraint=p.step(params={'targetLocation':'F2_TEST_GATE','speed':2})
 for marker,steps,field in [('F151_BAD_STRUCTURE',[structure],'structureCheckResult'),('F151_BAD_CAPABILITY',[capability],'capabilityCheckResult'),('F151_BAD_SAFETY',[constraint],'constraintCheckResult')]:
  row=submit(marker,steps);o=row['observed'];tid=o['task']['id'];row['supervisionRequest']=p.raw(op,f'/tasks/{tid}/manual-actions',{'action':'REQUEST_SUPERVISION','reason':'Synthetic unvalidated plan supervision request'})
  row['afterInterception']=p.observe(op,tid)
  row['checks']={'relevantHardCheckFail':o['plans'][0][field]=='FAIL','notFrozen':not o['plans'][0]['frozenAt'],'neverSupervised':not any(e['eventType']=='SUPERVISION_JUDGED' for e in row['afterInterception']['events']),'noAssignmentsOrCommands':not o['assignments'] and not o['commands'],'http4004110':row['supervisionRequest']['http']==400 and row['supervisionRequest']['body']['code']==4110,'interceptionPersisted':any(e['eventType']=='FORCE_BYPASS_INTERCEPTED' for e in row['afterInterception']['events']) and bool(row['afterInterception']['bypassAuditRows'])}
  print(marker,tid,row['checks'],flush=True);p.save('baseline-and-hard-gates',ev)
finally:
 sim('SUCCESS');status=ev['templateBefore']['templateStatus'];p.sql(f"update {p.SC}.baseline_templates set template_status='{status}' where id={templateId}")
 for rule in ev['rulesBefore']:
  if rule['ruleCode'].startswith('RULE_'):cfg('/risk-rules/'+rule['ruleCode']+'/update','POST',{'enabled':rule['enabled']})
 if ev['definitionBefore']['definitionStatus']=='DISABLED':cfg('/task-definitions/17/disable','POST')
 for row in ev['cases']:
  tid=row['observed']['task']['id']
  if op(f'/tasks/{tid}')['status'] not in ['COMPLETED','FAILED','MANUAL_TERMINATED']:row['cleanupTerminate']=p.raw(op,f'/tasks/{tid}/terminate',{'reason':'F014 V151 baseline and gate cleanup','confirmed':True})
 ev['fixturesRestored']=True;p.save('baseline-and-hard-gates',ev)
