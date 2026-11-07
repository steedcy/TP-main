"""F022 V2.4 independent HTTP/SQL/synthetic-protocol round, fixed V1.175.
Own reusable schema, Redis10 and ports only. No product source mutation.
Waits for explicit UI finish sentinel, then restores fixtures and keeps all evidence.
"""
import importlib.util,json,time,copy,urllib.request,urllib.error
from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('h',Path(__file__).with_name('probe-f022-v175-helpers.py'));h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
q=h.q;m=h.m;SC=m.SC
raw=m.p.raw
def save():q.save()
def record(row,checks):q.record(row,checks)
def case(name):
 r={'name':name};q.ev['cases'].append(r);save();return r
def capture(row,key='after'):
 o=q.observe(row['taskId']);row[key]=o;save();return o
def drow(did):return m.rows(f'select * from {SC}.task_definitions where id={did}')
def definition(body,name=None):
 b=copy.deepcopy(body)
 if name:b['taskName']=name
 d=q.cfg('/task-definitions','POST',b);q.definitions.append(d['id']);save();return d
def payload(d):return {k:d[k] for k in ['goalTemplate','sceneParams','availableCapabilityTypes','constraintDescription','completionCondition']}
def persist_snapshot():return m.rows(f'select * from {SC}.task_definitions order by id')
def new(name,steps=None,family=None,scene=None,**cfg):
 h.reset();marker='F175_'+name.upper().replace('-','_')
 q.cases[marker]={'steps':steps or [h.st(timeout=600)],'goalCompletion':'routeGenerated=true',**cfg}
 (R/'.local-test/f022-v175-cases.json').write_text(json.dumps(q.cases),encoding='utf-8')
 body={'taskGoal':marker+' Synthetic passenger service F2_TEST_GATE','taskFamily':family or q.family,'sceneParams':scene or {'targetLocation':'F2_TEST_GATE','partyCount':2,'assist':True,'distance':2.5}}
 res=raw(q.op,'/tasks',body)
 tid=int(m.sql(f'select id from {SC}.tasks where task_goal={m.lit(body["taskGoal"])} order by id desc limit 1'))
 row={'name':name,'taskId':tid,'request':body,'response':res};q.tasks.append(tid);q.ev['cases'].append(row);save();return row
def finishcase(row):q.terminate(row)

def definition_boundaries():
 r=case('definition-create-update-boundaries');r['invalid']=[]
 base=copy.deepcopy(q.definitionBody);base['taskName']='G175 invalid boundary'
 did=q.definitions[0]
 before=persist_snapshot();r['before']=before
 bad=[]
 for value in [None,'','   ','\t\n','x'*501]:bad.append(('constraintDescription',value))
 bad.append(('constraintDescription','OMITTED'))
 bad += [('taskName',''),('taskName',' '),('taskName','x'*65),('taskName',q.definitionBody['taskName']),('goalTemplate',''),('goalTemplate','x'*501),('sceneParams',[]),('availableCapabilityTypes',[]),('completionCondition',''),('sceneParams',[{'name':'','type':'String','required':True}]),('sceneParams',[{'name':'where','type':''}])]
 for field,val in bad:
  b=copy.deepcopy(base)
  if val=='OMITTED':b.pop(field)
  else:b[field]=val
  r['invalid'].append({'method':'POST','field':field,'value':val,'response':raw(q.cfg,'/task-definitions',b)})
 for field,val in bad:
  if field=='taskName':continue
  b=payload(base)
  if val=='OMITTED':b.pop(field)
  else:b[field]=val
  r['invalid'].append({'method':'PUT','field':field,'value':val,'response':raw(q.cfg,f'/task-definitions/{did}',b,'PUT')})
 r['afterInvalid']=persist_snapshot()
 r['legal']=[]
 for n in [1,500]:
  b=copy.deepcopy(base);b.update(taskName=('Z' if n==1 else 'N'*64),goalTemplate='g'*n,constraintDescription='约'*n)
  d=definition(b);r['legal'].append({'request':copy.deepcopy(b),'created':d,'persisted':drow(d['id'])})
  b['constraintDescription']='界'*(500 if n==1 else 1);u=q.cfg(f'/task-definitions/{d["id"]}','PUT',payload(b));r['legal'][-1].update(updateRequest=payload(b),updated=u,updatedRows=drow(d['id']))
 checks={'allInvalid400orDuplicate409':all(x['response']['http']==(409 if x['field']=='taskName' and x['value']==q.definitionBody['taskName'] else 400) for x in r['invalid']),'invalidNoMutation':before==r['afterInvalid'],'constraintInvalid3001':all(x['response']['body']['code']==3001 for x in r['invalid'] if x['field']=='constraintDescription'),'oneAnd500CharsPersistExactly':all(x['persisted'][0]['constraint_description']==x['request']['constraintDescription'] and x['updatedRows'][0]['constraint_description']==x['updateRequest']['constraintDescription'] for x in r['legal']),'name1And64Goal1And500':all(x['created']['taskName']==x['request']['taskName'] and x['created']['goalTemplate']==x['request']['goalTemplate'] for x in r['legal'])}
 record(r,checks)

def preset_protection():
 r=case('three-preset-protection-edit-restore');r['presets']=[]
 for d in q.cfg('/task-definitions'):
  if not d['isPreset']:continue
  b=payload(d);entry={'before':d,'delete':raw(q.cfg,f'/task-definitions/{d["id"]}',None,'DELETE')};r['presets'].append(entry)
  edit=copy.deepcopy(b);edit['sceneParams']=b['sceneParams']+[{'name':'f175Optional','type':'String','required':False,'range':'synthetic edit restore'}];edit['constraintDescription']='F175 synthetic preset constraint';edit.update(taskName='FORBIDDEN_RENAME',definitionCode='FORBIDDEN_CODE')
  try:entry['updated']=q.cfg(f'/task-definitions/{d["id"]}','PUT',edit);entry['persisted']=drow(d['id'])
  finally:entry['restored']=q.cfg(f'/task-definitions/{d["id"]}','PUT',b);save()
 checks={'exactlyThreePresets':len(r['presets'])==3,'allDeleteRejected':all(x['delete']['http']==400 for x in r['presets']),'paramsConstraintsEditable':all(x['updated']['constraintDescription']=='F175 synthetic preset constraint' and any(p['name']=='f175Optional' for p in x['updated']['sceneParams']) for x in r['presets']),'nameCodeImmutable':all(x['updated']['taskName']==x['before']['taskName'] and x['updated']['definitionCode']==x['before']['definitionCode'] for x in r['presets']),'businessFieldsRestored':all(payload(x['before'])==payload(x['restored']) for x in r['presets'])}
 record(r,checks)

def capability_gap():
 r=case('unknown-and-no-enabled-capability');r['requests']=[];before=persist_snapshot()
 b=copy.deepcopy(q.definitionBody);b['taskName']='G175 unknown capability';b['availableCapabilityTypes']=['CAP_F175_UNKNOWN']
 for method,path in [('POST','/task-definitions'),('PUT',f'/task-definitions/{q.definitions[0]}')]:r['requests'].append({'kind':'unknown','response':raw(q.cfg,path,b if method=='POST' else payload(b),method)})
 original=m.rows(f"select id,capability_status from {SC}.device_capabilities where capability_type='CAP_INFO_DISPLAY'");r['fixtureOriginal']=original
 try:
  m.sql(f"update {SC}.device_capabilities set capability_status='DISABLED' where capability_type='CAP_INFO_DISPLAY'")
  b['taskName']='G175 disabled capability';b['availableCapabilityTypes']=['CAP_INFO_DISPLAY']
  for method,path in [('POST','/task-definitions'),('PUT',f'/task-definitions/{q.definitions[0]}')]:r['requests'].append({'kind':'known-but-no-enabled-instance','response':raw(q.cfg,path,b if method=='POST' else payload(b),method)})
 finally:
  for x in original:m.sql(f"update {SC}.device_capabilities set capability_status={m.lit(x['capability_status'])} where id={x['id']}")
 r['restored']=m.rows(f"select id,capability_status from {SC}.device_capabilities where capability_type='CAP_INFO_DISPLAY'");r['definitionsAfter']=persist_snapshot()
 record(r,{'allFour400':len(r['requests'])==4 and all(x['response']['http']==400 for x in r['requests']),'capabilityGapExplained':all('能力' in x['response']['body']['message'] for x in r['requests']),'invalidNoDefinitionMutation':before==r['definitionsAfter'],'fixtureRestored':sorted(original,key=lambda x:x['id'])==sorted(r['restored'],key=lambda x:x['id'])})

def dynamic_gate():
 r=case('dynamic-required-four-types-api');r['requests']=[]
 good={'targetLocation':'F2_TEST_GATE','partyCount':2,'assist':True,'distance':2.5}
 before=m.sql(f'select count(*) from {SC}.tasks');journal=R/'.local-test/f022-v175-model-requests.jsonl';calls=len(journal.read_text(encoding='utf-8').splitlines()) if journal.exists() else 0
 for field,value in [('targetLocation',None),('targetLocation',''),('partyCount','wrong'),('assist','wrong'),('distance','wrong')]:
  scene=copy.deepcopy(good)
  if value is None:scene.pop(field)
  else:scene[field]=value
  body={'taskGoal':'F175 invalid scene','taskFamily':q.family,'sceneParams':scene};r['requests'].append({'request':body,'response':raw(q.op,'/tasks',body)})
 r['taskCountBefore']=before;r['taskCountAfter']=m.sql(f'select count(*) from {SC}.tasks');r['modelCallsBefore']=calls;r['modelCallsAfter']=len(journal.read_text(encoding='utf-8').splitlines()) if journal.exists() else 0
 record(r,{'all400':all(x['response']['http']==400 for x in r['requests']),'noTaskCreated':r['taskCountBefore']==r['taskCountAfter'],'noModelCall':r['modelCallsBefore']==r['modelCallsAfter']})

def lifecycle_and_five_steps():
 for name,n in [('same-definition-two-step',2),('same-definition-five-step',5)]:
  row=new(name,[h.st(i+1,timeout=600) for i in range(n)]);end=h.finish(row);plans=end['plans'];assign=end['assignments']
  record(row,{'submit200':row['response']['http']==200,'completed':end['task']['status']=='COMPLETED','planHasExpectedSteps':all(len(p['planSteps'])==n for p in plans),'actualAtMostFive':len([a for a in assign if a['stepStatus']=='COMPLETED'])==n<=5,'allValidationPass':all(all(p[k]=='PASS' for k in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']) for p in plans),'typedScenePersisted':end['task']['sceneParams']==row['request']['sceneParams'],'autonomousSource':all(p['source']=='AUTONOMOUS' for p in plans)})
 row=new('six-step-rejected',[h.st(i+1) for i in range(6)]);o=capture(row)
 record(row,{'stepLimitReason':any(e.get('reasonCode')=='ERR_STEP_LIMIT_EXCEEDED' for e in o['events']),'noFrozenInvalidPlan':all(not p['frozenAt'] for p in o['plans']),'noAssignmentsCommands':not o['assignments'] and not o['commandRows'],'pendingManual':o['task']['status']=='PENDING_MANUAL'});finishcase(row)

def constraint_and_completion():
 row=new('definition-capability-scope-reject',[m.p.step(cap='CAP_INFO_DISPLAY',params={'displayContent':'synthetic F175','displayLocation':'F2_TEST_GATE'})]);o=capture(row)
 record(row,{'constraintFail':any(p['constraintCheckResult']=='FAIL' for p in o['plans']),'reasonNamesScope':any(e.get('reasonCode')=='ERR_CAPABILITY_NOT_IN_TASK_DEFINITION' for e in o['events']) or 'ERR_CAPABILITY_NOT_IN_TASK_DEFINITION' in json.dumps(o),'noCommands':not o['commandRows'],'notFrozen':all(not p['frozenAt'] for p in o['plans'])});finishcase(row)
 row=new('definition-completion-conflict-reject',[h.st(completionCondition='routeGenerated=false')],goalCompletion='routeGenerated=false');o=capture(row)
 record(row,{'definitionOverridesModel':any(p['constraintCheckResult']=='FAIL' for p in o['plans']),'explicitConflictReason':'ERR_COMPLETION_CONDITION_CONFLICT' in json.dumps(o),'noExecution':not o['commandRows'] and not o['assignments']});finishcase(row)
 row=new('success-feedback-unmet-completion',[h.st(timeout=600)]);d,msg=h.accept(row);ret=h.feed(row,d,msg,output={'routeGenerated':False});o=capture(row)
 record(row,{'callback200':ret['http']==200,'notTaskCompleted':o['task']['status']!='COMPLETED','stepNotCompleted':all(a['stepStatus']!='COMPLETED' for a in o['assignments']),'unmetConditionPersisted':'routeGenerated' in json.dumps(o) and any(a.get('outputParams',{}).get('routeGenerated') is False for a in o['assignments']),'noStepCompletedEvent':not any(e['eventType']=='STEP_COMPLETED' for e in o['events'])});finishcase(row)

def disable_existing_and_audit():
 row=new('disable-definition-existing-task-continues',[h.st(timeout=600),h.st(2,timeout=600)]);d,msg=h.accept(row);before=capture(row,'beforeDisable');did=q.definitions[0]
 q.cfg(f'/task-definitions/{did}/disable','POST');row['enabledDefinitions']=[x for x in q.op('/task-definitions') if x['definitionStatus']=='ENABLED'];row['disabledSubmit']=raw(q.op,'/tasks',row['request']);h.feed(row,d,msg);end=h.finish(row)
 logs=m.rows(f"select * from {SC}.operation_logs where operation_type like 'TASK_DEFINITION_%' and operation_target={m.lit(q.definitionBody['taskName'])} order by id");row['definitionAudit']=logs
 record(row,{'disabledNotSelectable':not any(x['id']==did for x in row['enabledDefinitions']),'disabledNewSubmit400':row['disabledSubmit']['http']==400,'existingCompletes':end['task']['status']=='COMPLETED','existingVersionPreserved':before['task']['currentPlanVersionId']==end['task']['currentPlanVersionId'],'createUpdateEnableDisableAudited':{'TASK_DEFINITION_CREATE','TASK_DEFINITION_UPDATE','TASK_DEFINITION_ENABLE','TASK_DEFINITION_DISABLE'}<=set(x['operation_type'] for x in logs),'auditActorResultTime':all(x.get('username') and x.get('created_at') and x['operation_result']=='SUCCESS' for x in logs)})
 q.cfg(f'/task-definitions/{did}/enable','POST')

def authorization_delete():
 r=case('authorization-and-extension-delete');r['denied']=[];before=persist_snapshot()
 for method,path,body in [('POST','/task-definitions',{}),('PUT',f'/task-definitions/{q.definitions[0]}',{}),('DELETE',f'/task-definitions/{q.definitions[0]}',None)]:r['denied'].append(raw(q.op,path,body,method))
 r['unchanged']=before==persist_snapshot();d=definition(q.definitionBody,'G175 disposable delete');r['created']=d;r['delete']=raw(q.cfg,f'/task-definitions/{d["id"]}',None,'DELETE');r['afterDelete']=drow(d['id'])
 record(r,{'operator403BeforeValidation':all(x['http']==403 for x in r['denied']),'deniedNoMutation':r['unchanged'],'extensionDelete200':r['delete']['http']==200,'deletedAbsent':not r['afterDelete']})
 q.definitions.remove(d['id'])

def ui_wait():
 q.ev['uiFixture']={'definitionId':q.definitions[0],'definitionName':q.definitionBody['taskName'],'family':q.family};save();(R/'.local-test/f022-v175-ui-ready.json').write_text(json.dumps(q.ev['uiFixture']))
 while not (R/'.local-test/f022-v175-finish').exists():time.sleep(1)

def main():
 try:
  q.setup();q.ev['resourceOwnership']={'backend':18129,'model':18117,'adapters':[18132,18133,18134],'ui':15179,'schema':SC,'redis':10};save()
  b=copy.deepcopy(q.definitionBody);b['sceneParams']=[{'name':'targetLocation','type':'String','required':True,'range':'synthetic location'},{'name':'partyCount','type':'Integer','required':True,'range':'synthetic integer'},{'name':'assist','type':'Boolean','required':True,'range':'synthetic boolean'},{'name':'distance','type':'Double','required':True,'range':'synthetic double'}]
  q.cfg(f'/task-definitions/{q.definitions[0]}','PUT',payload(b));q.definitionBody=b
  for fn in [definition_boundaries,capability_gap,dynamic_gate,lifecycle_and_five_steps,constraint_and_completion,disable_existing_and_audit,authorization_delete,ui_wait]:q.run(fn.__name__,fn)
 finally:q.cleanup();q.ev['endedAt']=m.now();save()
if __name__=='__main__':main()
