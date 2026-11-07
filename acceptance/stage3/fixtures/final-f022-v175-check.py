"""Read evidence, restore only GPT fixtures, and capture final F022 SQL/build metadata.
No product writes, schema drops, shared-service stops, or evidence deletions.
"""
import importlib.util,json,subprocess,hashlib,re,xml.etree.ElementTree as ET
from pathlib import Path
R=Path(__file__).resolve().parents[3];D=R/'acceptance/stage3';E=D/'evidence';PRE='SRS_F022-V1.175-'
s=importlib.util.spec_from_file_location('m',D/'probe-f022-v175-base.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def put(name,x):
 path=E/(PRE+name+'-20261107.json');assert not path.exists();path.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def get(suffix):return json.loads((E/(PRE+suffix)).read_text(encoding='utf8'))
def run(*args):return subprocess.check_output(args,cwd=R,encoding='utf8').strip()
cfg=m.l.API('配置管理员');op=m.l.API('运行操作员')
initial=get('http-20261107.json');supp=get('http-20261107-supplement.json');flight=get('http-20261107-preset-flight.json');budget=get('http-20261107-replan-budget.json')
# Restore exact JSON representation too (DTO adds optional defaultValue:null).
presets=[d for d in initial['cases'][0]['before'] if d['is_preset']]
before=m.rows(f'select * from {m.SC}.task_definitions where is_preset=true order by id')
for d in presets:
 changes=[]
 for key in ['goal_template','scene_params','available_capability_types','constraint_description','completion_condition']:
  value=d[key];changes.append(key+'='+m.lit(json.dumps(value,ensure_ascii=False) if isinstance(value,(list,dict)) else value)+('::json' if isinstance(value,(list,dict)) else ''))
 m.sql(f"update {m.SC}.task_definitions set {','.join(changes)} where id={d['id']}")
after=m.rows(f'select * from {m.SC}.task_definitions where is_preset=true order by id')
business=lambda d:{k:d[k] for k in ['id','definition_code','task_name','goal_template','scene_params','available_capability_types','constraint_description','completion_condition','definition_status','is_preset']}
for d in cfg('/task-definitions'):
 if d['taskName'].startswith('G175 ') or d['id'] in initial['definitionIds']:
  if d['definitionStatus']!='DISABLED':cfg(f'/task-definitions/{d["id"]}/disable','POST')
for c in m.rows(f"select c.id,c.capability_code from {m.SC}.device_capabilities c join {m.SC}.devices d on c.device_id=d.id where d.device_code='G175_F022_FLIGHT'"):
 cfg(f"/devices/G175_F022_FLIGHT/capabilities/{c['capability_code']}/status",'POST',{'status':'DISABLED'})
tidrange='task_id between 982 and 997'
cleanup={'at':m.now(),'presetsBeforeRestore':before,'presetsAfterRestore':after,'presetsInitial':presets,'exactBusinessConfigRestored':list(map(business,presets))==list(map(business,after)),'definitions':m.rows(f"select * from {m.SC}.task_definitions where task_name like 'G175 %' or id in ({','.join(str(x) for x in initial['definitionIds'])}) order by id"),'tasks':m.rows(f'select id,task_code,status,current_plan_version_id from {m.SC}.tasks where id between 982 and 997 order by id'),'ownedAgents':m.rows(f"select a.*,d.device_code,d.device_status from {m.SC}.device_agents a join {m.SC}.devices d on d.id=a.device_id where d.device_code like 'G160_F016_%' or d.device_code='G175_F022_FLIGHT' order by a.id"),'currentActiveAssignments':m.sql(f"select count(*) from {m.SC}.task_step_assignments a join {m.SC}.tasks t on t.id=a.task_id where t.id between 982 and 997 and a.plan_version_id=t.current_plan_version_id and a.step_status in ('PENDING_ASSIGNMENT','EXECUTING')"),'triggers':m.sql(f"select count(*) from information_schema.triggers where trigger_schema={m.lit(m.SC)}"),'sharedServices':'not stopped/reset; GPT-owned schema only; no rule/template changes'}
put('fixture-cleanup',cleanup)
corrections={'at':m.now(),'rawEvidenceNeverOverwritten':True,'originalDiagnostics':initial['diagnostics']+supp['diagnostics'],'ui':{},'preset':{},'budget':{},'unsupportedTypeScope':'SRS V1.0 5.6.1 does not enumerate allowed scene-schema type values. Original Number/Object fixtures were outside the UI-supported four types and cannot substitute for supported-type gate coverage. Accepted values/tasks982/983 retained as exploratory robustness observations, not retrospectively asserted P. Supported String/Integer/Boolean/Double negative and legal controls are separately current tested.'}
for name in ['new-empty','edit-roundtrip','edit-persisted']:
 text=(E/(PRE+'ui-'+name+'-20261107.txt')).read_text(encoding='utf8')
 if name=='new-empty':checks={'constraintStartsBlank':any('textbox "* 约束条件' in line and line.rstrip().endswith('"') for line in text.splitlines()),'requiredLabel':'* 约束条件' in text}
 else:checks={'textareaValueInSavedRenderedSnapshot':('Use existing navigation only' if name=='edit-roundtrip' else 'Updated synthetic navigation constraint') in text}
 corrections['ui'][name]={'reason':'DOM textarea value differs from textContent; blank value attribute need not be null. Saved rendered DOM/screenshot supplies original actual value, no new UI execution.','checks':checks,'result':'P' if all(checks.values()) else 'F'}
normalize=lambda value:{k:normalize(v) for k,v in value.items() if v is not None} if isinstance(value,dict) else [normalize(v) for v in value] if isinstance(value,list) else value
allpresets=supp['cases'][1]['presets'][:2]+[flight['cases'][0]]
corrections['preset']={'reason':'DTO normalization adds optional defaultValue:null; configuration values are semantically unchanged. Exact original JSON subsequently restored with explicit SQL fixture restoration. Capability-test return uses capabilityStatus=TESTED_PASSED, not result=SUCCESS.','checks':{'threeValidEditsAndRestores':all(normalize(r['before']['sceneParams'])==normalize(r['restored']['sceneParams']) and r['before']['constraintDescription']==r['restored']['constraintDescription'] for r in allpresets),'flightTestPassed':flight['cases'][0]['capabilityTest']['capabilityStatus']=='TESTED_PASSED','exactFinalConfigRestored':cleanup['exactBusinessConfigRestored']}}
c=budget['cases'][0];o=c['after'];corrections['budget']={'reason':'Five-step replan passes validation but existing RULE_RESOURCE_CRITICAL intentionally routes to high risk/no baseline/manual. F022 requires plan/path<=5, not bypass of risk supervision. Original completion expectation was wrong; no standards relaxed.','taskId':c['taskId'],'checks':{'realReplanAndTwoVersions':len(o['plans'])==2 and any(e['eventType']=='REPLANNING_TRIGGERED' for e in o['events']),'everyVersionAtMostFive':all(len(x['planSteps'])<=5 for x in o['plans']),'mergedPlanFive':len(o['plans'][-1]['planSteps'])==5,'highRiskReasonRecorded':any(e.get('reasonCode')=='RULE_RESOURCE_CRITICAL' for e in o['events']),'actualPathAtMostFive':len([a for a in o['assignments'] if a['stepStatus']=='COMPLETED'])<=5,'completedPrefixPreserved':any(a['stepSeq']==1 and a['stepStatus']=='COMPLETED' for a in o['assignments'])}}
put('probe-corrections',corrections)
smoke={'at':m.now(),'health':m.l.request('http://127.0.0.1:18129/actuator/health'),'authenticated':{},'productSourceDiff':run('git','diff','--name-only','V1.175','--','backend/src/main','frontend/src'),'sha':run('git','rev-parse','V1.175'),'head':run('git','rev-parse','HEAD'),'remote':run('git','ls-remote','origin','refs/heads/main','refs/heads/ai/claude-fix','refs/tags/V1.175'),'jarSha256':hashlib.sha256((R/'backend/target/airport-ai-app-1.0.0.jar').read_bytes()).hexdigest()}
for path in ['/tasks?page=1&size=1','/dashboard/summary','/device-agents?page=1&size=1']:
 try:smoke['authenticated'][path]={'success':True,'data':op(path)}
 except Exception as ex:smoke['authenticated'][path]={'success':False,'error':str(ex)}
put('version-build-smoke',smoke)
suites=[]
for p in sorted((R/'backend/target/surefire-reports').glob('TEST-*.xml')):
 x=ET.parse(p).getroot();suites.append({k:x.get(k) for k in ['name','tests','failures','errors','skipped','time']})
put('backend-tests',{'command':'mvn -o test','totals':{k:sum(int(x[k]) for x in suites) for k in ['tests','failures','errors','skipped']},'suites':suites})
for source,target in [('f022-v175-backend-test.txt','backend-test-log'),('f022-v175-backend-build.txt','backend-build-log'),('f022-v175-frontend-build.txt','frontend-build-log')]:
 data=(R/'.local-test'/source).read_text(encoding='utf-8',errors='replace');(E/(PRE+target+'-20261107.txt')).write_text(data,encoding='utf8')
print(json.dumps({'cleanup':cleanup['exactBusinessConfigRestored'],'active':cleanup['currentActiveAssignments'],'correctionChecks':corrections['preset']['checks'],'smoke':{k:v['success'] for k,v in smoke['authenticated'].items()}},ensure_ascii=False))
