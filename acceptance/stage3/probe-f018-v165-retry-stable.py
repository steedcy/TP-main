"""Stable re-run of the interrupted used-quota branch. Serialize owned adapter heartbeat and acceptance state so an older synthetic IDLE cannot overtake BUSY acceptance. No product changes."""
import os,importlib.util,threading
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='retry-stable'
R=Path(__file__).resolve().parents[2];s=importlib.util.spec_from_file_location('h',Path(__file__).with_name('probe-f018-v165-helpers.py'));h=importlib.util.module_from_spec(s);s.loader.exec_module(h);q=h.q;m=h.m
original_init=m.Device.__init__;original_heartbeat=m.Device.heartbeat;original_response=q.response

def init(self,*args,**kw):self.guard=threading.RLock();original_init(self,*args,**kw)
def heartbeat(self):
 with self.guard:return original_heartbeat(self)
def response(d,msg,accepted=True):
 with d.guard:return original_response(d,msg,accepted)
m.Device.__init__=init;m.Device.heartbeat=heartbeat;q.response=response
try:
 q.setup();q.ev['fixtureSequencing']='RLock serializes status heartbeat with TASK_RESPONSE state and HTTP delivery; prevents queued pre-accept IDLE crossing the acceptance boundary.';q.ev['rulesBefore']=q.cfg('/risk-rules');q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':False});h.run('used-quota-stable',lambda:h.exhaustion('second-failure'))
finally:
 for rule in q.ev.get('rulesBefore',[]):
  if rule['ruleCode']=='RULE_RESOURCE_CRITICAL':q.cfg('/risk-rules/RULE_RESOURCE_CRITICAL/update','POST',{'enabled':rule['enabled']})
 q.cleanup();q.ev['endedAt']=m.now();q.save()
