"""Independent remaining call site: high-risk local replan falls back to baseline tail.
Actual prefix completed, actual recovery exhausted; no SQL-synthesized task lifecycle.
"""
import os,importlib.util,json,time,copy
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='replan-baseline'
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('r',P/'probe-f022-v177-round.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q;h=r.h;m=r.m
def st(seq=1):return h.st(seq,timeout=600,inputParams={'targetLocation':'F2_ZONE_A'})
def new(name,target):
 h.reset();marker='F177_'+name.upper().replace('-','_');q.cases[marker]={'steps':[st(1),st(2)],'goalCompletion':'routeGenerated=true','replanSteps':[st()],'replanConfidence':.79,'replanDiverse':True};(r.R/'.local-test/f022-v177-cases.json').write_bytes(json.dumps(q.cases).encode('utf8'))
 body={'taskGoal':marker+' Synthetic passenger guidance F2_ZONE_A','taskFamily':q.family,'sceneParams':{'targetLocation':'F2_ZONE_A','fallbackLocation':target}};ret=r.raw(q.op,'/tasks',body);tid=int(m.sql(f'select id from {m.SC}.tasks where task_goal={m.lit(body["taskGoal"])} order by id desc limit 1'));row={'name':name,'taskId':tid,'request':body,'response':ret};q.tasks.append(tid);q.ev['cases'].append(row);q.save();return row
def main():
 try:
  q.setup();b=r.payload(q.definitionBody);b['sceneParams']=[{'name':'targetLocation','type':'String','required':True},{'name':'fallbackLocation','type':'String','required':True}];q.cfg(f'/task-definitions/{q.definitions[0]}','PUT',b);q.definitionBody.update(b);h.reset()
  t=q.cfg('/baseline-templates','POST',{'templateName':'G177 replan baseline '+str(time.time_ns()),'templateIntent':q.family,'inputParams':b['sceneParams'],'steps':[{'capabilityType':'CAP_NAVIGATION','paramMapping':[{'target':'targetLocation','source':'TEMPLATE_INPUT.'+name}],'stepTimeout':600,'completionCondition':'routeGenerated=true'} for name in ['targetLocation','fallbackLocation']]});q.templates.append(t['id']);q.save()
  ret=q.cfg(f'/baseline-templates/{t["id"]}/dry-run','POST',{'inputParams':{'targetLocation':'F2_ZONE_A','fallbackLocation':'F2_TEST_GATE'},'simulatedDevices':[{'stepSeq':1,'agentId':q.devices[0].agent},{'stepSeq':2,'agentId':q.devices[0].agent}]});row={'name':'replan-baseline-two-step-trial','taskId':ret['taskId'],'templateId':t['id'],'response':ret};q.tasks.append(row['taskId']);q.ev['cases'].append(row);q.save();o=h.finish(row);row['trialResult']=q.cfg(f'/baseline-templates/{t["id"]}/dry-runs/{row["taskId"]}');r.record(row,{'completed':o['task']['status']=='COMPLETED','trialPassed':row['trialResult']['result']=='SUCCESS'});q.cfg(f'/baseline-templates/{t["id"]}/enable','POST')
  b['constraintDescription']='禁止前往F2_TEST_GATE；仅允许前往F2_ZONE_A。';q.cfg(f'/task-definitions/{q.definitions[0]}','PUT',b)
  for name,target,allowed in [('replan-baseline-allowed-tail','F2_ZONE_A',True),('replan-baseline-prohibited-tail','F2_TEST_GATE',False)]:
   row=new(name,target);row['definition']=q.cfg(f'/task-definitions/{q.definitions[0]}');dev,msg=h.accept(row);h.feed(row,dev,msg);r.capture(row,'completedPrefix');dev,msg=h.accept(row);h.failtwice(row,dev,msg);backup,msg=h.accept(row);h.failtwice(row,backup,msg);o=r.capture(row,'afterFallback')
   checks={'realReplan':any(e['eventType']=='REPLANNING_TRIGGERED' for e in o['events']),'baselineTailVersion':any(p['source']=='BASELINE_TEMPLATE' for p in o['plans']),'prefixStillCompleted':any(a['stepSeq']==1 and a['stepStatus']=='COMPLETED' for a in o['assignments'])}
   if allowed:
    end=h.finish(row);checks.update(completed=end['task']['status']=='COMPLETED',baselineConstraintPass=any(p['source']=='BASELINE_TEMPLATE' and p['constraintCheckResult']=='PASS' for p in end['plans']))
   else:
    if o['task']['status'] in ['DOWNGRADING','PENDING_ASSIGNMENT','EXECUTING']:
     dev,msg=h.accept(row);row['unexpectedBaselineTailExecute']=msg
    end=r.capture(row);checks.update(prohibitedTailRejected=any(p['source']=='BASELINE_TEMPLATE' and p['constraintCheckResult']=='FAIL' for p in end['plans']),prohibitedBaselineUnfrozen=all(not p['frozenAt'] for p in end['plans'] if p['source']=='BASELINE_TEMPLATE'),noProhibitedTailCommand=not any(c['command_type']=='EXECUTE_CAPABILITY' and 'F2_TEST_GATE' in json.dumps(c) for c in end['commandRows']))
   r.record(row,checks);q.terminate(row)
 finally:
  for tid in q.templates:
   try:q.cfg(f'/baseline-templates/{tid}/disable','POST')
   except Exception as ex:q.ev['diagnostics'].append({'templateCleanup':tid,'error':str(ex)})
  q.cleanup();q.ev['endedAt']=m.now();q.save()
if __name__=='__main__':main()
