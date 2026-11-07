"""F022 shared-validator baseline dependency, after primary adapter process exits.
Correctly uses only mapped required template input; own new definition and template.
"""
import os,importlib.util,json,time
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='baseline'
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('r',P/'probe-f022-v177-round.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q;h=r.h;m=r.m;R=r.R
def constraint(text):
 body=r.payload(q.definitionBody);body['constraintDescription']=text;q.cfg(f'/task-definitions/{q.definitions[0]}','PUT',body)
def main():
 try:
  q.setup();h.reset()
  body={'templateName':'G177 mapped baseline '+str(time.time_ns()),'templateIntent':q.family,'inputParams':[{'name':'targetLocation','type':'String','required':True,'range':'synthetic destination'}],'steps':[{'capabilityType':'CAP_NAVIGATION','paramMapping':[{'target':'targetLocation','source':'TEMPLATE_INPUT.targetLocation'}],'stepTimeout':600,'completionCondition':'routeGenerated=true'}]}
  t=q.cfg('/baseline-templates','POST',body);q.templates.append(t['id']);q.save();ret=q.cfg(f"/baseline-templates/{t['id']}/dry-run",'POST',{'inputParams':{'targetLocation':'F2_TEST_GATE'},'simulatedDevices':[{'stepSeq':1,'agentId':q.devices[0].agent}]})
  row={'name':'baseline-publication-trial','taskId':ret['taskId'],'templateId':t['id'],'request':body,'response':ret};q.tasks.append(row['taskId']);q.ev['cases'].append(row);q.save();o=h.finish(row);row['trialResult']=q.cfg(f"/baseline-templates/{t['id']}/dry-runs/{row['taskId']}");r.record(row,{'completed':o['task']['status']=='COMPLETED','actualTrialSuccess':row['trialResult']['result']=='SUCCESS'});q.cfg(f"/baseline-templates/{t['id']}/enable",'POST')
  for name,text,expected in [('baseline-location-allowed','仅允许前往F2_TEST_GATE。',True),('baseline-location-prohibited','禁止前往F2_TEST_GATE；仅允许前往F2_ZONE_A。',False)]:
   constraint(text);row=r.new(name,[h.st(timeout=600)],scene={'targetLocation':'F2_TEST_GATE'},planHttpStatus=503);row['definition']=q.cfg(f'/task-definitions/{q.definitions[0]}');h.wait(lambda:q.op(f"/tasks/{row['taskId']}")['status'] in ['DOWNGRADING','PENDING_ASSIGNMENT','EXECUTING','PENDING_MANUAL','FAILED','COMPLETED']);o=r.capture(row,'beforeDevice')
   if expected:
    end=h.finish(row);checks={'baselineSource':any(p['source']=='BASELINE_TEMPLATE' for p in end['plans']),'completed':end['task']['status']=='COMPLETED','validationPass':any(p['source']=='BASELINE_TEMPLATE' and p['constraintCheckResult']=='PASS' for p in end['plans'])}
   else:
    if o['task']['status'] in ['DOWNGRADING','PENDING_ASSIGNMENT']:d,msg=h.accept(row);row['unexpectedExecute']=msg
    end=r.capture(row);checks={'baselineHardConstraintFail':any(p['source']=='BASELINE_TEMPLATE' and p['constraintCheckResult']=='FAIL' for p in end['plans']),'definitionReason':'ERR_TASK_DEFINITION_CONSTRAINT' in json.dumps(end),'noFrozen':all(not p['frozenAt'] for p in end['plans']),'noExecute':not any(c['command_type']=='EXECUTE_CAPABILITY' for c in end['commandRows'])}
   r.record(row,checks);q.terminate(row)
 finally:
  for tid in q.templates:
   try:q.cfg(f'/baseline-templates/{tid}/disable','POST')
   except Exception as ex:q.ev['diagnostics'].append({'templateCleanup':tid,'error':str(ex)})
  q.cleanup();q.ev['endedAt']=m.now();q.save()
if __name__=='__main__':main()
