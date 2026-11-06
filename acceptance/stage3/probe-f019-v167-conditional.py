"""Finish conditional legal-boundary observation after early callback diagnostics.
The helper waits for persisted command attempts before sending synthetic feedback.
"""
import os,importlib.util
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='conditional'
s=importlib.util.spec_from_file_location('r',Path(__file__).with_name('probe-f019-v167-round.py'));r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q
try:
 q.setup();q.ev['rulesBefore']=q.cfg('/risk-rules');q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
 r.h.run('conditional-durable-callback',lambda:r.run_case('conditional-durable-callback',tail=r.condition_tail(3)))
finally:
 for rule in q.ev.get('rulesBefore',[]):
  if rule['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':rule['enabled']})
 q.cleanup();q.ev['endedAt']=r.m.now();q.save()
