"""Independent boundaries for F018: false predicate, forbidden skip and assignment gap.
Only owned schema and synthetic protocol devices. No product source changes.
"""
import os,importlib.util,json,time
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='boundaries'
R=Path(__file__).resolve().parents[2];s=importlib.util.spec_from_file_location('h',Path(__file__).with_name('probe-f018-v165-helpers.py'));h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
q=h.q;m=h.m

def gap():
 h.reset();row=q.submit('capability-gap-assignment-boundary',[h.st(),h.st(2)]);h.cfgcase(row,replanHttpStatus=503);d,msg=h.accept(row)
 row['injection']='Scoped own NAV capabilities disabled by SQL after plan validation, before next synchronous allocation; not public API reachability.'
 row['beforeInjection']=m.rows(f"select c.* from {m.SC}.device_capabilities c join {m.SC}.devices d on d.id=c.device_id where d.device_code like 'G160_F016_%' and c.capability_code='CAP_NAVIGATION'")
 m.sql(f"update {m.SC}.device_capabilities set capability_status='DISABLED' where device_id in (select id from {m.SC}.devices where device_code like 'G160_F016_%') and capability_code='CAP_NAVIGATION'")
 h.feed(row,d,msg);o=h.obs(row);q.record(row,{'gapRecorded':any(e['exception_type']=='CAPABILITY_GAP' for e in o['exceptions']),'noSecondStepCommands':not any(c['step_seq']==2 for c in o['commandRows']),'oneReplanThenManual':o['task']['replanUsed'] and o['task']['status']=='PENDING_MANUAL','archived':all(e['exception_status']=='RESOLVED' for e in o['exceptions'])});h.reset()

def false_goal():
 h.reset();old=q.family;body=dict(q.definitionBody,taskName='G165 false goal '+str(time.time_ns()),completionCondition='routeGenerated=false');de=q.cfg('/task-definitions','POST',body);q.definitions.append(de['id']);q.cfg(f"/task-definitions/{de['id']}/enable",'POST');q.family=de['definitionCode'];q.save()
 try:
  row=q.submit('noncritical-false-goal',[h.st(completionCondition='routeGenerated=false'),h.st(2,completionCondition='routeGenerated=false',failureHandling='非关键步骤，失败可跳过，原目标已满足时继续'),h.st(3,completionCondition='routeGenerated=false')]);h.cfgcase(row,replanSteps=[h.st(completionCondition='routeGenerated=false')]);d,msg=h.accept(row);h.feed(row,d,msg,output={'routeGenerated':False});h.obs(row,'prefix');d,msg=h.accept(row);h.failtwice(row,d,msg);b,cmd=h.accept(row);h.failtwice(row,b,cmd);mid=h.obs(row,'afterExhaustion')
  if not mid['task']['replanUsed'] and mid['task']['status'] not in ['COMPLETED','FAILED','PENDING_MANUAL']:
   d,msg=h.accept(row);h.feed(row,d,msg,output={'routeGenerated':False})
  o=h.obs(row);q.record(row,{'prefixActuallySatisfiedFalse':any(a['stepSeq']==1 and a['stepStatus']=='COMPLETED' and a.get('outputParams',{}).get('routeGenerated') is False for a in row['prefix']['assignments']),'noReplanForSatisfiedFalseGoal':not o['task']['replanUsed'],'optionalSkipped':any(a['stepSeq']==2 and a['stepStatus']=='SKIPPED' for a in o['assignments']),'originalVersionCompletes':len(o['plans'])==1 and o['task']['status']=='COMPLETED'})
 finally:q.family=old

def prohibited_skip():
 h.reset();row=q.submit('critical-prohibited-skip',[h.st(),h.st(2,failureHandling='关键步骤，不可跳过；恢复失败必须重规划或转人工'),h.st(3)]);h.cfgcase(row,replanSteps=[h.st()]);d,msg=h.prefix(row);h.failtwice(row,d,msg);b,cmd=h.accept(row);h.failtwice(row,b,cmd);o=h.obs(row)
 q.record(row,{'notSkipped':not any(a['stepSeq']==2 and a['stepStatus']=='SKIPPED' for a in o['assignments']),'criticalFailureUsesReplan':o['task']['replanUsed'] and bool(h.event(o,'REPLANNING_TRIGGERED')),'noFalseContinuability':not h.event(o,'PLAN_CONTINUATION_JUDGED')})

def last_optional():
 h.reset();row=q.submit('last-noncritical',[h.st(),h.st(2,failureHandling='非关键，可跳过，目标已满足时允许结束')]);d,msg=h.prefix(row);h.failtwice(row,d,msg);b,cmd=h.accept(row);h.failtwice(row,b,cmd);o=h.obs(row)
 q.record(row,{'completed':o['task']['status']=='COMPLETED','noReplan':not o['task']['replanUsed'],'optionalSkipped':any(a['stepSeq']==2 and a['stepStatus']=='SKIPPED' for a in o['assignments']),'allArchived':all(e['exception_status']=='RESOLVED' for e in o['exceptions']),'noOccupancy':all(a['current_task_id']!=row['taskId'] for a in o['agentRows'])})
def prohibited_words(label,policy):
 h.reset();row=q.submit('prohibited-'+label,[h.st(),h.st(2,failureHandling=policy),h.st(3)]);h.cfgcase(row,replanSteps=[h.st()]);d,msg=h.prefix(row);h.failtwice(row,d,msg);b,cmd=h.accept(row);h.failtwice(row,b,cmd);o=h.obs(row)
 q.record(row,{'explicitProhibitionNotSkipped':not any(a['stepSeq']==2 and a['stepStatus']=='SKIPPED' for a in o['assignments']),'prohibitionUsesReplan':o['task']['replanUsed'] and bool(h.event(o,'REPLANNING_TRIGGERED')),'noFalseContinuability':not h.event(o,'PLAN_CONTINUATION_JUDGED')})

def numeric_goal():
 h.reset();old=q.family;body=dict(q.definitionBody,taskName='G165 numeric goal '+str(time.time_ns()),completionCondition='waypointCount=2');de=q.cfg('/task-definitions','POST',body);q.definitions.append(de['id']);q.cfg(f"/task-definitions/{de['id']}/enable",'POST');q.family=de['definitionCode'];q.save()
 try:
  row=q.submit('noncritical-numeric-goal',[h.st(completionCondition='waypointCount=2'),h.st(2,completionCondition='waypointCount=2',failureHandling='可选步骤，恢复失败允许跳过'),h.st(3,completionCondition='waypointCount=2')]);h.cfgcase(row,replanSteps=[h.st(completionCondition='waypointCount=2')]);d,msg=h.accept(row);h.feed(row,d,msg,output={'waypointCount':2});h.obs(row,'prefix');d,msg=h.accept(row);h.failtwice(row,d,msg);b,cmd=h.accept(row);h.failtwice(row,b,cmd);mid=h.obs(row,'afterExhaustion')
  if not mid['task']['replanUsed'] and mid['task']['status'] not in ['COMPLETED','FAILED','PENDING_MANUAL']:
   d,msg=h.accept(row);h.feed(row,d,msg,output={'waypointCount':2})
  o=h.obs(row);q.record(row,{'typedNumericPrefixSatisfied':any(a['stepSeq']==1 and a['stepStatus']=='COMPLETED' and a.get('outputParams',{}).get('waypointCount')==2 for a in row['prefix']['assignments']),'noReplan':not o['task']['replanUsed'],'skipped':any(a['stepSeq']==2 and a['stepStatus']=='SKIPPED' for a in o['assignments']),'originalVersionComplete':len(o['plans'])==1 and o['task']['status']=='COMPLETED','allArchived':all(e['exception_status']=='RESOLVED' for e in o['exceptions'])})
 finally:q.family=old

try:
 q.setup();q.ev['rulesBefore']=q.cfg('/risk-rules');q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
 for name,fn in [('gap',gap),('false-goal',false_goal),('prohibited-skip',prohibited_skip),('last-optional',last_optional),('forbidden-word',lambda:prohibited_words('forbidden','禁止跳过；恢复失败需转人工处理')),('must-not-word',lambda:prohibited_words('must-not','不得跳过；异常后应交人工处理')),('numeric-goal',numeric_goal)]:h.run(name,fn)
finally:
 for rule in q.ev.get('rulesBefore',[]):
  if rule['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':rule['enabled']})
 q.cleanup();q.ev['endedAt']=m.now();q.save()
