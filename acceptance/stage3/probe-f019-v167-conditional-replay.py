"""Reproduce conditional-tail rollback and retry same failed device callback.
Preserve server404 as product behavior after persisted command and SQL gates.
"""
import os,importlib.util,time
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='conditional-replay'
s=importlib.util.spec_from_file_location('r',Path(__file__).with_name('probe-f019-v167-round.py'));r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q;h=r.h;m=r.m
def case():
 h.reset();row=q.submit('conditional-replay',[h.st(),h.st(2),h.st(3),h.st(4)]);h.cfgcase(row,replanSteps=r.condition_tail(3));d,msg=r.prefix(row,2);h.failtwice(row,d,msg);r.capture(row,'candidateSwitch');b,cmd=h.accept(row);h.failtwice(row,b,cmd);r.capture(row,'afterFirstFailure')
 retry=h.wait(lambda:next((mm for dd,mm in h.msgs(row,'EXECUTE_CAPABILITY') if dd==b and mm['commandId']==cmd['commandId'] and mm['attemptNo']==1),None));row['durableAttemptBeforeReplay']=m.rows(f"select c.* from {m.SC}.device_commands c where command_id={m.lit(retry['commandId'])} and attempt_no=1")
 h.feed(row,b,retry,'FAILED','ERR_SYNTHETIC_HARDWARE');o=r.capture(row);row['replanModelCalls']=r.model_rows(row);calls=[x for x in row['replanModelCalls'] if x['phase']=='planning' and any('仅替换步骤' in c for c in x['request'].get('constraints',[]))]
 q.record(row,{'validConditionalTailAccepted':len(o['plans'])==2,'newFiveActionPlanCommitted':len(o['plans'][-1]['planSteps'])==5,'failureCallbackHttp200':all(f['response']['http']==200 for f in row['feedbacks']),'atMostOneReplanModelCall':len(calls)<=1,'opportunityConsumedAfterModelCall':bool(o['task']['replanUsed']),'failedReplanningIsManualOrContinuesNewPlan':o['task']['status']=='PENDING_MANUAL' or (len(o['plans'])==2 and o['task']['currentPlanVersionId']==o['plans'][-1]['id']),'prefixPreserved':all(any(a['id']==old['id'] and a==old for a in o['allAssignments']) for old in row['prefix']['allAssignments'] if old['step_status']=='COMPLETED')})
try:
 q.setup();q.ev['rulesBefore']=q.cfg('/risk-rules');q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False});q.run('conditional-replay',case)
finally:
 for rule in q.ev.get('rulesBefore',[]):
  if rule['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':rule['enabled']})
 q.cleanup();q.ev['endedAt']=m.now();q.save()
