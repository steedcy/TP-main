"""Legal conditional plan with an action before condition: contrast for DEF111.
Two completed + three actions, one folded condition; exact same quota as failure.
"""
import os,importlib.util
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='contrast'
s=importlib.util.spec_from_file_location('r',Path(__file__).with_name('probe-f019-v167-round.py'));r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q;h=r.h;m=r.m
try:
 q.setup();q.ev['rulesBefore']=q.cfg('/risk-rules');q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False})
 node={'stepSeq':2,'conditionNode':True,'nodeType':'CONDITION','condition':'routeGenerated=true','stepGoal':'判断已有路径'}
 h.run('action-before-condition',lambda:r.run_case('action-before-condition',tail=[h.st(),node,h.st(3,branchOf=2),h.st(4,branchOf=2)]))
finally:
 for rule in q.ev.get('rulesBefore',[]):
  if rule['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':rule['enabled']})
 q.cleanup();q.ev['endedAt']=m.now();q.save()
