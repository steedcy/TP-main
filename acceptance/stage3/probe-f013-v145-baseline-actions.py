"""Manual baseline positive/negative gates and explicit failed handling in GPT schema only.
Enabled status and legacy unsafe content are seeded only on newly-created fixture templates.
This probe does not claim template publication/dry-run acceptance.
"""
import importlib.util,json,time
from pathlib import Path
r=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('p',r/'acceptance/stage3/probe-f013-v145.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
cfg=p.l.API('配置管理员');op=p.l.API('运行操作员');ev=p.metadata();templates=[];tasks=[]
def save():p.save('baseline-and-manual-actions',ev)
def submit(family,marker):
 t=op('/tasks','POST',{'taskGoal':marker+' F013_MISSING_completionCondition synthetic baseline gate','taskFamily':family,'sceneParams':{'targetLocation':'F2_TEST_GATE'}});tasks.append(t['id']);return t['id']
def template(family,name):
 t=cfg('/baseline-templates','POST',{'templateName':name,'templateIntent':family,'inputParams':[{'name':'targetLocation','type':'String','required':True,'defaultValue':'F2_TEST_GATE'}], 'steps':[{'capabilityType':'CAP_NAVIGATION','stepTimeout':60,'completionCondition':'routeGenerated=true','paramMapping':[{'target':'targetLocation','source':'TEMPLATE_INPUT.targetLocation'}]}]});templates.append(t['id']);return t
try:
 definition=cfg('/task-definitions','POST',{'taskName':'G145 F013 baseline fixtures','goalTemplate':'Synthetic navigation to selected destination','sceneParams':[{'name':'targetLocation','type':'String','required':True,'defaultValue':'F2_TEST_GATE'}],'availableCapabilityTypes':['CAP_NAVIGATION'],'constraintDescription':'Synthetic isolated F013 runtime baseline gate','completionCondition':'routeGenerated=true'})
 family=definition['definitionCode'];ev['definition']=definition
 valid=template(family,'G145 F013 valid runtime baseline');ev['validTemplateBefore']=valid
 tid=submit(family,'F145_VALID_BASE');ev['validBefore']=p.observe(op,tid);assert ev['validBefore']['task']['status']=='PENDING_MANUAL'
 p.sql(f"update {p.SC}.baseline_templates set template_status='ENABLED' where id={valid['id']} and template_status='DRAFT'")
 ev['fixtureSeed']='Only own new DRAFT template status seeded ENABLED; second own template completionCondition seeded speed=2 to emulate unsafe legacy input. No publication/dry-run P claimed.'
 ev['validSwitch']=p.raw(op,f'/tasks/{tid}/manual-actions',{'action':'SWITCH_TO_BASELINE','reason':'F013 synthetic positive baseline revalidation'})
 for _ in range(35):
  observed=p.observe(op,tid)
  if observed['task']['status'] in ['COMPLETED','FAILED','PENDING_MANUAL']:break
  time.sleep(0.5)
 ev['validAfter']=observed;save()
 p.sql(f"update {p.SC}.baseline_templates set template_status='DISABLED' where id={valid['id']}")
 for _ in range(20):
  if p.sql(f"select work_status from {p.SC}.device_agents where agent_code='AGT-803437A3'")=='IDLE':break
  time.sleep(0.5)
 invalid=template(family,'G145 F013 unsafe legacy runtime baseline');ev['invalidTemplateBeforeSeed']=invalid
 badTid=submit(family,'F145_BAD_BASE');ev['invalidBefore']=p.observe(op,badTid);assert ev['invalidBefore']['task']['status']=='PENDING_MANUAL'
 badSteps=invalid['steps']
 if isinstance(badSteps,str):badSteps=json.loads(badSteps)
 badSteps[0]['completionCondition']='speed=2'
 encoded=json.dumps(badSteps).replace("'","''")
 p.sql(f"update {p.SC}.baseline_templates set steps='{encoded}'::json,template_status='ENABLED' where id={invalid['id']}")
 ev['invalidSwitch']=p.raw(op,f'/tasks/{badTid}/manual-actions',{'action':'SWITCH_TO_BASELINE','reason':'F013 synthetic negative baseline revalidation'})
 ev['invalidAfter']=p.observe(op,badTid)
 ev['markFailed']=p.raw(op,f'/tasks/{badTid}/manual-actions',{'action':'MARK_FAILED','reason':'F013 synthetic operator decision after unsafe baseline rejection'})
 ev['failedAfter']=p.observe(op,badTid)
 base=ev['validAfter']['plans'][-1];bad=ev['invalidAfter']['plans'][-1]
 ev['checks']={'validBaselineThreeChecksAndFreeze':base['source']=='BASELINE_TEMPLATE' and all(base[k]=='PASS' for k in ['structureCheckResult','capabilityCheckResult','constraintCheckResult']) and bool(base['frozenAt']),
 'validOriginalFailureVersionPreserved':ev['validAfter']['plans'][0]==ev['validBefore']['plans'][0],
 'validBaselineCompleted':ev['validAfter']['task']['status']=='COMPLETED',
 'unsafeBaselineConstraintFails':bad['constraintCheckResult']=='FAIL' and any(x['reasonCode']=='ERR_MOTION_SAFETY_FIELD' for x in bad['validationErrors']),
 'unsafeBaselineNotFrozenOrDispatched':not bad['frozenAt'] and not ev['invalidAfter']['commands'] and not ev['invalidAfter']['assignments'],
 'manualFailureRecordedWithReason':ev['failedAfter']['task']['status']=='FAILED' and any(e['eventType']=='TASK_FAILED' and 'synthetic operator decision' in e.get('detailSummary','') for e in ev['failedAfter']['events']),
 'failedHandlingPlanVersionsUnchanged':ev['failedAfter']['plans']==ev['invalidAfter']['plans']}
 print(json.dumps({'tasks':tasks,'checks':ev['checks']}),flush=True)
finally:
 for templateId in templates:p.sql(f"update {p.SC}.baseline_templates set template_status='DISABLED' where id={templateId}")
 ev['fixtureTemplatesDisabled']=templates;ev['fixtureTaskIds']=tasks;save()
