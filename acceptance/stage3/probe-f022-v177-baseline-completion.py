"""Fill baseline execution assertions after probe incorrectly excluded DOWNGRADING.
Retains prior trial. Since cleanup disabled the template, reactivation requires a new
successful trial under the existing template state machine; this is recorded explicitly.
"""
import os,importlib.util,json
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='baseline-completion'
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('r',P/'probe-f022-v177-round.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q;h=r.h;m=r.m
old=json.loads((P/'evidence/SRS_F022-V1.177-http-20261107-baseline.json').read_text(encoding='utf8'))
def main():
 try:
  q.setup();did=old['definitionIds'][0];tid=old['templateIds'][0];d=q.cfg(f'/task-definitions/{did}');q.family=d['definitionCode'];q.definitionBody=dict(r.payload(d),taskName=d['taskName']);q.definitions.append(did);q.templates.append(tid);q.cfg(f'/task-definitions/{did}/enable','POST')
  ret=q.cfg(f'/baseline-templates/{tid}/dry-run','POST',{'inputParams':{'targetLocation':'F2_TEST_GATE'},'simulatedDevices':[{'stepSeq':1,'agentId':q.devices[0].agent}]});trial={'name':'baseline-reactivation-required-trial','taskId':ret['taskId'],'response':ret,'templateId':tid};q.tasks.append(trial['taskId']);q.ev['cases'].append(trial);q.save();o=h.finish(trial);trial['trialResult']=q.cfg(f'/baseline-templates/{tid}/dry-runs/{trial["taskId"]}');r.record(trial,{'completed':o['task']['status']=='COMPLETED','trialPassed':trial['trialResult']['result']=='SUCCESS'});q.cfg(f'/baseline-templates/{tid}/enable','POST')
  q.ev['fixtureCorrection']={'source':'SRS_F022-V1.177-http-20261107-baseline.json','reason':'Previous publication trial passed; allowed task entered normal DOWNGRADING but the wait predicate excluded this legitimate baseline state and timed out. Original evidence retained. Subsequent cleanup disabled template, so direct re-enable was correctly rejected; new reactivation trial is necessary under current state machine.','successfulTrialTaskId':old['cases'][0]['taskId'],'priorIncompleteTaskId':old['cases'][1]['taskId'],'reactivationTrialTaskId':trial['taskId']};q.save()
  for name,text,expected in [('baseline-allowed-complete','仅允许前往F2_TEST_GATE。',True),('baseline-prohibited-complete','禁止前往F2_TEST_GATE；仅允许前往F2_ZONE_A。',False)]:
   body=r.payload(q.definitionBody);body['constraintDescription']=text;q.cfg(f'/task-definitions/{did}','PUT',body);row=r.new(name,[h.st(timeout=600)],scene={'targetLocation':'F2_TEST_GATE'},planHttpStatus=503);row['definition']=q.cfg(f'/task-definitions/{did}');h.wait(lambda:q.op(f"/tasks/{row['taskId']}")['status'] in ['DOWNGRADING','PENDING_ASSIGNMENT','EXECUTING','PENDING_MANUAL','FAILED','COMPLETED']);o=r.capture(row,'beforeDevice')
   if expected:
    end=h.finish(row);checks={'baselineSource':any(p['source']=='BASELINE_TEMPLATE' for p in end['plans']),'completed':end['task']['status']=='COMPLETED','constraintPass':any(p['source']=='BASELINE_TEMPLATE' and p['constraintCheckResult']=='PASS' for p in end['plans'])}
   else:
    if o['task']['status'] in ['DOWNGRADING','PENDING_ASSIGNMENT']:dev,msg=h.accept(row);row['unexpectedExecute']=msg
    end=r.capture(row);checks={'baselineConstraintFail':any(p['source']=='BASELINE_TEMPLATE' and p['constraintCheckResult']=='FAIL' for p in end['plans']),'definitionReason':'ERR_TASK_DEFINITION_CONSTRAINT' in json.dumps(end),'notFrozen':all(not p['frozenAt'] for p in end['plans']),'noExecute':not any(c['command_type']=='EXECUTE_CAPABILITY' for c in end['commandRows'])}
   r.record(row,checks);q.terminate(row)
 finally:
  for tid in q.templates:
   try:q.cfg(f'/baseline-templates/{tid}/disable','POST')
   except Exception as ex:q.ev['diagnostics'].append({'templateCleanup':tid,'error':str(ex)})
  q.cleanup();q.ev['endedAt']=m.now();q.save()
if __name__=='__main__':main()
