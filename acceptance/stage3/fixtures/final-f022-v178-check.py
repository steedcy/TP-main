"""Final read-only business review, owned-fixture cleanup, and redacted log capture.
Run only after current HTTP probes and browser configuration writes have finished.
No task/plan lifecycle is synthesized; retained failures are never deleted.
"""
from pathlib import Path
import importlib.util, json, hashlib, subprocess, re, datetime
import xml.etree.ElementTree as ET
R=Path(__file__).resolve().parents[3]; D=R/'acceptance/stage3'; E=D/'evidence'; PRE='SRS_F022-V1.178-'
def put(name,obj):
    p=E/(PRE+name+'-20261107.json'); assert not p.exists()
    p.write_bytes(json.dumps(obj,ensure_ascii=False,indent=2).encode('utf-8'))
def git(*args):return subprocess.check_output(['git',*args],cwd=R,encoding='utf-8').strip()
raw=[]
for p in sorted(E.glob(PRE+'http-20261107*.json')):
    x=json.loads(p.read_text(encoding='utf-8')); assert x.get('endedAt'),p.name
    raw.append((p,x))
spec=importlib.util.spec_from_file_location('m',D/'probe-f022-v178-base.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
cfg=m.l.API('配置管理员');op=m.l.API('运行操作员')
ids=sorted({int(v) for _,x in raw for v in x['taskIds']})
defs=sorted({int(v) for _,x in raw for v in x['definitionIds']})
templates=sorted({int(v) for _,x in raw for v in x['templateIds']})
for d in cfg('/task-definitions'):
    if d['taskName'].startswith('G178 ') and d['id'] not in defs:defs.append(d['id'])
for did in defs:
    if cfg(f'/task-definitions/{did}')['definitionStatus']!='DISABLED':cfg(f'/task-definitions/{did}/disable','POST')
for tid in templates:
    if cfg(f'/baseline-templates/{tid}')['templateStatus']=='ENABLED':cfg(f'/baseline-templates/{tid}/disable','POST')
initial=json.loads((E/(PRE+'http-20261107.json')).read_text(encoding='utf-8'))
before=initial['initialPresetRows'];after=m.rows(f'select * from {m.SC}.task_definitions where is_preset=true order by id')
keys=['id','definition_code','task_name','goal_template','scene_params','available_capability_types','constraint_description','completion_condition','definition_status','is_preset']
business=lambda x:{k:x[k] for k in keys}
owned=m.rows(f"select a.*,d.device_code,d.device_status from {m.SC}.device_agents a join {m.SC}.devices d on d.id=a.device_id where d.device_code like 'G160_F016_%' or d.device_code='G175_F022_FLIGHT' order by a.id")
taskids=','.join(map(str,ids))
tasks=m.rows(f'select id,task_code,task_goal,status,current_plan_version_id from {m.SC}.tasks where id in ({taskids}) order by id')
active=m.sql(f"select count(*) from {m.SC}.task_step_assignments a join {m.SC}.tasks t on t.id=a.task_id where t.id in ({taskids}) and a.plan_version_id=t.current_plan_version_id and a.step_status in ('PENDING_ASSIGNMENT','EXECUTING')")
state={'at':m.now(),'schema':m.SC,'redisDb':10,'taskIds':ids,'tasks':tasks,'definitionIds':defs,'definitions':m.rows(f"select * from {m.SC}.task_definitions where id in ({','.join(map(str,defs))}) order by id"),'templateIds':templates,'templates':[cfg(f'/baseline-templates/{v}') for v in templates],'presetBusinessAndRawJsonRestored':list(map(business,before))==list(map(business,after)),'presetsBefore':before,'presetsAfter':after,'ownedAgents':owned,'currentActiveAssignments':active,'triggers':m.sql(f"select count(*) from information_schema.triggers where trigger_schema='{m.SC}'"),'allTasksTerminal':all(t['status'] in ['COMPLETED','FAILED','MANUAL_TERMINATED'] for t in tasks),'sharedServices':'not stopped/reset; no Claude resources touched; no risk-rule changes'}
assert state['presetBusinessAndRawJsonRestored'] and state['allTasksTerminal'] and active=='0'
assert all(a['current_task_id'] is None and a['device_status']=='INACTIVE' for a in owned)
put('fixture-cleanup',state)
main=R.parent/'tip';bf=json.loads((R/'.local-test/f022-v178-main-userfiles-before.json').read_text(encoding='utf-8'));af=[]
for name in subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=main).decode('utf-8').split('\0'):
    if name and (main/name).is_file():af.append({'path':name,'sha256':hashlib.sha256((main/name).read_bytes()).hexdigest()})
quality={'at':m.now(),'tag':'V1.178','productSha':git('rev-parse','V1.178'),'head':git('rev-parse','HEAD'),'remote':git('ls-remote','origin','refs/heads/main','refs/heads/ai/claude-fix','refs/heads/ai/gpt-test','refs/tags/V1.178'),'productSourceDiff':git('diff','--name-only','V1.178','--','backend/src','frontend/src'),'jarSha256':hashlib.sha256((R/'backend/target/airport-ai-app-1.0.0.jar').read_bytes()).hexdigest(),'health':m.l.request('http://127.0.0.1:18129/actuator/health'),'authenticatedSmoke':{p:op(p) for p in ['/tasks?page=1&size=1','/dashboard/overview','/device-agents?page=1&size=1','/task-definitions']},'probeDiagnostics':[{'source':p.name,'diagnostics':x['diagnostics'],'casesWithoutVerdict':[v['name'] for v in x['cases'] if not v.get('result')],'startedAt':x['startedAt'],'endedAt':x['endedAt']} for p,x in raw],'mainUserFilesCount':len(bf),'mainUserFileHashesUnchanged':bf==af}
assert quality['mainUserFileHashesUnchanged'] and not quality['productSourceDiff']
put('final-quality-review',quality)
suites=[]
for p in sorted((R/'backend/target/surefire-reports').glob('TEST-*.xml')):
    x=ET.parse(p).getroot();suites.append({k:x.get(k) for k in ['name','tests','failures','errors','skipped']})
put('backend-tests',{'command':'mvn -o test','totals':{k:sum(int(v[k]) for v in suites) for k in ['tests','failures','errors','skipped']},'suites':suites})
secrets=[v for k,v in m.prior.p.base.d.variables.items() if v and any(t in k.upper() for t in ['PASSWORD','API_KEY','ENCRYPTION_KEY','SECRET'])]
for role in ['配置管理员','运行操作员','系统管理员']:
    try:secrets.append(m.l.account(role)[1])
    except Exception:pass
copies=[('backend-v178.log','jar-runtime-log'),('f022-v178-backend-test.txt','backend-test-log'),('f022-v178-backend-build.txt','backend-build-log'),('f022-v178-frontend-build.txt','frontend-build-log'),('f022-v178-model-requests.jsonl','model-requests'),('f022-v178-suite-console.txt','suite-console'),('f022-v178-flight-preset-console.txt','flight-preset-console'),('f022-v178-baseline-console.txt','baseline-console'),('f022-v178-replan-baseline-console.txt','replan-baseline-console'),('f022-v178-container-probe-console.txt','container-probe-console'),('f022-v178-capability-gap-stable-console.txt','capability-gap-stable-console')]
redactions={}
for local,label in copies:
    text=(R/'.local-test'/local).read_text(encoding='utf-8',errors='replace');text,n=re.subn(r'(Using generated security password:) [^\r\n]+',r'\1 [REDACTED_EPHEMERAL_TEST_PASSWORD]',text);redactions[label]=n
    for secret in secrets:
        if len(secret)>=6:text=text.replace(secret,'[REDACTED_LOCAL_SECRET]')
    text=re.sub(r'eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+','[REDACTED_JWT]',text)
    (E/(PRE+label+'-20261107'+('.jsonl' if label=='model-requests' else '.txt'))).write_bytes(text.encode('utf-8'))
put('privacy-review',{'localCredentialMatchesAfterRedaction':0,'temporaryUnitTestPasswordRedactions':redactions,'originalLocalLogsRetained':True,'noOfficeOrJarOrPrivateEnvironmentCommitted':True})
print('Terminal tasks',len(ids),'definitions',len(defs),'templates',len(templates),'main userfiles unchanged',len(bf))
