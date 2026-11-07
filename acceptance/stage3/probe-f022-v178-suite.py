"""V178 full F022 independent HTTP/SQL/protocol suite. Real UI joins same fixture.
Current requirement all measured anew. Keep failures, continue independent branches.
"""
import importlib.util,json,time,copy
from pathlib import Path
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('r',P/'probe-f022-v178-round.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
q=r.q;h=r.h;m=r.m;R=r.R;SC=r.SC
NEUTRAL='Synthetic existing navigation capability; no new protocol.'
def norm(v):return {k:norm(x) for k,x in v.items() if x is not None} if isinstance(v,dict) else [norm(x) for x in v] if isinstance(v,list) else v
def scene(target='F2_TEST_GATE'):return {'targetLocation':target,'partyCount':2,'assist':True,'distance':2.5}
def set_constraint(text):
 b=r.payload(q.definitionBody);b['constraintDescription']=text;q.cfg(f'/task-definitions/{q.definitions[0]}','PUT',b)
def step(target='F2_TEST_GATE',seq=1):return h.st(seq,timeout=600,inputParams={'targetLocation':target},stepGoal='Synthetic passenger guidance')
def neutral():set_constraint(NEUTRAL)
def capture(row,key='after'):return r.capture(row,key)
def journal_for(row):return [v for v in [json.loads(x) for x in (R/'.local-test/f022-v178-model-requests.jsonl').read_text(encoding='utf8').splitlines()] if v['request'].get('taskGoal')==row['request']['taskGoal']]

def presets():
 row=r.case('three-presets-edit-restore');row['originalCapabilities']=m.rows(f'select id,capability_type,capability_status from {SC}.device_capabilities order by id');row['entries']=[]
 originals=m.rows(f'select * from {SC}.task_definitions where is_preset=true order by id');row['originalRows']=originals
 try:
  m.sql(f"update {SC}.device_capabilities set capability_status='ENABLED' where id in (select min(id) from {SC}.device_capabilities where test_passed=true group by capability_type)")
  for d in q.cfg('/task-definitions'):
   if not d['isPreset']:continue
   b=r.payload(d);edit=copy.deepcopy(b);edit['constraintDescription']='G178 temporary preset edit';edit['sceneParams'].append({'name':'g178Optional','type':'String','required':False,'range':'synthetic edit'})
   e={'before':d,'delete':r.raw(q.cfg,f'/task-definitions/{d["id"]}',None,'DELETE'),'identityChange':r.raw(q.cfg,f'/task-definitions/{d["id"]}',dict(edit,taskName='FORBIDDEN',definitionCode='FORBIDDEN'),'PUT')};row['entries'].append(e)
   try:e['edited']=q.cfg(f'/task-definitions/{d["id"]}','PUT',edit)
   finally:e['restored']=q.cfg(f'/task-definitions/{d["id"]}','PUT',b);q.save()
 finally:
  for d in originals:
   m.sql(f"update {SC}.task_definitions set scene_params={m.lit(json.dumps(d['scene_params'],ensure_ascii=False))}::json where id={d['id']}")
  for c in row['originalCapabilities']:m.sql(f"update {SC}.device_capabilities set capability_status={m.lit(c['capability_status'])} where id={c['id']}")
 row['restoredCapabilities']=m.rows(f'select id,capability_type,capability_status from {SC}.device_capabilities order by id');row['restoredRows']=m.rows(f'select * from {SC}.task_definitions where is_preset=true order by id')
 r.record(row,{'threePresets':len(row['entries'])==3,'allDeleteRejected':all(e['delete']['http']==400 for e in row['entries']),'identityRejected':all(e['identityChange']['http']==400 for e in row['entries']),'paramsConstraintEditable':all(e['edited']['constraintDescription']=='G178 temporary preset edit' for e in row['entries']),'semanticRestored':all(norm(r.payload(e['before']))==norm(r.payload(e['restored'])) for e in row['entries']),'rawSceneJsonRestored':all(a['scene_params']==b['scene_params'] for a,b in zip(originals,row['restoredRows'])),'capabilitiesRestored':row['originalCapabilities']==row['restoredCapabilities']})

def description_case(name,text,target,should_pass):
 set_constraint(text);row=r.new(name,[step(target)],scene=scene(target));row['definition']=q.cfg(f'/task-definitions/{q.definitions[0]}');row['definitionRows']=r.drow(q.definitions[0]);o=capture(row,'beforeAcceptance')
 if should_pass:
  end=h.finish(row);checks={'definitionPersisted':row['definition']['constraintDescription']==text,'legalPlanPasses':bool(end['plans']) and all(p['constraintCheckResult']=='PASS' for p in end['plans']),'legalTaskCompletes':end['task']['status']=='COMPLETED'}
 else:
  if o['task']['status']=='PENDING_ASSIGNMENT':
   d,msg=h.accept(row);row['actualProhibitedExecute']=msg
  end=capture(row);checks={'definitionPersisted':row['definition']['constraintDescription']==text,'hardConstraintFail':any(p['constraintCheckResult']=='FAIL' and any(e.get('reasonCode')=='ERR_TASK_DEFINITION_CONSTRAINT' for e in p['validationErrors']) for p in end['plans']),'noFreeze':all(not p['frozenAt'] for p in end['plans']),'noExecution':not any(c['command_type']=='EXECUTE_CAPABILITY' for c in end['commandRows'])}
 row['modelCalls']=journal_for(row);planning=[x for x in row['modelCalls'] if x['phase']=='planning'];checks['exactDescriptionInInitialRequest']=bool(planning) and text in planning[0]['request']['constraints'];r.record(row,checks);q.terminate(row);neutral()

def descriptions():
 cases=[('116-original-allowed','仅允许前往F2_TEST_GATE。','F2_TEST_GATE',True),('116-original-prohibition','禁止前往F2_TEST_GATE；仅允许前往F2_ZONE_A。','F2_TEST_GATE',False),('116-allowed-zone','禁止前往F2_TEST_GATE；仅允许前往F2_ZONE_A。','F2_ZONE_A',True),('116-whitelist-other-zone','仅允许前往F2_ZONE_A。','F2_ZONE_B',False),('116-whitelist-shorter-valid-area','仅允许前往F2_TEST_GATE。','F2_TEST',False),('116-capability-sentence-legal','仅允许使用CAP_NAVIGATION能力。','F2_TEST_GATE',True),('capability-prohibition','禁止使用CAP_NAVIGATION能力。','F2_TEST_GATE',False),('capability-allow-other-reject','仅允许使用CAP_INFO_DISPLAY能力。','F2_TEST_GATE',False),('combined-capability-and-location-legal','仅允许使用CAP_NAVIGATION能力；仅允许前往F2_TEST_GATE。','F2_TEST_GATE',True),('combined-capability-and-location-reject','仅允许使用CAP_NAVIGATION能力；仅允许前往F2_ZONE_A。','F2_TEST_GATE',False)]
 for args in cases:q.run(args[0],lambda args=args:description_case(*args))
 neutral()

def condition_and_types():
 row=r.new('supported-four-types-complete',[step()]);o=h.finish(row);r.record(row,{'completed':o['task']['status']=='COMPLETED','sceneExact':o['task']['sceneParams']==scene()})
 row=r.new('condition-plus-five-actions',[{'stepSeq':1,'nodeType':'CONDITION','condition':'synthetic assistance required'}]+[h.st(i+2,timeout=600,branchOf=1) for i in range(5)]);o=h.finish(row);r.record(row,{'completed':o['task']['status']=='COMPLETED','fiveFrozenActions':len(o['plans'][-1]['planSteps'])==5,'fiveCompletedActions':len([a for a in o['assignments'] if a['stepStatus']=='COMPLETED'])==5})

def replan_case(name,remaining,text=NEUTRAL,target='F2_TEST_GATE'):
 set_constraint(text);initialTarget='F2_ZONE_A' if '禁止' in text else 'F2_TEST_GATE';row=r.new(name,[step(initialTarget,i+1) for i in range(3)],scene=scene(initialTarget),replanSteps=[step(target,i+1) for i in range(remaining)])
 d,msg=h.accept(row);h.feed(row,d,msg);capture(row,'completedPrefix');d,msg=h.accept(row);h.failtwice(row,d,msg);backup,cmd=h.accept(row);h.failtwice(row,backup,cmd);o=capture(row)
 checks={'realReplan':any(e['eventType']=='REPLANNING_TRIGGERED' for e in o['events']),'prefixPreserved':any(a['stepSeq']==1 and a['stepStatus']=='COMPLETED' for a in o['assignments'])}
 if '禁止' in text:checks.update(replanConstraintRejected=any(p['versionNo']>1 and p['constraintCheckResult']=='FAIL' for p in o['plans']),newVersionUnfrozen=all(not p['frozenAt'] for p in o['plans'] if p['versionNo']>1),definitionReason='ERR_TASK_DEFINITION_CONSTRAINT' in json.dumps(o))
 elif remaining==5:checks.update(overGlobalQuotaRejected=any(e.get('reasonCode')=='ERR_STEP_LIMIT_EXCEEDED' for e in o['events']),noOverLimitFrozen=all(not p['frozenAt'] or len(p['planSteps'])<=5 for p in o['plans']))
 else:checks.update(mergedFive=any(p['versionNo']>1 and len(p['planSteps'])==5 and p['constraintCheckResult']=='PASS' for p in o['plans']),allVersionsAtMostFive=all(len(p['planSteps'])<=5 for p in o['plans']),actualCompletedAtMostFive=len([a for a in o['assignments'] if a['stepStatus']=='COMPLETED'])<=5)
 row['modelCalls']=journal_for(row);r.record(row,checks);q.terminate(row);neutral()

def baseline():
 neutral();h.reset();t=q.cfg('/baseline-templates','POST',{'templateName':'G178 baseline '+str(time.time_ns()),'templateIntent':q.family,'inputParams':[q.definitionBody['sceneParams'][0]],'steps':[{'capabilityType':'CAP_NAVIGATION','paramMapping':[{'target':'targetLocation','source':'TEMPLATE_INPUT.targetLocation'}],'stepTimeout':600,'completionCondition':'routeGenerated=true'}]});q.templates.append(t['id']);q.save()
 ret=q.cfg(f"/baseline-templates/{t['id']}/dry-run",'POST',{'inputParams':scene(),'simulatedDevices':[{'stepSeq':1,'agentId':q.devices[0].agent}]});row={'name':'baseline-publication-trial','taskId':ret['taskId'],'response':ret,'templateId':t['id']};q.tasks.append(row['taskId']);q.ev['cases'].append(row);q.save();end=h.finish(row);trial=q.cfg(f"/baseline-templates/{t['id']}/dry-runs/{row['taskId']}");row['trialResult']=trial;r.record(row,{'trialCompletes':end['task']['status']=='COMPLETED','trialSuccess':trial['result']=='SUCCESS'});q.cfg(f"/baseline-templates/{t['id']}/enable",'POST')
 for name,text,should_pass in [('baseline-allowed','仅允许前往F2_TEST_GATE。',True),('baseline-prohibited','禁止前往F2_TEST_GATE；仅允许前往F2_ZONE_A。',False)]:
  set_constraint(text);row=r.new(name,[step()],planHttpStatus=503);o=capture(row)
  if should_pass:
   end=h.finish(row);checks={'baselineSource':any(p['source']=='BASELINE_TEMPLATE' for p in end['plans']),'completed':end['task']['status']=='COMPLETED'}
  else:
   if o['task']['status']=='PENDING_ASSIGNMENT':d,msg=h.accept(row);row['unexpectedExecute']=msg
   end=capture(row);checks={'constraintRejected':any(p['source']=='BASELINE_TEMPLATE' and p['constraintCheckResult']=='FAIL' for p in end['plans']),'noFrozenProhibited':all(not p['frozenAt'] for p in end['plans']),'noExecution':not any(c['command_type']=='EXECUTE_CAPABILITY' for c in end['commandRows'])}
  r.record(row,checks);q.terminate(row)
 neutral();q.cfg(f"/baseline-templates/{t['id']}/disable",'POST')

def ui_wait():
 neutral();q.ev['uiFixture']={'definitionId':q.definitions[0],'definitionName':q.definitionBody['taskName'],'family':q.family};q.save();(R/'.local-test/f022-v178-ui-ready.json').write_bytes(json.dumps(q.ev['uiFixture']).encode('utf8'))
 while not (R/'.local-test/f022-v178-finish').exists():time.sleep(1)
 ids=m.rows(f"select id from {SC}.tasks where task_goal like 'F178_BROWSER%' order by id")
 for item in ids:
  tid=item['id'];q.tasks.append(tid);row={'name':'browser-submitted-persistence','taskId':tid};q.ev['cases'].append(row);o=capture(row);r.record(row,{'sceneExact':o['task']['sceneParams']==scene(),'createdByOperator':o['task']['createdBy'] is not None});q.terminate(row)

def main():
 try:
  q.setup();q.ev['resourceOwnership']={'schema':SC,'redisDb':10,'backend':18129,'model':18117,'adapters':[18132,18133,18134],'ui':15179};q.ev['initialPresetRows']=m.rows(f'select * from {SC}.task_definitions where is_preset=true order by id');q.save()
  b=copy.deepcopy(q.definitionBody);b['sceneParams']=[{'name':'targetLocation','type':'String','required':True,'range':'synthetic location'},{'name':'partyCount','type':'Integer','required':True,'range':'synthetic integer'},{'name':'assist','type':'Boolean','required':True,'range':'synthetic boolean'},{'name':'distance','type':'Double','required':True,'range':'synthetic double'}];b['constraintDescription']=NEUTRAL;q.cfg(f'/task-definitions/{q.definitions[0]}','PUT',r.payload(b));q.definitionBody=b
  for fn in [r.definition_boundaries,presets,r.capability_gap,r.dynamic_gate,r.lifecycle_and_five_steps,r.constraint_and_completion,r.disable_existing_and_audit,r.authorization_delete,condition_and_types,descriptions,lambda:replan_case('replan-prefix1-plus4',4),lambda:replan_case('replan-prefix1-plus5-reject',5),lambda:replan_case('replan-prohibited-destination',1,'禁止前往F2_TEST_GATE；仅允许前往F2_ZONE_A。'),ui_wait]:q.run(fn.__name__,fn)
 finally:
  for tid in q.templates:
   try:q.cfg(f'/baseline-templates/{tid}/disable','POST')
   except Exception as ex:q.ev['diagnostics'].append({'templateCleanup':tid,'error':str(ex)})
  q.cleanup();q.ev['endedAt']=m.now();q.save()
if __name__=='__main__':main()
