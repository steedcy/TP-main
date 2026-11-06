"""Complete missing F020 switch/template/UI observations after fixture repair.
Disabling a published template invalidates its trial version; do not re-enable
without a fresh trial. Prepare pending tasks before publishing instead.
Initial diagnostics retained; no product repair and no repeat of valid checks.
"""
import os,importlib.util,json,time
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='supplement'
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('r',P/'probe-f020-v171-round.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q;h=r.h;m=r.m;R=r.R;SC=r.SC
def switches(rows,t):
 for row,reason in [(rows['switch-valid'],'F020 valid baseline reason'),(rows['switch-no-reason'],None)]:
  ret=r.act(row,'SWITCH_TO_BASELINE',reason);o=r.capture(row,'afterAction');end=r.finish(row)
  r.record(row,{'action200':ret['http']==200,'baselineSource':o['plans'][-1]['source']=='BASELINE_TEMPLATE','templateIdentity':bool(o['plans'][-1].get('baselineTemplateId')),'threePass':all(o['plans'][-1][x]=='PASS' for x in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']),'resumedAndCompleted':end['task']['status']=='COMPLETED',**r.logchecks(o,reason),'reasonRecordedNonempty':bool(r.auditdetail(o['audit'][-1]).get('reason'))})
 original=m.sql(f"select steps::text from {SC}.baseline_templates where id={t['id']}")
 try:
  for mode in ['structure','capability','constraint']:
   row=rows['switch-reject-'+mode];h.reset();steps=json.loads(original)
   if mode=='structure':steps=[]
   if mode=='capability':steps[0]['capabilityType']='CAP_F020_UNKNOWN'
   if mode=='constraint':steps[0]['paramMapping']=[{'target':'targetLocation','source':'TEMPLATE_INPUT.targetLocation'},{'target':'waypoint','source':'[1,2]'}]
   m.sql(f"update {SC}.baseline_templates set steps={m.lit(json.dumps(steps))}::json where id={t['id']}")
   ret=r.act(row,'SWITCH_TO_BASELINE','F020 invalid baseline '+mode);o=r.capture(row);r.record(row,{'manualRetained':o['task']['status']=='PENDING_MANUAL','noCommands':r.checks_no_commands(o),'failureExplained':bool(o['task']['failureReason']),'validatorRejected':any(p.get(mode+'CheckResult')=='FAIL' for p in o['plans'])});r.finishcase(row)
 finally:m.sql(f"update {SC}.baseline_templates set steps={m.lit(original)}::json where id={t['id']}")
def ui(rows):
 ids={name:row['taskId'] for name,row in rows.items() if name.startswith('ui-')}
 h.reset();row=r.new('ui-refresh',steps=[h.st(timeout=600)]);d,msg=h.accept(row);ids['ui-refresh']=row['taskId'];q.ev['uiFixtures']=ids;q.save();(R/'.local-test/f020-ui-ready.json').write_text(json.dumps(ids))
 while not (R/'.local-test/f020-finish').exists():
  command=R/'.local-test/f020-command.json'
  if command.exists():
   cmd=json.loads(command.read_text());command.unlink();target=next(x for x in q.ev['cases'] if x.get('taskId')==cmd['taskId'])
   if cmd['action']=='complete':
    if cmd['taskId']==row['taskId']:h.feed(row,d,msg)
    else:r.finish(target)
    r.capture(target,'afterBrowserComplete')
  time.sleep(.2)
 for n,tid in ids.items():r.capture(next(x for x in q.ev['cases'] if x.get('taskId')==tid),'afterBrowser')
try:
 q.setup();q.ev['rulesBefore']=q.cfg('/risk-rules');q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
 rows={}
 for name in ['switch-valid','switch-no-reason','switch-reject-structure','switch-reject-capability','switch-reject-constraint','ui-mark-failed','ui-terminate','ui-retry','ui-switch']:
  rows[name]=r.pending(name)
  if name.startswith('ui-'):r.change_model(rows[name])
 t=r.baseline();q.run('switches',lambda:switches(rows,t));q.run('ui',lambda:ui(rows))
finally:
 for tid in q.templates:
  try:q.cfg(f'/baseline-templates/{tid}/disable','POST')
  except Exception:pass
 for rr in q.ev.get('rulesBefore',[]):
  if rr['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':rr['enabled']})
 q.cleanup();q.ev['endedAt']=m.now();q.save()
