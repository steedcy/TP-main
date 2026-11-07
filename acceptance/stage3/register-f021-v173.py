"""Build traceable effective verdicts without changing any raw observation.
Register only F021 rows, preserve history and original probe diagnostics.
Run after resource cleanup, before evidence commit. No product changes.
"""
import json,csv,hashlib,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'acceptance/stage3';E=D/'evidence';PREFIX='SRS_F021-V1.173-'
def read(name):return json.loads((E/(PREFIX+name+'-20261107.json')).read_text(encoding='utf-8-sig'))
first=read('http');second=json.loads((E/(PREFIX+'http-20261107-supplement.json')).read_text(encoding='utf8'));ui=read('ui');offline=read('offline-assertion-correction')
groups=[]
corrections={x['taskId']:x for x in second['corrections']}
for c in first['cases']:
 if 'checks' not in c and c['taskId'] not in corrections:continue
 checks=dict(corrections.get(c['taskId'],c)['checks'])
 if c['taskId']==923:
  checks.update(next(x['checks'] for x in second['cases'] if x['name']=='structured-event-operation-audit-original-counterexample'))
 groups.append({'name':c['name'],'taskIds':[c['taskId']],'checks':checks,'source':PREFIX+'http-20261107.json','correction':corrections.get(c['taskId'])})
for c in second['cases']:
 if c['taskId']==923 or c['taskId']==948:continue
 checks=dict(c['checks'])
 if c['taskId']==946:checks=offline['correctedChecks']
 ids=[c['taskId']]
 if c['taskId']==947:ids.append(948);checks['otherControlCompleted']=next(x for x in second['cases'] if x['taskId']==948)['checks']['controlCompleted']
 groups.append({'name':c['name'],'taskIds':ids,'checks':checks,'source':PREFIX+'http-20261107-supplement.json'})
for g in groups:g['result']='P' if all(g['checks'].values()) else 'F'
uicases=[]
for c in ui['cases']:
 checks=dict(c['checks'])
 for correction in ui.get('corrections',[]):
  if correction['case']==c['name']:checks[correction['assertion']]=correction['corrected']
 uicases.append({'name':c['name'],'checks':checks,'result':'P' if all(checks.values()) else 'F'})
assert len(groups)==20 and sum(g['result']=='F' for g in groups)==1
assert all(x['result']=='P' for x in uicases)
assert read('process-cleanup')['allReleased']
tests=[]
for f in (R/'backend/target/surefire-reports').glob('TEST-*.xml'):
 x=ET.parse(f).getroot();tests.append({'name':x.attrib['name'],**{k:int(x.attrib[k]) for k in ['tests','failures','errors','skipped']}})
summary={k:sum(x[k] for x in tests) for k in ['tests','failures','errors','skipped']};assert summary==dict(tests=433,failures=0,errors=0,skipped=2)
for local,pub in [('f021-v173-backend-build.txt','backend-build'),('f021-v173-frontend-build.txt','frontend-build'),('f021-v173-round-console.txt','round-console'),('f021-v173-supplement-console.txt','supplement-console')]:
 b=(R/'.local-test'/local).read_bytes();s=b.decode('utf-16') if b.startswith((b'\xff\xfe',b'\xfe\xff')) else b.decode('utf8',errors='replace');(E/(PREFIX+pub+'-20261107.txt')).write_text(s,encoding='utf8')
(E/(PREFIX+'backend-tests-20261107.json')).write_text(json.dumps({'summary':summary,'suites':tests},indent=2),encoding='utf8')
log=(R/'.local-test/backend-v173.log').read_text(encoding='utf8',errors='replace')
(E/(PREFIX+'jar-runtime-20261107.txt')).write_text('\n'.join(x for x in log.splitlines() if any(w in x for w in ['Starting AirportAiApplication','Tomcat started on port','Started AirportAiApplication','Successfully applied','Schema "tip_gpt_']))+'\n',encoding='utf8')
ruleReasons={
 'R01':'918缺失/null/空串/空白/201字/缺确认/false均400且完整业务快照不变；919合法200字、1字trim持久化；936真实UI空白及未确认禁用、201输入限制200、取消无状态变更、确认后成功。',
 'R02':'922待承接终止后迟到接受、923执行中终止后迟到反馈均不触发后续步骤；936真实UI首步完成/后二步冻结；947终止预选仅冻结自身。',
 'R03':'923单设备和945双设备取消消息与持久编号逐项对应、取消与承接/执行编号独立；946离线取消DELIVERY_FAILED持久化且失败设备摘要准确。',
 'R04':'BL006现有安全门：925未确认BUSY保留，真实默认60秒超时提示；OFFLINE IDLE和ONLINE BUSY不释放，相关ONLINE IDLE确认/幂等；945双设备与946离线执行设备恢复确认释放，947不清他任务占用。',
 'R05':'936真实弹窗明确业务终止非设备安全急停、已完成结果不回滚不补偿及现场核实责任；截图/DOM与禁用行为实测。',
 'R06':'923与936真实三步流程首步COMPLETED及outputParams保持；未完成两步FROZEN，不回滚/补偿，正常两步921及其他任务948完成对照。',
 'R07':'923重试规划/转基线/置失败409，澄清/取消/重复终止拒绝；无新业务及状态恢复，925超时/空闲恢复仍终态；六合法状态200与三终态409均当前HTTP，九状态UI入口正确。禁止绕过操作按既有F013返回400/4110并留拦截记录。',
 'R08':'DEF-S3-059仍F：923 TASK_TERMINATED.detail整体非JSON（说明文字+JSON数组），不能json.loads且无对象级deviceCancelResults；TaskEvent.getDetail仅别名detailSummary。operation_logs.detail有效结构化、945多设备编码/编号、超时/确认事件均当前子范围P，但不足以关闭事件完整JSON缺口。'}
rules={f'SRS_F021.{k}':{'status':'F' if k=='R08' else 'P','actual':v} for k,v in ruleReasons.items()}
steps={
 'TC-066.S1':{'status':'P','actual':ruleReasons['R01']+' '+ruleReasons['R05']},
 'TC-066.S2':{'status':'P','actual':'923/936完成结果保留、未完成冻结、独立取消/空闲确认、终态硬门禁；945双设备、946离线恢复、947跨任务保护，BL006不提前释放。'},
 'TC-066.S3':{'status':'F','actual':ruleReasons['R08']},
 'TC-067.S1':{'status':'P','actual':'920及937～941六种合法状态200人工终止；942～944三终态409且业务快照不变；927～935真实浏览器六入口有/三终态无。状态专用SQL夹具不冒充自然生命周期。'},
 'TC-067.S2':{'status':'P','actual':'925真实默认60秒未响应转TIMED_OUT，DEVICE_CANCEL_NO_CONFIRMATION含设备/指令号，UI明确保留占用待核查，恢复ONLINE IDLE后CONFIRMED_IDLE/释放且不恢复执行；OFFLINE IDLE/ONLINE BUSY拒绝释放，重复确认幂等。按已有BL006合并解读，不以旧立即释放字面取消安全门。'}}
index={'tag':first['tag'],'productSha':first['productSha'],'handoffSha':first['handoffSha'],'executionBaseline':'V2.4 + existing BL006','timezone':'Asia/Shanghai','startedAt':first['startedAt'],'endedAt':second['endedAt'],'verdict':'READY_FOR_CLAUDE','ruleCounts':{'P':7,'F':1,'NT':0},'stepCounts':{'P':4,'F':1,'NT':0},'rules':rules,'steps':steps,'businessGroups':groups,'businessGroupCounts':{'total':20,'P':19,'F':1,'assertions':sum(len(g['checks']) for g in groups),'failedAssertions':sum(not v for g in groups for v in g['checks'].values())},'ui':{'browser':'IAB Chromium','groups':uicases,'stateGateCount':9,'rawDiagnosticsAndCorrections':PREFIX+'ui-20261107.json'},'backendTests':summary,'taskCount':32,'taskProvenance':{'actualLifecycleProtocolTasks':11,'explicitSQLStatusFixtures':21,'diagnosticIncompleteTasks':[924,926],'allRawTasksPreserved':True,'multiDeviceQualification':'945 first device natural execution, second same-task occupation explicitly SQL seeded; not a naturally parallel plan'},'historicalBusinessPassesReused':0,'historicalEvidence':'F020 V1.172 and older F021 observations are comparison only, no current P substitution','issues':{'DEF-S3-059':'open residual; operation detail fixed, event whole JSON fails','newDefects':[],'historicalR04':'No-response monitor gap covered by current925 + UI; original historical F preserved'},'probeCorrections':{'jsonAlreadyDict':'Initial 5diagnostics retained; adequate raw observations re-evaluated or missing assertions supplemented','forbiddenBypass':'400/4110 and denial events expected by existing F013, not409/no-event','offlineCandidate':'946 naturally switched candidate after offline; correlate actual executing device instead of assuming one cancel/all cancels confirmed; original F and correction both retained','ui':'wrapper maxlength lookup and pre-fetch body text corrected from actual inputLength200 and stable two frozen rendered rows','cleanupQuery':'Initial read-only query used status instead of definition_status; corrected read-only fixture inspector passed'},'builds':{'backend':'mvn -o clean test package: success; actual JAR health UP + authenticated business HTTP','frontend':'npm run build: success3271 modules; chunk-size advisory retained'},'cleanup':PREFIX+'cleanup-smoke-20261107.json','processCleanup':PREFIX+'process-cleanup-20261107.json','main':{'sha':'a8d6409964085e4a500bd399bb1a6b4f6bfb2918','merged':False,'pr':None},'minimalFailureCheckpoint':'fb44f7a','report':'SRS_F021-V1.173-整轮独立复测与统一交修.md','limitations':['Controlled model/HTTP synthetic adapters; no commercial-model or physical emergency-stop certification','SQL status and multi-occupancy fixtures explicitly separated from natural lifecycle','433unit reports include2pre-existing skipped tests; not business NT','Does not accept later requirements, three end-to-end core scenarios or all95cases']}
(E/(PREFIX+'complete-verification-20261107.json')).write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf8')
evidence=';'.join('acceptance/stage3/evidence/'+PREFIX+n for n in ['complete-verification-20261107.json','http-20261107.json','http-20261107-supplement.json','ui-20261107.json','offline-assertion-correction-20261107.json'])
for filename,keycol,items in [('rules.csv','ruleId',rules),('steps.csv','stepId',steps)]:
 path=D/filename
 with path.open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
 for row in rows:
  if row[keycol] not in items:continue
  item=items[row[keycol]];row['status']=item['status'];row['evidence']+=';'+evidence;row['issue']='DEF-S3-059' if item['status']=='F' else ''
  if filename=='steps.csv':row['observedAt']='2026-11-07';row['actual']+='；【V1.173 / 761bd0b / 当前实测，历史原文保留】'+item['actual']
  else:row['verifiedBy']='TC-066.S1' if row['ruleId'].endswith(('R01','R05')) else 'TC-066.S3' if row['ruleId'].endswith('R08') else 'TC-066.S2'
 with path.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
path=D/'issues.csv'
with path.open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
for row in rows:
 if row['编号']=='DEF-S3-059':row['状态']='V1.173 F021整轮仍F：事件detail整体非JSON；操作日志与多设备取消子范围P';row['事实']+='；【V1.173独立整轮】'+ruleReasons['R08'];row['证据']+=';'+evidence;row['阶段4动作']='保留059编号与旧失败；将TASK_TERMINATED事件detail提供为完整JSON对象（reason/previousStatus/operator/deviceCancelResults）；不要仅给detailSummary增加别名。保持人类可读时间线、取消确认安全门及多设备/离线/终态通过行为。发新唯一标签后F021整轮复测。'
with path.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
path=D/'阶段3-复测进度.md';t=path.read_text(encoding='utf-8-sig');pos=t.index('\n')+1;t=t[:pos]+'\n- **2026-11-07 / F021 V1.173 / V2.4：READY_FOR_CLAUDE**。8规则7P/1F/0NT、正式5步骤4P/1F/0NT，当前全部适用项实测/历史P复用0；059事件整体JSON残留统一交修，操作日志/多设备/离线恢复/默认60秒超时/终态/真实界面子范围P。32持久任务（11实际协议流程、21显式SQL状态夹具），20去重业务组19P/1F、4真实IAB界面组及9状态入口；433报告431通过2原有跳过、构建/实际JAR。探针诊断与更正全保留，2定义/3设备停用，分配占用及注入0、3自有进程树/6端口释放；main保持a8d6409，无本轮合入/PR，不推进F022。报告`SRS_F021-V1.173-整轮独立复测与统一交修.md`。\n'+t[pos:];path.write_text(t,encoding='utf8')
report=f'''# SRS_F021 V1.173 整轮独立复测与统一交修

**整项未通过：READY_FOR_CLAUDE。规则7P/1F/0NT，TC-066/TC-067五步骤4P/1F/0NT。** 当前需求全部适用项已实测，历史P复用0。仅DEF-S3-059仍有事件JSON残留；未修改产品代码、未放宽业务基线、未合main、无PR，不推进F022。

固定产品`761bd0b51af380c19b06357f815acda751905a3b` / `V1.173`，Claude文档`f00536c595d291a495a5f7e55561dbf08823ac8c`。已核对远端分支、标签解引用和提交链，标签不移动。上一F020已合main，当前main仍`a8d6409964085e4a500bd399bb1a6b4f6bfb2918`。测试工作区`C:/Users/savy/Desktop/TIP-main/tip-gpt-f013` / `ai/gpt-test`，2026-11-07 Asia/Shanghai，V2.4整轮策略及现有BL006；初始状态/资源与差异见`evidence/{PREFIX}version-scope-20261107.json`。

| 规则 | 本轮结果 | 当前依据 |
|---|---|---|
'''
for k,v in rules.items():report+=f"| {k} | {v['status']} | {v['actual']} |\n"
report+='\n| 正式步骤 | 本轮结果 | 当前依据 |\n|---|---|---|\n'
for k,v in steps.items():report+=f"| {k} | {v['status']} | {v['actual']} |\n"
report+=f'''
缺陷059复现：真实三步任务923（任务号TASK-20261107-0913）先完成步骤1，再接受执行步骤2；POST `/api/v1/tasks/923/terminate`，原因`F173 independent safe termination`、`confirmed=true`；GET事件选择`TASK_TERMINATED`并整体解析`detail`。实际返回说明文字加JSON数组，而非含`deviceCancelResults`的完整对象，`json.loads`在首字符失败。SQL持久事件同为说明文字，`TaskEvent.getDetail`仅返回`detailSummary`。操作日志的非空对象已修，945双设备编码/指令编号/取消结果也已实证，不将这些子范围P当作059整体关闭。保留原编号，不重复建缺陷。最小证据已先推送检查点`fb44f7a`；完整证据和正式交接SHA由HANDOFF后续提交记录。

修复建议：为终止事件提供完整的JSON详情（含原因、前状态、操作者、设备结果及取消编号），同时保留人类可读时间线；核对事件持久化与REST输出，不能只加别名。取消结果为当时请求结果，最终空闲确认仍由后续相关事件/命令关联，不伪写物理设备已安全急停。

本轮20个去重HTTP/SQL/协议观察组19P/1F，共{index['businessGroupCounts']['assertions']}条明确断言，失败1条；UI四组经原始诊断更正全部P，包含九种状态入口。UI任务936与HTTP对同一实际终止共证，不累加业务执行次数；同版重新解析923/919/920已有原始观察不算重跑。32持久任务=11实际协议/生命周期任务+21显式SQL状态夹具；924/926因探针中断仅部分取证，完整多设备/离线缺失断言由945/946补齐，其任务和原始诊断保留。945第二设备占用是明确SQL夹具，不宣称自然并行规划。六种状态HTTP门禁和九种UI入口是状态覆盖，不冒充九个自然生命周期。

后端`mvn -o clean test package`433项报告：431通过、2原有跳过、0失败/错误；前端`npm run build`成功（体积建议原样保留）。实际启动本轮打包JAR，健康UP、登录与关键业务HTTP/SQL、合成设备消息/回执及IAB Chromium界面均已执行。单测、真实HTTP、持久化、浏览器和合成设备分层登记；未覆盖商业模型和物理设备急停认证。正常两步921、另一任务948执行完成及配置管理员403/匿名401是必要核心冒烟/邻接。历史F020等只作对照，无历史业务P替代当前实测。

既有BL006明确适用于F021：终止立即冻结业务，执行设备需相关ONLINE IDLE确认后释放。TC067旧“超时释放”与现有受控补充合并阅读；925真实默认60秒超时后保留BUSY并提示现场核实，之后相关ONLINE IDLE释放，不以字面无条件释放破坏安全门。无新业务标准变更。历史DEF-R04-001缺少无响应处理的原失败保留，当前监控/提示子范围已实证闭环。

所有探针错误和更正均保留：操作日志JSON已为对象却再次loads（五次诊断）；F013禁止绕过动作应400/4110并追加拦截事件，而非笼统409和事件不变；946离线自然切换候选后会有两条取消，按真正执行设备匹配DELIVERY_FAILED→CONFIRMED_IDLE，未接受候选不冒充执行确认；UI组件包装器maxlength属性读取及关闭弹窗后立即读文本的时序错误分别由实际输入200和稳定两冻结行更正。原F/原诊断均未删除，也未把探针错误交给Claude。

GPT自有schema`tip_gpt_f006_v118_20261030`、Redis10、后端18129、模型18117、适配器18132～18134、Vite15179。两轮探针退出后2定义DISABLED、3设备INACTIVE、活跃分配0、设备占用0、注入触发器0；无规则/模板变更，32任务/计划/失败全部保留。核对命令归属后停止3自有进程树，六端口监听0，共享PG/Redis及Claude资源未动。清理详情见`evidence/{PREFIX}cleanup-smoke-20261107.json`和`process-cleanup`证据。

总索引`evidence/{PREFIX}complete-verification-20261107.json`；原始HTTP两文件、UI JSON/6截图/9状态DOM与超时DOM、最小反例、离线断言更正、构建/433项报告、资源/版本与SHA256 manifest共同构成证据。原台账快照随本轮保留。完整证据先提交推送，再顺序更新HANDOFF/ROADMAP并引用实际证据SHA。下一Claude接收`ai/gpt-test`完整证据，只修059残留及直接影响后发新唯一标签，再F021整轮复测。此结论不表示后续需求、三核心场景或95项整体验收已通过。
'''
(D/'SRS_F021-V1.173-整轮独立复测与统一交修.md').write_text(report,encoding='utf8')
files=sorted(E.glob(PREFIX+'*'))+[D/'SRS_F021-V1.173-整轮独立复测与统一交修.md']+list(D.glob('*f021-v173*.py'))+list((D/'fixtures').glob('*f021-v173*'))
manifest=[{'path':str(f.relative_to(R)).replace('\\','/'),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in files if 'evidence-manifest' not in f.name]
(E/(PREFIX+'evidence-manifest-20261107.json')).write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'groups':index['businessGroupCounts'],'rules':index['ruleCounts'],'steps':index['stepCounts'],'backend':summary,'manifestEntries':len(manifest)},ensure_ascii=False))
