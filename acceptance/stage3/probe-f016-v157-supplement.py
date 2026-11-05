"""Complete independent branches after fixing probe timing/schema assumptions.
Retains the original observations, including probe errors. Product SHA unchanged.
"""
import importlib.util,copy,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('f016',Path(__file__).with_name('probe-f016-v157.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.OUT=ROOT/'acceptance/stage3/evidence/SRS_F016-V1.157-supplement-20261105.json'
q=m.Probe()
q.setup()
q.ev['rulesBefore']=q.cfg('/risk-rules')
q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
q.ev['rulesDuring']=q.cfg('/risk-rules');q.save()
try:
 q.run('all-reject',lambda:q.reject('all-reject-fixed',True))
 q.run('busy-control',q.busy_control)
 q.run('concurrent',q.concurrent)
 q.run('no-candidate',q.no_candidate)
 q.run('terminate-online',q.terminate_case)
 q.run('terminate-offline',lambda:q.terminate_case(True))
 def tie():
  q.reset();row=q.submit('tie-agent-code');d,msg=q.wait_message(row);row['before']=q.observe(row['taskId']);q.response(d,msg);q.complete(row,d);row['after']=q.observe(row['taskId']);q.record(row,{'codeAscending':d.agent==min(x.agent for x in q.devices[:2]),'completed':row['after']['task']['status']=='COMPLETED'})
 q.run('tie',tie)
 def stale_offline():
  q.reset();q.devices[1].configure(online='OFFLINE');row=q.submit('offline-before-accept-callback');d,msg=q.wait_message(row);row['before']=q.observe(row['taskId']);d.configure(online='OFFLINE');row['responseAfterOffline']=q.response(d,msg);time.sleep(.2);row['after']=q.observe(row['taskId']);q.record(row,{'noBusinessTransport':not any(x['message']['commandType']=='EXECUTE_CAPABILITY' for x in d.messages_for(row['after']['task']['taskCode'])),'exceptionPath':bool(row['after']['exceptions']),'notExecutingOffline':row['after']['task']['status'] in ['PENDING_MANUAL','FAILED']});q.terminate(row)
 q.run('offline-before-callback',stale_offline)
 def baseline():
  q.reset();a=q.devices[0]
  body={'templateName':'G157 F016 baseline control','templateIntent':q.family,'inputParams':copy.deepcopy(q.definitionBody['sceneParams']),'steps':[{'capabilityType':'CAP_NAVIGATION','paramMapping':[{'target':'targetLocation','source':'TEMPLATE_INPUT.targetLocation'}],'stepTimeout':60,'completionCondition':'routeGenerated=true'}]}
  t=q.cfg('/baseline-templates','POST',body);q.templates.append(t['id']);q.save()
  res=q.cfg(f"/baseline-templates/{t['id']}/dry-run",'POST',{'inputParams':{'targetLocation':'F2_TEST_GATE'},'simulatedDevices':[{'stepSeq':1,'agentId':a.agent}]})
  row={'name':'baseline-real-dry-run','taskId':res['taskId'],'response':res};q.tasks.append(res['taskId']);q.ev['cases'].append(row);q.save()
  d,msg=q.wait_message(row);q.response(d,msg);q.complete(row,d);row['after']=q.observe(row['taskId']);q.record(row,{'completed':row['after']['task']['status']=='COMPLETED','isDryRun':row['after']['task']['isDryRun'] is True})
  q.cfg(f"/baseline-templates/{t['id']}/enable",'POST')
  q.reset();row=q.submit('baseline-downgrading-match',high=True);d,msg=q.wait_message(row);row['beforeAcceptance']=q.observe(row['taskId']);q.response(d,msg);q.complete(row,d);row['after']=q.observe(row['taskId']);q.record(row,{'baselineSelected':any(v['source']=='BASELINE_TEMPLATE' for v in row['after']['plans']),'downgradingBeforeAccept':row['beforeAcceptance']['task']['status']=='DOWNGRADING','completed':row['after']['task']['status']=='COMPLETED','onlyTaskAcceptBeforeResponse':all(c['command_type']=='TASK_ACCEPT' for c in row['beforeAcceptance']['commandRows'])})
  q.cfg(f"/baseline-templates/{t['id']}/disable",'POST')
 q.run('baseline',baseline)
 def input_coords():
  q.reset()
  for d in q.devices:
   c=next(c for c in q.cfg(f'/devices/{d.code}/capabilities') if c['capabilityCode']=='CAP_NAVIGATION')
   body={k:c[k] for k in ['capabilityName','inputParams','outputParams','capabilityDescription']}
   body['inputParams']+= [{'name':key,'type':'Double','required':False,'defaultValue':0} for key in ['targetX','targetY']]
   q.cfg(f'/devices/{d.code}/capabilities/CAP_NAVIGATION','PUT',body);d.configure();q.cfg(f'/devices/{d.code}/capabilities/CAP_NAVIGATION/test','POST');q.cfg(f'/devices/{d.code}/capabilities/CAP_NAVIGATION/status','POST',{'status':'ENABLED'})
  q.devices[0].configure(x=3,y=4);q.devices[1].configure(x=0,y=0);q.devices[2].configure(online='OFFLINE')
  row=q.submit('distance-from-input-params',[m.p.step(params={'targetLocation':'F2_TEST_GATE','targetX':0,'targetY':0})]);d,msg=q.wait_message(row);row['before']=q.observe(row['taskId']);q.response(d,msg);q.complete(row,d);row['after']=q.observe(row['taskId']);q.record(row,{'selectedNearestB':d.agent==q.devices[1].agent,'completed':row['after']['task']['status']=='COMPLETED'})
 q.run('input-coordinates',input_coords)
finally:
 for r in q.ev['rulesBefore']:
  if r['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':r['enabled']})
 q.ev['rulesAfter']=q.cfg('/risk-rules')
 for t in q.templates:
  try:
   if q.cfg(f'/baseline-templates/{t}')['templateStatus']=='ENABLED':q.cfg(f'/baseline-templates/{t}/disable','POST')
  except Exception:pass
 q.cleanup();q.ev['endedAt']=m.now();q.save()
