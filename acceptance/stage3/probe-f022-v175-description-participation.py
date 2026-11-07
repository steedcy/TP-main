"""F022.R07: causal task-family constraint description versus same legal plan.
Authoritative SRS V1.0 5.6.1 R07 and 5.4.4 R03 require family constraints in hard validation.
Uses only a synthetic adapter and symbolic service zone; no physical motion.
"""
import os,importlib.util,json,copy
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='description-participation'
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('r',P/'probe-f022-v175-round.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q;h=r.h;m=r.m;R=r.R;SC=r.SC
def main():
 try:
  q.setup();did=q.definitions[0]
  allowed='仅允许前往F2_TEST_GATE。';forbidden='禁止前往F2_TEST_GATE；仅允许前往F2_ZONE_A。'
  body=r.payload(q.definitionBody);body['constraintDescription']=allowed;q.cfg(f'/task-definitions/{did}','PUT',body)
  row=r.new('description-location-allowed-control',[h.st(timeout=600)],scene={'targetLocation':'F2_TEST_GATE'});row['definition']=q.cfg(f'/task-definitions/{did}');end=h.finish(row)
  r.record(row,{'permittedTargetCompletes':end['task']['status']=='COMPLETED','descriptionPersisted':row['definition']['constraintDescription']==allowed,'allChecksPass':end['plans'][-1]['constraintCheckResult']=='PASS'})
  body['constraintDescription']=forbidden;q.cfg(f'/task-definitions/{did}','PUT',body)
  row=r.new('description-location-prohibited-counterexample',[h.st(timeout=600)],scene={'targetLocation':'F2_TEST_GATE'});row['definition']=q.cfg(f'/task-definitions/{did}');row['definitionRows']=r.drow(did);before=r.capture(row,'beforeAcceptance')
  if before['task']['status']=='PENDING_ASSIGNMENT':
   d,msg=h.accept(row);row['actualExecuteMessage']=msg;row['acceptedBySyntheticAgent']=d.agent
  o=r.capture(row)
  journal=[json.loads(x) for x in (R/'.local-test/f022-v175-model-requests.jsonl').read_text(encoding='utf8').splitlines()];row['modelCalls']=[x for x in journal if x['request'].get('taskGoal')==row['request']['taskGoal']]
  planning=[x for x in row['modelCalls'] if x['phase']=='planning']
  row['expected']='Definition prohibition of F2_TEST_GATE must participate in family-constraint hard validation: reject conflicting plan, no freeze or execution; exact text must reach planning context rather than silently disappear.'
  r.record(row,{'descriptionPersisted':row['definition']['constraintDescription']==forbidden,'descriptionInInitialPlanningRequest':bool(planning) and forbidden in json.dumps(planning[0]['request'],ensure_ascii=False),'prohibitedPlanNotFrozen':all(not p['frozenAt'] for p in o['plans']),'prohibitedPlanConstraintFail':any(p['constraintCheckResult']=='FAIL' for p in o['plans']),'noExecuteCapability':not any(c['command_type']=='EXECUTE_CAPABILITY' for c in o['commandRows'])})
 finally:q.cleanup();q.ev['endedAt']=m.now();q.save()
if __name__=='__main__':main()
