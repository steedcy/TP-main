"""Prove the non-exact candidate is truly eligible, completing the ranking contrast."""
import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('m',ROOT/'acceptance/stage3/probe-f015-v156.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def main():
 original=json.loads(m.OUT.read_text(encoding='utf-8'))
 recovery=m.OUT
 assert json.loads(recovery.read_text(encoding='utf-8')).get('finishedAt')
 m.OUT=m.OUT.with_stem(m.OUT.stem+'-prefix-control');m.STATE=ROOT/'.local-test/f015-v156-prefix-state.json';assert not m.OUT.exists()
 q=m.Probe.__new__(m.Probe);q.cfg=m.p.l.API('配置管理员');q.op=m.p.l.API('运行操作员');q.templates=[];q.tasks=[];q.definitions=[];q.modelCases={};q.ports={'G126_ROBOT':18132}
 q.tokens={'G126_ROBOT':json.loads(m.p.l.protect((ROOT.parent/'tip/.local-test/gpt-f007-v126-robot.dpapi').read_bytes(),True))['token']}
 d=original['definition'];q.definitionId=d['id'];q.family=d['definitionCode'];q.definitionBody={k:d[k] for k in ['taskName','goalTemplate','sceneParams','availableCapabilityTypes','constraintDescription','completionCondition']}
 parent=original['prefixDefinitionFixture'];q.ev={'tag':'V1.156','productSha':m.SHA,'executionBaseline':'V2.4','startedAt':m.now(),'timezone':'Asia/Shanghai','schema':m.SC,'redisDb':10,'cases':[],'trials':[],'rulesBefore':q.cfg('/risk-rules'),
  'planned':['non-exact-eligible-control'],'purpose':'Original exact-family case249 must beat a genuinely eligible prefix candidate, not an unmatched candidate. This positive control uses the same prefix family with no enabled exact-family template.'}
 q.cfg(f'/task-definitions/{q.definitionId}/enable','POST');q.cfg(f"/task-definitions/{parent['id']}/enable",'POST')
 try:
  t=q.create('prefix-eligible-control',1,parent['code']);q.trial(t)
  row=q.submit('non-exact-eligible-control',{'planMode':'MALFORMED'});checks=q.baseline_checks(row,t['id'])
  checks['nonExactBasisRecorded']=any('任务族非精确匹配' in e['detailSummary'] for e in row['observed']['events'] if e['eventType']=='BASELINE_DOWNGRADED')
  q.judge(row,checks)
 finally:
  q.cleanup();q.cfg(f'/task-definitions/{q.definitionId}/disable','POST');q.cfg(f"/task-definitions/{parent['id']}/disable",'POST');q.ev['definitionsRestoredDisabled']=True;q.save()

if __name__=='__main__':main()
