"""Complete assertions blocked by first probe schema lookup errors; retain diagnostics.
Run after round has cleaned its devices. Negative observations are audited separately,
without repeating sufficient same-version HTTP observations.
"""
import os,importlib.util
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='stable'
s=importlib.util.spec_from_file_location('round',Path(__file__).with_name('probe-f019-v167-round.py'));r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q;h=r.h;m=r.m
try:
 q.setup();q.ev['rulesBefore']=q.cfg('/risk-rules');q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
 for name,n,tail,mode in [('stable-normal-three',2,None,'success'),('stable-conditional-three',2,r.condition_tail(3),'success'),('stable-one-remaining',4,None,'success'),('stable-five-remaining',0,None,'success'),('stable-second-failure',2,None,'second-failure')]:h.run(name,lambda name=name,n=n,tail=tail,mode=mode:r.run_case(name,n=n,tail=tail,mode=mode))
 h.run('high-without-template',lambda:r.run_case('high-without-template',mode='no-baseline',replanConfidence=.79,replanDiverse=True))
 q.run('baseline-setup',r.baseline_setup)
 h.run('stable-high-risk',lambda:r.run_case('stable-high-risk',mode='high',replanConfidence=.79,replanDiverse=True))
finally:
 for t in q.templates:
  try:q.cfg(f'/baseline-templates/{t}/disable','POST')
  except Exception:pass
 for rule in q.ev.get('rulesBefore',[]):
  if rule['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':rule['enabled']})
 q.cleanup();q.ev['endedAt']=m.now();q.save()
