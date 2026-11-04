"""Finish multi-device/frozen branches after correcting second simulator readiness."""
import importlib.util,json,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('m',ROOT/'acceptance/stage3/probe-f015-v155.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def main():
 original=json.loads(m.OUT.read_text(encoding='utf-8'));assert original.get('finishedAt')
 supplement=ROOT/'acceptance/stage3/evidence/SRS_F015-V1.155-full-round-20261104-supplement.json'
 assert json.loads(supplement.read_text(encoding='utf-8')).get('finishedAt'),'Do not compete with supplement fixture'
 label=sys.argv[1] if len(sys.argv)>1 else 'stable'
 m.OUT=m.OUT.with_stem(m.OUT.stem+'-recovery-'+label);m.STATE=ROOT/f'.local-test/f015-v155-recovery-{label}-state.json';assert not m.OUT.exists()
 q=m.Probe.__new__(m.Probe);q.cfg=m.p.l.API('配置管理员');q.op=m.p.l.API('运行操作员')
 q.templates=[];q.tasks=[];q.definitions=[];q.modelCases={};q.tokens={};q.ports={'G126_ROBOT':18132,'G155_F015_ROBOT_B':18133}
 for code,file in [('G126_ROBOT',ROOT.parent/'tip/.local-test/gpt-f007-v126-robot.dpapi'),('G155_F015_ROBOT_B',ROOT/'.local-test/f015-v155-robot-b.dpapi')]:
  q.tokens[code]=json.loads(m.p.l.protect(file.read_bytes(),True))['token']
 d=original['definition'];q.definitionId=d['id'];q.family=d['definitionCode'];q.definitionBody={k:d[k] for k in ['taskName','goalTemplate','sceneParams','availableCapabilityTypes','constraintDescription','completionCondition']}
 q.ev={'tag':'V1.155','productSha':m.SHA,'executionBaseline':'V2.4','startedAt':m.now(),'timezone':'Asia/Shanghai','schema':m.SC,'redisDb':10,
  'cases':[],'trials':[],'planned':['multi-candidate-recovered','multi-candidate-exhausted','frozen-live-edit','autonomous-replan-neighbor'],
  'rulesBefore':q.cfg('/risk-rules'),'readinessCorrection':'Original connection-test returned HTTP200 with unsuccessful connection before simulator finished starting. Capability test correctly failed with no agent. Now verify actual ONLINE before testing/enabling; no product defect assigned.'}
 q.cfg(f'/task-definitions/{q.definitionId}/enable','POST')
 try:
  connection=q.cfg('/devices/G155_F015_ROBOT_B/connection-test','POST')
  assert connection['result']=='PASSED',connection
  q.cfg('/devices/G155_F015_ROBOT_B/status','POST',{'status':'ACTIVE'})
  for _ in range(80):
   q.cfg('/devices/G155_F015_ROBOT_B/connection-test','POST')
   try:
    if q.agent('G155_F015_ROBOT_B')['onlineStatus']=='ONLINE':break
   except StopIteration:pass
   time.sleep(.5)
  else:raise RuntimeError('B not actually ONLINE')
  q.ev['bCapabilityRetest']=q.cfg('/devices/G155_F015_ROBOT_B/capabilities/CAP_NAVIGATION/test','POST')
  assert q.ev['bCapabilityRetest']['capabilityStatus']=='TESTED_PASSED',q.ev['bCapabilityRetest']
  q.cfg('/devices/G155_F015_ROBOT_B/capabilities/CAP_NAVIGATION/status','POST',{'status':'ENABLED'});q.idle()
  q.ev['agentsBefore']=[q.agent(c) for c in q.ports];q.save();q.second_robot=lambda:None
  q.run('recovery-and-frozen-corrected',q.recovery_and_frozen)
 finally:
  q.cleanup();q.cfg(f'/task-definitions/{q.definitionId}/disable','POST');q.ev['originalDefinitionRestoredDisabled']=True;q.save()

if __name__=='__main__':main()
