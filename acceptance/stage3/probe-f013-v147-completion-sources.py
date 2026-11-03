import importlib.util,json,time,copy
from pathlib import Path
r=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('p',r/'acceptance/stage3/probe-f013-v147.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
op=p.l.API('运行操作员');cfg=p.l.API('配置管理员');ev=p.metadata();ev['cases']=[]
old=json.loads((r/'acceptance/stage3/evidence/SRS_F013-V1.145-baseline-and-manual-actions-20261103.json').read_text(encoding='utf-8'))
family=old['definition']['definitionCode'];definitionId=old['definition']['id'];validId=old['validTemplateBefore']['id'];badId=old['invalidTemplateBeforeSeed']['id']
cfg(f'/task-definitions/{definitionId}/enable','POST');ev['definition']=cfg(f'/task-definitions/{definitionId}')
def step(value='routeGenerated=true',seq=1):return {'stepSeq':seq,'stepGoal':'Generate route to F2_TEST_GATE','capabilityType':'CAP_NAVIGATION','inputParams':{'targetLocation':'F2_TEST_GATE'},'precondition':'device online','completionCondition':value,'failureHandling':'manual handling','stepTimeout':60}
missing=step();missing.pop('precondition')
cases={'F147_BADBOOL':{'steps':[step('routeGenerated=false')]},'F147_MATCH':{'steps':[step()]},'F147_NORMALIZED':{'steps':[step("ROUTE_GENERATED == 'false'")]},'F147_MULTI_MATCH':{'steps':[step('routeGenerated=true and waypointCount>0'),step(seq=2)]},'F147_BASE_TRIGGER':{'steps':[missing]},'F147_REPLAN_BAD':{'steps':[step()],'replanSteps':[step('routeGenerated=false')]},'F147_NATURAL_GOAL':{'goalCompletion':'The navigation route has been generated.','steps':[step('routeGenerated=false')]}}
for marker in ['F147_MATCH','F147_MULTI_MATCH','F147_BASE_TRIGGER','F147_REPLAN_BAD']:
 cases[marker]['goalCompletion']='The navigation route has been generated.'
cases['F147_NATURAL_GOOD']={'goalCompletion':'The navigation route has been generated.','steps':[step()]}
cases['F147_MODEL_OVERRIDE']={'goalCompletion':'routeGenerated=false','steps':[step('routeGenerated=false')]}
path=r/'.local-test/f013-v147-cases.json';path.write_bytes(json.dumps(cases).encode('utf-8'))
ev['controlledCases']=cases
def submit(name):
 req={'taskGoal':name+' synthetic navigation to F2_TEST_GATE','taskFamily':family,'sceneParams':{'targetLocation':'F2_TEST_GATE'}}
 t=op('/tasks','POST',req);o=p.observe(op,t['id']);return {'name':name,'request':req,'observed':o}
originalBad=p.sql(f'select steps::text from {p.SC}.baseline_templates where id={badId}')
try:
 for ident in [validId,badId]:p.sql(f"update {p.SC}.baseline_templates set template_status='DISABLED' where id={ident}")
 for name in ['F147_BADBOOL','F147_MATCH','F147_NORMALIZED','F147_MULTI_MATCH']:
  c=submit(name);o=c['observed'];v=o['plans'][-1]
  if name in ['F147_BADBOOL','F147_NORMALIZED']:
   c['checks']={'constraintRejected':v['constraintCheckResult']=='FAIL','conflictCode':any(e['reasonCode']=='ERR_COMPLETION_CONDITION_CONFLICT' for e in v['validationErrors']),'notFrozen':not v['frozenAt'],'notSupervisedOrDispatched':not any(e['eventType']=='SUPERVISION_JUDGED' for e in o['events']) and not o['commands'] and not o['assignments']}
  else:c['checks']={'threePass':all(v[k]=='PASS' for k in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']),'frozen':bool(v['frozenAt']),'supervised':any(e['eventType']=='SUPERVISION_JUDGED' for e in o['events'])}
  ev['cases'].append(c);p.save('completion-three-sources',ev);print(name,o['task']['id'],c['checks'],flush=True)
 c=submit('F147_BASE_TRIGGER');tid=c['observed']['task']['id'];ev['baselineBefore']=c
 steps=json.loads(originalBad);steps[0]['completionCondition']='routeGenerated=false';encoded=json.dumps(steps).replace("'","''")
 p.sql(f"update {p.SC}.baseline_templates set steps='{encoded}'::json,template_status='ENABLED' where id={badId}")
 ev['baselineFixtureNote']='Only own legacy-test template completionCondition seeded false and ENABLED to exercise runtime hard revalidation; no publication gate acceptance claimed.'
 ev['badBaselineSwitch']=p.raw(op,f'/tasks/{tid}/manual-actions',{'action':'SWITCH_TO_BASELINE','reason':'F013 V147 contradictory baseline negative'})
 bad=p.observe(op,tid);ev['badBaselineAfter']=bad
 p.sql(f"update {p.SC}.baseline_templates set template_status='DISABLED' where id={badId}")
 p.sql(f"update {p.SC}.baseline_templates set template_status='ENABLED' where id={validId}")
 ev['goodBaselineSwitch']=p.raw(op,f'/tasks/{tid}/manual-actions',{'action':'SWITCH_TO_BASELINE','reason':'F013 V147 consistent baseline positive'})
 for _ in range(40):
  good=p.observe(op,tid)
  if good['task']['status'] in ['COMPLETED','FAILED','PENDING_MANUAL']:break
  time.sleep(0.5)
 ev['goodBaselineAfter']=good
 v=bad['plans'][-1];g=good['plans'][-1]
 ev['baselineChecks']={'badConflictRejected':v['constraintCheckResult']=='FAIL' and any(e['reasonCode']=='ERR_COMPLETION_CONDITION_CONFLICT' for e in v['validationErrors']),'badUnfrozenAndNoDispatch':not v['frozenAt'] and not bad['commands'] and not bad['assignments'],'goodBaselinePassesAndCompletes':g['source']=='BASELINE_TEMPLATE' and all(g[k]=='PASS' for k in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']) and bool(g['frozenAt']) and good['task']['status']=='COMPLETED','oldFailedVersionsPreserved':bad['plans']==good['plans'][:len(bad['plans'])]}
 print('baseline',tid,ev['baselineChecks'],flush=True)
finally:
 for ident in [validId,badId]:p.sql(f"update {p.SC}.baseline_templates set template_status='DISABLED' where id={ident}")
 encoded=originalBad.replace("'","''");p.sql(f"update {p.SC}.baseline_templates set steps='{encoded}'::json where id={badId}")
 ev['templateFixturesRestored']=True;p.save('completion-three-sources',ev)
