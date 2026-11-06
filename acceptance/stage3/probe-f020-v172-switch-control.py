"""Complete the missing synthetic callback for browser baseline action.
Original single-slot command file was overwritten by subsequent refresh command;
retain original task/trace and use an acknowledged isolated callback control.
"""
import os,importlib.util,json,time
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='switch-control';P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('r',P/'probe-f020-v172-round.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q;m=r.m;R=r.R
try:
 q.setup();q.ev['rulesBefore']=q.cfg('/risk-rules');q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
 row=r.pending('ui-switch-acknowledged');t=r.baseline();(R/'.local-test/f020-v172-switch-ready.json').write_text(json.dumps({'taskId':row['taskId']}))
 while not (R/'.local-test/f020-v172-switch-ack').exists():time.sleep(.2)
 mid=r.capture(row,'afterBrowserAction');end=r.finish(row);r.record(row,{'actualBaselineSource':end['plans'][-1]['source']=='BASELINE_TEMPLATE','threeValidatorsPass':all(end['plans'][-1][x]=='PASS' for x in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']),'resumedThenCompleted':mid['task']['status']=='DOWNGRADING' and end['task']['status']=='COMPLETED',**r.logchecks(end,'F172 acknowledged browser switch reason')})
 (R/'.local-test/f020-v172-switch-done').write_text('done')
finally:
 for t in q.templates:
  try:q.cfg(f'/baseline-templates/{t}/disable','POST')
  except Exception:pass
 for x in q.ev.get('rulesBefore',[]):
  if x['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':x['enabled']})
 q.cleanup();q.ev['endedAt']=m.now();q.save()
