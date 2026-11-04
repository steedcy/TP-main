"""Repair fixture-only gaps after the main round; keep its original evidence intact."""
import importlib.util,json,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('round155',ROOT/'acceptance/stage3/probe-f015-v156.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def main():
 original=json.loads(m.OUT.read_text(encoding='utf-8'))
 assert original.get('finishedAt'),'Main fixture must be cleaned before independent supplement'
 m.OUT=m.OUT.with_stem(m.OUT.stem+'-supplement')
 m.STATE=ROOT/'.local-test/f015-v156-supplement-state.json'
 assert not m.OUT.exists(),'Do not overwrite evidence'
 q=m.Probe.__new__(m.Probe);q.cfg=m.p.l.API('配置管理员');q.op=m.p.l.API('运行操作员')
 q.templates=[];q.tasks=[];q.definitions=[];q.modelCases={};q.ports={'G126_ROBOT':18132}
 q.tokens={'G126_ROBOT':json.loads(m.p.l.protect((ROOT.parent/'tip/.local-test/gpt-f007-v126-robot.dpapi').read_bytes(),True))['token']}
 d=original['definition'];q.definitionId=d['id'];q.family=d['definitionCode']
 q.definitionBody={k:d[k] for k in ['taskName','goalTemplate','sceneParams','availableCapabilityTypes','constraintDescription','completionCondition']}
 q.ev={'tag':'V1.156','productSha':m.SHA,'executionBaseline':'V2.4','startedAt':m.now(),'timezone':'Asia/Shanghai',
  'schema':m.SC,'redisDb':10,'cases':[],'trials':[],'rulesBefore':q.cfg('/risk-rules'),
  'planned':['constraint-hard-fail-corrected','true-empty-family-no-match','zero-six-static-boundaries'],
  'diagnosticCorrections':['The original update included immutable taskName; the API correctly rejected it before any product data change. Correct the fixture payload and execute constraint rejection now.',
   'Original no-template task242 had the same disabled-matching-template fixture as241. Keep the actual request, but do not count it as a distinct empty-family observation; use a new family with zero templates below.']}
 q.cfg(f'/task-definitions/{q.definitionId}/enable','POST');q.save()
 try:
  def constraint():
   t=q.create('constraint-corrected');q.trial(t)
   before={k:v for k,v in q.definitionBody.items() if k!='taskName'}
   changed=copy.deepcopy(before);changed['completionCondition']='routeGenerated=false'
   q.cfg(f'/task-definitions/{q.definitionId}','PUT',changed)
   try:
    step=m.p.step();step['completionCondition']='routeGenerated=false'
    row=q.submit('constraint-hard-fail-corrected',{'goalCompletion':'routeGenerated=false','steps':[step]})
    o=row['observed'];b=o['plans'][-1]
    q.judge(row,{'baselineSelected':b['source']=='BASELINE_TEMPLATE','constraintFails':b['constraintCheckResult']=='FAIL',
     'notFrozen':not b['frozenAt'],'pendingManual':o['task']['status']=='PENDING_MANUAL','zeroCommands':not o['commands']})
   finally:q.cfg(f'/task-definitions/{q.definitionId}','PUT',before);q.disable(t['id'])
  # Constraint rejection already executed by the corrected main probe; no duplicate trial/task.
  def empty_family():
   body=copy.deepcopy(q.definitionBody);body['taskName']='G156 true empty family '+m.datetime.now().strftime('%H%M%S')
   empty=q.cfg('/task-definitions','POST',body);q.definitions.append(empty['id']);q.cfg(f"/task-definitions/{empty['id']}/enable",'POST')
   previous=q.family;q.family=empty['definitionCode']
   try:
    row=q.submit('true-empty-family-no-match');o=row['observed']
    row['matchingTemplatesBefore']=q.cfg('/baseline-templates')
    q.judge(row,{'familyHasZeroTemplates':not any(t['templateIntent']==q.family for t in row['matchingTemplatesBefore']),
     'pendingManual':o['task']['status']=='PENDING_MANUAL','noMatchReason':any(e['reasonCode']=='ERR_NO_BASELINE_TEMPLATE' for e in o['events']),
     'zeroCommands':not o['commands'],'noBaselineVersion':all(v['source']!='BASELINE_TEMPLATE' for v in o['plans'])})
   finally:q.family=previous
  q.run('empty-family-corrected',empty_family)
  def static_bounds():
   seed=q.cfg('/baseline-templates/'+str(original['trials'][0]['templateId']));body={'templateName':'G156 invalid boundary '+m.datetime.now().strftime('%H%M%S'),
    'templateIntent':q.family,'inputParams':seed['inputParams'],'steps':[]};before=m.sql(f'select count(*) from {m.SC}.baseline_templates')
   zero=m.p.raw(q.cfg,'/baseline-templates',body);body['steps']=[copy.deepcopy(seed['steps'][0]) for _ in range(6)]
   six=m.p.raw(q.cfg,'/baseline-templates',body);after=m.sql(f'select count(*) from {m.SC}.baseline_templates')
   q.ev['staticBounds']={'zero':zero,'six':six,'countBefore':before,'countAfter':after,
    'checks':{'zeroRejected':zero['http']==400,'sixRejected':six['http']==400,'noInvalidTemplateWritten':before==after}};q.save()
  q.run('static-boundaries',static_bounds)
 finally:
  q.cleanup();q.cfg(f'/task-definitions/{q.definitionId}/disable','POST')
  q.ev['originalDefinitionRestoredDisabled']=q.cfg(f'/task-definitions/{q.definitionId}')['definitionStatus']=='DISABLED';q.save()

if __name__=='__main__':main()
