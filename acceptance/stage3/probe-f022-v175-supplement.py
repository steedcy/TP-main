"""Fill missing F022 assertions after retained probe diagnostics; no repeat of sufficient observations."""
import os,importlib.util,json,copy,time
from pathlib import Path
os.environ['GPT_EVIDENCE_LABEL']='supplement'
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('round',P/'probe-f022-v175-round.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)

def normalized(v):
 return {k:normalized(x) for k,x in v.items() if x is not None} if isinstance(v,dict) else [normalized(x) for x in v] if isinstance(v,list) else v

q=r.q;h=r.h;m=r.m;SC=r.SC;R=r.R
original=json.loads((P/'evidence/SRS_F022-V1.175-http-20261107.json').read_text(encoding='utf-8'))
def corrected_observations():
 row=r.case('retained-observations-correction-no-new-execution');row['source']='SRS_F022-V1.175-http-20261107.json';c=original['cases'][0]
 row['explanation']=['Duplicate names correctly use HTTP409/API4602, not all400.','Original legal request dictionary was mutated after creation; compare persisted value to captured actual create response, update to updateRequest.','Capability fixture restoration comparison must sort by primary key.','Six steps are rejected before plan persistence; retained model response and ERR_STEP_LIMIT_EXCEEDED prove boundary.','Number/Object are outside supported String/Integer/Boolean/Double UI types, so original accepted wrong values do not prove failure of supported-type validation; original tasks982/983 retained and cleaned.','Audit result column is operation_result; no business execution repeated.']
 checks={'createInvalid400ExceptDuplicate409':all(x['response']['http']==(409 if x['field']=='taskName' and x['response']['body']['code']==4602 else 400) for x in c['invalid']),'allBoundaryRowsMatchCapturedResponses':all(x['persisted'][0]['constraint_description']==x['created']['constraintDescription'] and x['updatedRows'][0]['constraint_description']==x['updated']['constraintDescription'] for x in c['legal'])}
 cap=next(c for c in original['cases'] if c['name']=='unknown-and-no-enabled-capability');checks['originalCapabilityRestoreExact']=sorted(cap['fixtureOriginal'],key=lambda x:x['id'])==sorted(cap['restored'],key=lambda x:x['id'])
 six=next(c for c in original['cases'] if c['name']=='six-step-rejected')['after'];checks['sixRejectedBeforePersist']=not six['plans'] and not six['commandRows'] and any(e.get('reasonCode')=='ERR_STEP_LIMIT_EXCEEDED' for e in six['events'])
 life=next(c for c in original['cases'] if c['name']=='disable-definition-existing-task-continues');logs=life['definitionAudit']
 checks.update(disabledAbsent=not any(x['id']==original['definitionIds'][0] for x in life['enabledDefinitions']),disabledNewSubmit400=life['disabledSubmit']['http']==400,existingContinues=life['after']['task']['status']=='COMPLETED' and life['beforeDisable']['task']['currentPlanVersionId']==life['after']['task']['currentPlanVersionId'],fourAuditTypes={'TASK_DEFINITION_CREATE','TASK_DEFINITION_UPDATE','TASK_DEFINITION_ENABLE','TASK_DEFINITION_DISABLE'}<=set(x['operation_type'] for x in logs),auditFields=all(x['username'] and x['created_at'] and x['operation_result']=='SUCCESS' for x in logs))
 row['checksSourceCases']=[c['name'],'unknown-and-no-enabled-capability','six-step-rejected','disable-definition-existing-task-continues'];r.record(row,checks)

def presets():
 row=r.case('three-presets-edit-and-restore-complete');row['capabilityFixture']=m.rows(f'select id,capability_type,capability_status from {SC}.device_capabilities order by id');row['presets']=[]
 try:
  # Configuration-only prerequisite in GPT's private schema. No actual device/hardware claim.
  m.sql(f"update {SC}.device_capabilities set capability_status='ENABLED' where id in (select min(id) from {SC}.device_capabilities group by capability_type)")
  for d in q.cfg('/task-definitions'):
   if not d['isPreset'] or d['definitionCode']=='FLIGHT_CHANGE_RESPONSE':continue
   b=r.payload(d);edit=copy.deepcopy(b);edit['constraintDescription']='F175 preset edit restore';edit['sceneParams'].append({'name':'f175Optional','type':'String','required':False,'range':'synthetic edit'})
   e={'before':d,'delete':r.raw(q.cfg,f'/task-definitions/{d["id"]}',None,'DELETE')};row['presets'].append(e)
   try:
    e['immutableReject']=r.raw(q.cfg,f'/task-definitions/{d["id"]}',dict(edit,taskName='FORBIDDEN_RENAME',definitionCode='FORBIDDEN_CODE'),'PUT')
    e['updated']=q.cfg(f'/task-definitions/{d["id"]}','PUT',edit)
   finally:e['restored']=q.cfg(f'/task-definitions/{d["id"]}','PUT',b);q.save()
 finally:
  for c in row['capabilityFixture']:m.sql(f"update {SC}.device_capabilities set capability_status={m.lit(c['capability_status'])} where id={c['id']}")
 row['restoredCapabilities']=m.rows(f'select id,capability_type,capability_status from {SC}.device_capabilities order by id')
 r.record(row,{'twoPresetsFlightSeparate':len(row['presets'])==2,'delete400':all(x['delete']['http']==400 for x in row['presets']),'nameCodeUnknownFieldsRejected':all(x['immutableReject']['http']==400 for x in row['presets']),'editableParamsConstraint':all(x['updated']['constraintDescription']=='F175 preset edit restore' and x['updated']['sceneParams'][-1]['name']=='f175Optional' for x in row['presets']),'identityPreserved':all(x['updated']['taskName']==x['before']['taskName'] and x['updated']['definitionCode']==x['before']['definitionCode'] for x in row['presets']),'allBusinessFieldsRestored':all(normalized(r.payload(x['before']))==normalized(r.payload(x['restored'])) for x in row['presets']),'allCapabilitiesRestored':row['capabilityFixture']==row['restoredCapabilities']})

def cap_put():
 row=r.case('capability-gap-put-actual-contract');did=q.definitions[0];row['requests']=[];before=r.drow(did)
 for cap in ['CAP_F175_UNKNOWN','CAP_INFO_DISPLAY']:
  original=m.rows(f"select id,capability_status from {SC}.device_capabilities where capability_type={m.lit(cap)} order by id")
  try:
   m.sql(f"update {SC}.device_capabilities set capability_status='DISABLED' where capability_type={m.lit(cap)}")
   b=r.payload(q.definitionBody);b['availableCapabilityTypes']=[cap];row['requests'].append(r.raw(q.cfg,f'/task-definitions/{did}',b,'PUT'))
  finally:
   for c in original:m.sql(f"update {SC}.device_capabilities set capability_status={m.lit(c['capability_status'])} where id={c['id']}")
 row['after']=r.drow(did)
 r.record(row,{'bothGap4004604':all(x['http']==400 and x['body']['code']==4604 and '能力' in x['body']['message'] for x in row['requests']),'noMutation':before==row['after']})

def dynamic_supported():
 r.dynamic_gate()
 row=r.new('supported-four-types-complete',[h.st(timeout=600)]);o=h.finish(row)
 r.record(row,{'submit200':row['response']['http']==200,'completed':o['task']['status']=='COMPLETED','allFourValuesPersisted':o['task']['sceneParams']==row['request']['sceneParams']})
 # Actual branches count toward the same five-action budget; condition node does not.
 condition={'stepSeq':1,'nodeType':'CONDITION','condition':'synthetic passenger assistance required'}
 steps=[condition]+[h.st(i+2,timeout=600,branchOf=1) for i in range(5)]
 row=r.new('condition-plus-five-actions',steps);o=h.finish(row)
 r.record(row,{'completed':o['task']['status']=='COMPLETED','fiveFrozenActions':len(o['plans'][-1]['planSteps'])==5,'fiveActualActions':len([a for a in o['assignments'] if a['stepStatus']=='COMPLETED'])==5,'conditionFolded':all(s.get('branchCondition')=='synthetic passenger assistance required' for s in o['plans'][-1]['planSteps'])})

def main():
 try:
  corrected_observations();q.setup()
  b=copy.deepcopy(q.definitionBody);b['sceneParams']=[{'name':'targetLocation','type':'String','required':True,'range':'synthetic location'},{'name':'partyCount','type':'Integer','required':True,'range':'synthetic integer'},{'name':'assist','type':'Boolean','required':True,'range':'synthetic boolean'},{'name':'distance','type':'Double','required':True,'range':'synthetic double'}]
  q.cfg(f'/task-definitions/{q.definitions[0]}','PUT',r.payload(b));q.definitionBody=b
  for fn in [presets,cap_put,dynamic_supported]:q.run(fn.__name__,fn)
  # Retain successful browser-created definition, register ownership for final disable.
  for d in q.cfg('/task-definitions'):
   if d['taskName']=='G175 browser definition':q.definitions.append(d['id'])
  for tid in [982,983]:
   row={'name':'unsupported-type-fixture-cleanup','taskId':tid,'fixtureOnly':True};q.tasks.append(tid);q.ev['cases'].append(row);row['preservedBeforeCleanup']=q.observe(tid);q.terminate(row);q.save()
  q.ev['uiFixture']={'definitionId':q.definitions[0],'definitionName':q.definitionBody['taskName'],'family':q.family};q.save();(R/'.local-test/f022-v175-ui-ready-supplement.json').write_text(json.dumps(q.ev['uiFixture']))
  while not (R/'.local-test/f022-v175-finish-supplement').exists():time.sleep(1)
 finally:q.cleanup();q.ev['endedAt']=m.now();q.save()
if __name__=='__main__':main()
