"""Fresh draft->real trial->enable->all reject. No reuse of disabled templates."""
import importlib.util,json,copy
from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('v160',Path(__file__).with_name('probe-f016-v160.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.OUT=R/'acceptance/stage3/evidence/SRS_F016-V1.160-baseline-controls-20261105.json';q=m.Probe();q.setup();before=q.cfg('/risk-rules');q.ev['rulesBefore']=before;q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
try:
 body={'templateName':'G160 all rejected '+m.datetime.now().strftime('%H%M%S'),'templateIntent':q.family,'inputParams':copy.deepcopy(q.definitionBody['sceneParams']),'steps':[{'capabilityType':'CAP_NAVIGATION','paramMapping':[{'target':'targetLocation','source':'TEMPLATE_INPUT.targetLocation'}],'stepTimeout':60,'completionCondition':'routeGenerated=true'}]}
 t=q.cfg('/baseline-templates','POST',body);tid=t['id'];q.templates.append(tid);q.save();q.reset();res=q.cfg(f'/baseline-templates/{tid}/dry-run','POST',{'inputParams':{'targetLocation':'F2_TEST_GATE'},'simulatedDevices':[{'stepSeq':1,'agentId':q.devices[0].agent}]})
 row={'name':'baseline-control-trial','taskId':res['taskId']};q.tasks.append(res['taskId']);q.ev['cases'].append(row);d,msg=q.wait_message(row);q.response(d,msg);q.complete(row,d);row['after']=q.observe(row['taskId']);q.record(row,{'completed':row['after']['task']['status']=='COMPLETED'});q.cfg(f'/baseline-templates/{tid}/enable','POST')
 q.reset();q.devices[0].configure(match=1);q.devices[1].configure(match=.9);row=q.submit('baseline-all-reject',high=True);d,msg=q.wait_message(row);row['firstReject']=q.response(d,msg,False);d2,msg2=q.wait_message(row,device=q.devices[1]);row['lastReject']=q.response(d2,msg2,False);row['after']=q.observe(row['taskId']);o=row['after']
 q.record(row,{'callback200':row['lastReject']['http']==200,'manual':o['task']['status']=='PENDING_MANUAL','noReplan':not o['task']['replanUsed'],'twoRequests':sum(c['command_type']=='TASK_ACCEPT' for c in o['commandRows'])==2,'twoRejectedEvents':sum(e['eventType']=='AGENT_REJECTED' for e in o['events'])==2,'failedEvent':any(e['eventType']=='STEP_ASSIGNMENT_FAILED' and e['reasonCode']=='ERR_ALL_CANDIDATES_REJECTED' for e in o['events']),'assignmentFailedPersisted':any(e['exception_type']=='ASSIGNMENT_FAILED' for e in o['exceptions']),'timingPersisted':all(a['acceptanceDurationMs'] is not None and a['acceptedAt'] and a['acceptanceRequestedAt'] for a in o['assignments']),'noBusiness':not any(c['command_type']=='EXECUTE_CAPABILITY' for c in o['commandRows'])})
finally:
 for r in before:
  if r['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':r['enabled']})
 q.ev['rulesAfter']=q.cfg('/risk-rules')
 for tid in q.templates:
  if q.cfg(f'/baseline-templates/{tid}')['templateStatus']=='ENABLED':q.cfg(f'/baseline-templates/{tid}/disable','POST')
 q.cleanup();q.ev['endedAt']=m.now();q.save()
