"""Exact envelope retry, preserving reportedAt (part of protocol idempotency hash).
653 changed reportedAt and was rightly rejected400; not a product failure.
"""
import os,importlib.util
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='exact-replay'
s=importlib.util.spec_from_file_location('r',Path(__file__).with_name('probe-f019-v169-round.py'));r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q;h=r.h
def test():
 h.reset()
 for d in q.devices:d.stable_callback_clock=True
 row=q.submit('exact-leading-replay',[h.st(),h.st(2),h.st(3),h.st(4)]);h.cfgcase(row,replanSteps=r.condition_tail(3));d,msg=r.prefix(row,2);h.failtwice(row,d,msg);b,cmd=h.accept(row);h.failtwice(row,b,cmd);r.capture(row,'beforeReplay');retry=next(mm for dd,mm in h.msgs(row,'EXECUTE_CAPABILITY') if dd==b and mm['commandId']==cmd['commandId'] and mm['attemptNo']==1);h.feed(row,b,retry,'FAILED','ERR_SYNTHETIC_HARDWARE');h.finish(row);o=r.capture(row);row['exactReplayReportedAt']=b.callback_times[(retry['commandId'],1)];row['modelObservations']=[x for x in r.model_rows(row) if x['phase']=='planning' and any('仅替换步骤' in c for c in x['request'].get('constraints',[]))];q.record(row,{'exactReplayAll200':all(f['response']['http']==200 for f in row['feedbacks']),'exactlyOneModelReplan':len(row['modelObservations'])==1,'consumedQuotaAndTwoPlans':o['task']['replanUsed'] and len(o['plans'])==2,'completedFiveActions':o['task']['status']=='COMPLETED' and sum(c['command_type']=='EXECUTE_CAPABILITY' and c['command_status']=='SUCCEEDED' for c in o['commandRows'])==5})
try:
 q.setup();q.ev['rulesBefore']=q.cfg('/risk-rules');q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False});q.run('exact-replay',test)
finally:
 for rule in q.ev.get('rulesBefore',[]):
  if rule['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':rule['enabled']})
 q.cleanup();q.ev['endedAt']=r.m.now();q.save()
