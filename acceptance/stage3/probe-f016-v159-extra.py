"""Baseline all-rejected timing and HTTP replay controls.
The autonomous all-rejected observation legitimately invoked one 5.5.3 replan;
the baseline control makes the terminal timing/UI observation unambiguous.
"""
import importlib.util,json,copy,time,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('v159',Path(__file__).with_name('probe-f016-v159.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
main=json.loads((R/'acceptance/stage3/evidence/SRS_F016-V1.159-http-20261105.json').read_text(encoding='utf-8'))
m.OUT=R/('acceptance/stage3/evidence/SRS_F016-V1.159-baseline-final-20261105.json' if '--baseline-only' in sys.argv else 'acceptance/stage3/evidence/SRS_F016-V1.159-extra-20261105.json');q=m.Probe();q.setup();before=q.cfg('/risk-rules');q.ev['rulesBefore']=before;q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
try:
 def all_rejected():
  q.family=next(r for r in main['cases'] if r['name']=='all-reject')['request']['taskFamily'];definition=main['definitionIds'][0];template=main['templateIds'][0];q.definitions.append(definition);q.templates.append(template);q.save();q.cfg(f'/task-definitions/{definition}/enable','POST');q.reset();res=q.cfg(f'/baseline-templates/{template}/dry-run','POST',{'inputParams':{'targetLocation':'F2_TEST_GATE'},'simulatedDevices':[{'stepSeq':1,'agentId':q.devices[0].agent}]})
  trial={'name':'baseline-retrial-after-disable','taskId':res['taskId']};q.tasks.append(res['taskId']);q.ev['cases'].append(trial);d,msg=q.wait_message(trial);q.response(d,msg);q.complete(trial,d);trial['after']=q.observe(trial['taskId']);q.record(trial,{'genuinePass':trial['after']['task']['status']=='COMPLETED'});q.cfg(f'/baseline-templates/{template}/enable','POST')
  q.reset();q.devices[0].configure(match=1);q.devices[1].configure(match=.9);row=q.submit('baseline-all-reject',high=True);d,msg=q.wait_message(row);row['firstReject']=q.response(d,msg,False);d2,msg2=q.wait_message(row,device=q.devices[1]);row['lastReject']=q.response(d2,msg2,False);row['after']=q.observe(row['taskId']);o=row['after']
  q.record(row,{'callback200':row['lastReject']['http']==200,'manual':o['task']['status']=='PENDING_MANUAL','noReplan':not o['task']['replanUsed'],'twoRequests':sum(c['command_type']=='TASK_ACCEPT' for c in o['commandRows'])==2,'twoRejectedEvents':sum(e['eventType']=='AGENT_REJECTED' for e in o['events'])==2,'failedEvent':any(e['eventType']=='STEP_ASSIGNMENT_FAILED' and e['reasonCode']=='ERR_ALL_CANDIDATES_REJECTED' for e in o['events']),'assignmentFailedPersisted':any(e['exception_type']=='ASSIGNMENT_FAILED' for e in o['exceptions']),'timingPersisted':all(a['acceptanceDurationMs'] is not None and a['acceptedAt'] and a['acceptanceRequestedAt'] for a in o['assignments']),'noBusiness':not any(c['command_type']=='EXECUTE_CAPABILITY' for c in o['commandRows'])});q.cfg(f'/baseline-templates/{template}/disable','POST')
 if '--reproduce-template-prep-error' in sys.argv:q.run('baseline-all-rejected',all_rejected)
 def replay():
  q.reset();row=q.submit('identical-http-replays');d,msg=q.wait_message(row);d.state['workStatus']='BUSY'
  body={'reportType':'TASK_RESPONSE','reportedAt':m.now(),'response':{'commandId':msg['commandId'],'accepted':True}};url=f'http://127.0.0.1:18129/device-api/v1/agents/{d.agent}/report';row['acceptFirst']=m.l.request(url,'POST',body,token=d.token);row['acceptReplay']=m.l.request(url,'POST',body,token=d.token);row['afterAcceptedReplay']=q.observe(row['taskId'])
  d,exe=q.wait_message(row,'EXECUTE_CAPABILITY',d);body={'reportType':'EXECUTION_FEEDBACK','reportedAt':m.now(),'feedback':{'commandId':exe['commandId'],'attemptNo':exe['attemptNo'],'executionResult':'SUCCESS','outputParams':{'routeGenerated':True}}};row['feedbackFirst']=m.l.request(url,'POST',body,token=d.token);row['feedbackReplay']=m.l.request(url,'POST',body,token=d.token);d.state['workStatus']='IDLE';row['after']=q.observe(row['taskId']);o=row['after']
  q.record(row,{'completed':o['task']['status']=='COMPLETED','oneExecution':sum(c['command_type']=='EXECUTE_CAPABILITY' for c in o['commandRows'])==1,'oneAcceptedEvent':sum(e['eventType']=='AGENT_ASSIGNED' for e in o['events'])==1,'oneCompletedEvent':sum(e['eventType']=='STEP_COMPLETED' for e in o['events'])==1,'timingStable':row['afterAcceptedReplay']['assignments'][0]['acceptanceDurationMs']==o['assignments'][0]['acceptanceDurationMs']})
 if '--baseline-only' not in sys.argv:q.run('HTTP replay',replay)
finally:
 for r in before:
  if r['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':r['enabled']})
 q.ev['rulesAfter']=q.cfg('/risk-rules')
 for t in q.templates:
  try:
   if q.cfg(f'/baseline-templates/{t}')['templateStatus']=='ENABLED':q.cfg(f'/baseline-templates/{t}/disable','POST')
  except Exception:pass
 q.cleanup();q.ev['endedAt']=m.now();q.save()
