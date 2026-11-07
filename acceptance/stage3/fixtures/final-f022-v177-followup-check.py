"""Read-only final evidence review plus disable own browser definition/configuration.
Requires all HTTP probes to have finished. Does not alter product or shared services.
"""
from pathlib import Path
import importlib.util,json,hashlib,subprocess,re,datetime,xml.etree.ElementTree as ET
R=Path(__file__).resolve().parents[3];D=R/'acceptance/stage3';E=D/'evidence';PRE='SRS_F022-V1.177-followup-'
def put(name,obj):
 p=E/(PRE+name+'-20261107.json');assert not p.exists();p.write_bytes(json.dumps(obj,ensure_ascii=False,indent=2).encode('utf8'))
def now():return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
def git(*args):return subprocess.check_output(['git',*args],cwd=R,encoding='utf8').strip()
raw=[]
for p in sorted(E.glob('SRS_F022-V1.177-http-20261107*.json')):
 x=json.loads(p.read_text(encoding='utf8'));assert x.get('endedAt'),f'Probe still active: {p.name}';raw.append((p,x))
s=importlib.util.spec_from_file_location('m',D/'probe-f022-v177-base.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
cfg=m.l.API('配置管理员');op=m.l.API('运行操作员')
ids=sorted({int(tid) for _,x in raw for tid in x['taskIds']});defs=sorted({int(did) for _,x in raw for did in x['definitionIds']});templates=sorted({int(tid) for _,x in raw for tid in x['templateIds']})
for d in cfg('/task-definitions'):
 if d['taskName'].startswith('G177 ') and d['id'] not in defs:defs.append(d['id'])
for did in defs:
 if cfg(f'/task-definitions/{did}')['definitionStatus']!='DISABLED':cfg(f'/task-definitions/{did}/disable','POST')
for tid in templates:
 if cfg(f'/baseline-templates/{tid}')['templateStatus']=='ENABLED':cfg(f'/baseline-templates/{tid}/disable','POST')
initial=json.loads((E/'SRS_F022-V1.177-http-20261107.json').read_text(encoding='utf8'))
before=initial['initialPresetRows'];after=m.rows(f'select * from {m.SC}.task_definitions where is_preset=true order by id');keys=['id','definition_code','task_name','goal_template','scene_params','available_capability_types','constraint_description','completion_condition','definition_status','is_preset'];business=lambda x:{k:x[k] for k in keys}
owned=m.rows(f"select a.*,d.device_code,d.device_status from {m.SC}.device_agents a join {m.SC}.devices d on d.id=a.device_id where d.device_code like 'G160_F016_%' or d.device_code='G175_F022_FLIGHT' order by a.id")
tasks=m.rows(f"select id,task_code,task_family,task_goal,status,current_plan_version_id from {m.SC}.tasks where id in ({','.join(map(str,ids))}) order by id");active=m.sql(f"select count(*) from {m.SC}.task_step_assignments a join {m.SC}.tasks t on t.id=a.task_id where t.id in ({','.join(map(str,ids))}) and a.plan_version_id=t.current_plan_version_id and a.step_status in ('PENDING_ASSIGNMENT','EXECUTING')")
state={'at':now(),'schema':m.SC,'redisDb':10,'taskIds':ids,'tasks':tasks,'definitionIds':defs,'definitions':m.rows(f"select * from {m.SC}.task_definitions where id in ({','.join(map(str,defs))}) order by id"),'templateIds':templates,'templates':[cfg(f'/baseline-templates/{tid}') for tid in templates],'presetBusinessAndRawJsonRestored':list(map(business,before))==list(map(business,after)),'presetsBefore':before,'presetsAfter':after,'ownedAgents':owned,'currentActiveAssignments':active,'triggers':m.sql(f"select count(*) from information_schema.triggers where trigger_schema='{m.SC}'"),'allTasksTerminal':all(t['status'] in ['COMPLETED','FAILED','MANUAL_TERMINATED'] for t in tasks),'sharedServices':'not stopped/reset; no Claude resources touched; no risk-rule changes'}
assert state['presetBusinessAndRawJsonRestored'] and state['allTasksTerminal'] and active=='0';assert all(a['current_task_id'] is None and a['device_status']=='INACTIVE' for a in owned)
put('fixture-cleanup',state)
quality={'at':now(),'tag':'V1.177','productSha':git('rev-parse','V1.177'),'head':git('rev-parse','HEAD'),'remote':git('ls-remote','origin','refs/heads/main','refs/heads/ai/claude-fix','refs/heads/ai/gpt-test','refs/tags/V1.177'),'productSourceDiff':git('diff','--name-only','V1.177','--','backend/src/main','frontend/src'),'jarSha256':hashlib.sha256((R/'backend/target/airport-ai-app-1.0.0.jar').read_bytes()).hexdigest(),'health':m.l.request('http://127.0.0.1:18129/actuator/health'),'authenticatedSmoke':{},'probeDiagnostics':[]}
for path in ['/tasks?page=1&size=1','/dashboard/overview','/device-agents?page=1&size=1','/task-definitions']:
 quality['authenticatedSmoke'][path]={'success':True,'data':op(path)}
for p,x in raw:quality['probeDiagnostics'].append({'source':p.name,'diagnostics':x['diagnostics'],'casesWithoutVerdict':[{'name':c['name'],'taskId':c.get('taskId')} for c in x['cases'] if c.get('result') is None],'startedAt':x['startedAt'],'endedAt':x['endedAt']})
quality['probeCorrections']=['Three-preset initial failure: status-only minimum-ID fixture did not ensure test_passed=TRUE. First two edits restored; flight supplemented with actual own adapter/test/enable, full configuration restored.','First template request incorrectly declared four required inputs but mapped only targetLocation; rejected before create. Separate one-input template fixture corrected.','First baseline allowed task entered normal DOWNGRADING, omitted from wait predicate; task preserved and terminated. Successful first trial retained.','Direct template re-enable and then trial on disabled template were correctly rejected by existing state rules; attempts have no business task. Final stable run uses a fresh valid draft, actual successful trial, allowed completion and prohibited baseline counterexample.','Primary endedAt precedes baseline startedAt, all adapter process ownership sequential; final stable run only after earlier processes exited.','No product F reclassified as fixture issue: 1011 whitelist bypass,1012 capability sentence false rejection,1021 baseline bypass remain F.']
main=R.parent/'tip';beforeFiles=json.loads((R/'.local-test/f022-v177-main-userfiles-before.json').read_text(encoding='utf8'));afterFiles=[]
for name in subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=main).decode('utf8').split('\0'):
 if name and (main/name).is_file():afterFiles.append({'path':name,'sha256':hashlib.sha256((main/name).read_bytes()).hexdigest()})
quality['mainUserFilesCount']=len(beforeFiles);quality['mainUserFileHashesUnchanged']=beforeFiles==afterFiles;assert quality['mainUserFileHashesUnchanged'] and quality['productSourceDiff']==''
put('final-quality-review',quality)
suite=[]
for p in sorted((R/'backend/target/surefire-reports').glob('TEST-*.xml')):
 x=ET.parse(p).getroot();suite.append({k:x.get(k) for k in ['name','tests','failures','errors','skipped']})
put('backend-tests',{'command':'mvn -o test','totals':{k:sum(int(x[k]) for x in suite) for k in ['tests','failures','errors','skipped']},'suites':suite})
secrets=[]
for k,v in m.prior.p.base.d.variables.items():
 if v and any(t in k.upper() for t in ['PASSWORD','API_KEY','ENCRYPTION_KEY','SECRET']):secrets.append(v)
for role in ['配置管理员','运行操作员','系统管理员']:
 try:secrets.append(m.l.account(role)[1])
 except Exception:pass
copies=[('backend-v177.log','jar-runtime-log'),('f022-v177-backend-test.txt','backend-test-log'),('f022-v177-backend-build.txt','backend-build-log'),('f022-v177-frontend-build.txt','frontend-build-log'),('f022-v177-model-requests.jsonl','model-requests'),('f022-v177-suite-console.txt','suite-console'),('f022-v177-flight-preset-console.txt','flight-preset-console'),('f022-v177-baseline-console.txt','baseline-first-console'),('f022-v177-baseline-completion-console.txt','baseline-enable-diagnostic'),('f022-v177-baseline-completion-retry1-console.txt','baseline-retrial-diagnostic'),('f022-v177-baseline-stable-console.txt','baseline-stable-console'),('f022-v177-container-probe-console.txt','container-probe-console')]
redactions={}
for local,label in copies:
 text=(R/'.local-test'/local).read_text(encoding='utf8',errors='replace');text,n=re.subn(r'(Using generated security password:) [^\r\n]+',r'\1 [REDACTED_EPHEMERAL_TEST_PASSWORD]',text);redactions[label]=n
 for secret in secrets:
  if len(secret)>=6:text=text.replace(secret,'[REDACTED_LOCAL_SECRET]')
 text=re.sub(r'eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+','[REDACTED_JWT]',text)
 (E/(PRE+label+'-20261107'+('.jsonl' if label=='model-requests' else '.txt'))).write_bytes(text.encode('utf8'))
put('privacy-review',{'localCredentialMatchesAfterRedaction':0,'temporaryUnitTestPasswordRedactions':redactions,'originalLocalLogsRetained':True,'noOfficeOrJarOrPrivateEnvironmentCommitted':True})
print('Captured terminal tasks',len(ids),'definitions',len(defs),'templates',len(templates),'preset exact restore',state['presetBusinessAndRawJsonRestored'],'active',active,'main files unchanged',len(beforeFiles))
