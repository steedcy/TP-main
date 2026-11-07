"""Capture product startup failure, independent checks and per-item blocking chains.
Only reads GPT DB state and local artifacts; no product edits/DB writes/shared stops.
"""
from pathlib import Path
import importlib.util,json,subprocess,hashlib,re,socket,datetime,xml.etree.ElementTree as ET
R=Path(__file__).resolve().parents[3];D=R/'acceptance/stage3';E=D/'evidence';PRE='SRS_F022-V1.176-'
def now():return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
def put(name,x):
 p=E/(PRE+name+'-20261107.json');assert not p.exists();p.write_bytes(json.dumps(x,ensure_ascii=False,indent=2).encode('utf8'))
def git(*args):return subprocess.check_output(['git',*args],cwd=R,encoding='utf8').strip()
# Prior-version module reused ONLY for the read-only SQL/environment transport.
s=importlib.util.spec_from_file_location('sqlhelper',D/'probe-f022-v175-base.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
db=m.prior.p.base.d
secrets=[value for key,value in db.variables.items() if value and any(x in key.upper() for x in ['PASSWORD','ENCRYPTION_KEY','API_KEY','SECRET'])]
for role in ['配置管理员','运行操作员','系统管理员']:
 try:secrets.append(m.l.account(role)[1])
 except Exception:pass
redactions={}
for local,name in [('backend-v176.log','jar-startup-log'),('f022-v176-start-console.txt','startup-helper-console'),('f022-v176-backend-test.txt','backend-test-log'),('f022-v176-backend-build.txt','backend-build-log'),('f022-v176-frontend-build.txt','frontend-build-log'),('f022-v176-container-probe-console.txt','container-probe-console')]:
 text=(R/'.local-test'/local).read_text(encoding='utf8',errors='replace')
 text,n=re.subn(r'(Using generated security password:) [^\r\n]+',r'\1 [REDACTED_EPHEMERAL_TEST_PASSWORD]',text);redactions[name]=n
 for secret in secrets:
  if len(secret)>=6:text=text.replace(secret,'[REDACTED_LOCAL_SECRET]')
 (E/(PRE+name+'-20261107.txt')).write_bytes(text.encode('utf8'))
startup=(E/(PRE+'jar-startup-log-20261107.txt')).read_text(encoding='utf8')
assert 'No default constructor found' in startup and 'PlanValidationService.<init>()' in startup
component=json.loads((E/(PRE+'container-component-20261107.json')).read_text(encoding='utf8'))
assert not component['container']['started']
jar=R/'backend/target/airport-ai-app-1.0.0.jar'
runtime=json.loads((R/'.local-test/runtime-v176.json').read_text())
ports={}
for port in [18129,18117,18132,18133,18134,18135,15179]:
 with socket.socket() as sock:ports[str(port)]=sock.connect_ex(('127.0.0.1',port))==0
state={'at':now(),'scope':'Read-only GPT schema verification after failed startup; no business API, model, adapters or browser launched','schema':m.SC,'redisDb':10,'databaseSelectOne':m.sql('select 1'),'taskCountAndMax':m.rows(f'select count(*) as count,max(id) as max_id from {m.SC}.tasks'),'newRoundDefinitions':m.rows(f"select id,task_name from {m.SC}.task_definitions where task_name like 'G176 %'"),'newRoundTasks':m.rows(f"select id,task_goal from {m.SC}.tasks where task_goal like 'F176_%'"),'ownedAgents':m.rows(f"select a.agent_code,a.work_status,a.current_task_id,d.device_code,d.device_status from {m.SC}.device_agents a join {m.SC}.devices d on d.id=a.device_id where d.device_code like 'G160_F016_%' or d.device_code='G175_F022_FLIGHT' order by a.id"),'triggers':m.sql(f"select count(*) from information_schema.triggers where trigger_schema='{m.SC}'"),'portsListening':ports,'runtimePid':runtime['pid'],'processState':subprocess.check_output(['powershell','-NoProfile','-Command',f"if (Get-Process -Id {runtime['pid']} -ErrorAction SilentlyContinue) {{'present'}} else {{'exited'}}"],encoding='utf8').strip(),'sharedServices':'not stopped/reset; no fixture mutation/restoration necessary','jarSha256':hashlib.sha256(jar.read_bytes()).hexdigest()}
assert not any(ports.values()) and state['processState']=='exited' and not state['newRoundDefinitions'] and not state['newRoundTasks']
assert all(a['current_task_id'] is None and a['device_status']=='INACTIVE' for a in state['ownedAgents'])
put('environment-cleanup',state)
main=R.parent/'tip';before=json.loads((R/'.local-test/f022-v176-main-userfiles-before.json').read_text(encoding='utf8'));after=[]
for path in subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=main).decode('utf8').split('\0'):
 if not path:continue
 p=main/path
 if p.is_file():after.append({'path':path,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
put('version-final-check',{'at':now(),'productSha':git('rev-parse','V1.176'),'claudeHandoffSha':'0ada3a8ef4d2692f61af53868e0a6639cd2806c2','head':git('rev-parse','HEAD'),'remote':git('ls-remote','origin','refs/heads/main','refs/heads/ai/claude-fix','refs/heads/ai/gpt-test','refs/tags/V1.176'),'productSourceDiff':git('diff','--name-only','V1.176','--','backend/src/main','frontend/src'),'mainUserFilesCount':len(before),'mainUserFileHashesUnchanged':all({x['path']:x['sha256'] for x in after}.get(x['path'])==x['sha256'] for x in before),'mainFinalFileCount':len(after),'redactedTemporaryTestPasswords':redactions,'sourceSyntax':'New Python fixtures compiled/parsed separately; prepared business probes never executed or counted'})
suites=[]
for p in sorted((R/'backend/target/surefire-reports').glob('TEST-*.xml')):
 x=ET.parse(p).getroot();suites.append({k:x.get(k) for k in ['name','tests','failures','errors','skipped']})
put('backend-tests',{'command':'mvn -o test','totals':{k:sum(int(x[k]) for x in suites) for k in ['tests','failures','errors','skipped']},'suites':suites})
reason='DEF-S3-117: V1.176 production JAR exits during Spring creation of PlanValidationService (No default constructor found / NoSuchMethodException <init>); no healthy HTTP service. No product code workaround or previous-version runtime substitution allowed.'
items=[]
descriptions={'R01':'三预置族真实列表、删除保护、编辑恢复','R02':'定义无预写步骤及同定义自主不同计划','R03':'定义新增编辑/边界、动态四类型及历史028/029/030','R04':'扩展沿既有页面/协议/能力完整运行','R05':'五步/六步/条件动作/跨版本总额度与实际路径','R06':'不存在/未启用能力拒绝和合法能力对照','R07':'116原反例/合法对照、首次模型请求、HTTP/SQL冻结/指令、基线/重规划与完成判定','R08':'定义创建编辑启停的持久操作记录'}
for k,scope in descriptions.items():items.append({'id':'SRS_F022.'+k,'status':'NT','scope':scope,'blockingChain':reason,'availablePartialCoverage':'454 unit report (452 passed/2 skipped); four seven-argument service observations only for R07; these do not prove current live business steps','requiredToUnblock':'Fix production Spring constructor selection AND inject TaskDefinitionMapper; publish new unique product tag; verify actual JAR healthy before a full new F022 round'})
for k,scope in [('TC-068.S1','定义列表/新增编辑边界及真实配置界面'),('TC-068.S2','动态参数/模型/计划/执行/禁区硬门/停用及历史追溯'),('TC-069.S1','预置族删除保护及参数约束编辑恢复'),('TC-069.S2','重复/缺必填/未知未启用能力的真实保存拒绝')]:items.append({'id':k,'status':'NT','scope':scope,'blockingChain':reason,'attempts':'Production JAR started with same previously healthy GPT environment; database SELECT1 succeeds; independent no-DB Spring context reproduces identical root error; front/backend builds and isolated component observations completed','requiredToUnblock':'Next fixed product release starts normally; then real HTTP/browser remeasurement. No historical P relabeled current.'})
put('per-item-blockers',{'at':now(),'runtimeGate':'F','issue':'DEF-S3-117','rules':{'P':0,'F':0,'NT':8},'steps':{'P':0,'F':0,'NT':4},'items':items,'remainingExecutableRequiredWork':'No live business branch available after service exit; independent compilation, production package, frontend build, no-DB Spring construction and four service-level controls completed. Backend-dependent browser/API/device paths are specifically NT, not skipped because first F.'})
put('DEF-S3-117-minimal',{'tag':'V1.176','productSha':git('rev-parse','V1.176'),'gate':'F','issue':'DEF-S3-117','expected':'Production JAR boots normally; PlanValidationService and its task-definition mapper dependency are instantiated; health UP and authenticated task-definition/task APIs reachable.','actual':'PID'+str(runtime['pid'])+' exits; Spring cannot instantiate PlanValidationService: No default constructor found; root NoSuchMethodException PlanValidationService.<init>().','productionStartupCommand':'python acceptance/stage3/fixtures/start-f022-v176-jar.py (private isolated env only)','isolatedReproducer':'python acceptance/stage3/fixtures/run-f022-v176-container-probe.py (fresh GPT_RUN_SUFFIX)','constructorFacts':component['constructors'],'independentContainer':component['container'],'classification':'V1.176 regression from added unselected public overloaded constructors; @Autowired(required=false) on mapper parameter does not select the constructor.','impact':'All HTTP/browser business paths blocked; DEF116 live retest NT, not closed by manual direct-constructor checks.','fixScope':'Make production Spring constructor choice unambiguous and ensure TaskDefinitionMapper actually injected. Add a real Spring/JAR startup regression; keep seven-argument validation original negative/positive coverage. Do not only select legacy one-argument constructor with mapper=null.'})
print('Captured startup F117, independent evidence, 8 rules/4 steps NT blockers and clean resources')
