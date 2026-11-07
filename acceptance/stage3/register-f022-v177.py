"""Finalize current full F022 observations; preserve all prior versions and diagnostics."""
from pathlib import Path
import json,csv,hashlib
R=Path(__file__).resolve().parents[2];D=R/'acceptance/stage3';E=D/'evidence';PRE='SRS_F022-V1.177-'
SHA='cf99ef9c50ac65ffbff19ad492eb87c86b2299e8';HANDOFF='521b6aafaec3e988f6419911857b486a9ab78c29';MAIN='413e1b3aee20116bb612ed1d4dac96e9937cde0e'
def get(suffix):return json.loads((E/(PRE+suffix)).read_text(encoding='utf8'))
def put(name,value):
 p=E/(PRE+name+'-20261107.json');assert not p.exists();p.write_bytes(json.dumps(value,ensure_ascii=False,indent=2).encode('utf8'))
main=get('http-20261107.json');base=get('http-20261107-baseline-stable.json');tail=get('http-20261107-replan-baseline.json');flight=get('http-20261107-flight-preset.json');ui=get('ui-20261107.json');state=get('followup-fixture-cleanup-20261107.json');tests=get('backend-tests-20261107.json');container=get('container-component-20261107.json')
assert container['container']=={'mapperInjected':True,'started':True} and all(c['result']=='P' for c in container['componentObservations'])
assert tests['totals']=={'tests':456,'failures':0,'errors':0,'skipped':2}
assert len(ui['groups'])==18 and all(c['result']=='P' for c in ui['groups']) and ui['consoleErrorCount']==0
assert state['allTasksTerminal'] and state['currentActiveAssignments']=='0' and state['presetBusinessAndRawJsonRestored']
assert get('process-cleanup-20261107.json')['allReleased'] and get('followup-process-cleanup-20261107.json')['allReleased']
find=lambda data,name:next(c for c in data['cases'] if c['name']==name)
prefix=find(main,'116-whitelist-shorter-valid-area');cap=find(main,'116-capability-sentence-legal');baseBad=find(base,'baseline-location-prohibited');tailBad=find(tail,'replan-baseline-prohibited-tail')
assert prefix['actualProhibitedExecute']['inputParams']['targetLocation']=='F2_TEST'
assert baseBad['unexpectedExecute']['inputParams']['targetLocation']=='F2_TEST_GATE'
assert tailBad['unexpectedBaselineTailExecute']['inputParams']['targetLocation']=='F2_TEST_GATE'
assert all(c['result']=='F' for c in [prefix,cap,baseBad,tailBad])
failureRows=[]
for source,c in [('http-20261107.json',prefix),('http-20261107.json',cap),('http-20261107-baseline-stable.json',baseBad),('http-20261107-replan-baseline.json',tailBad)]:
 o=c['after'];failureRows.append({'source':PRE+source,'name':c['name'],'taskId':c['taskId'],'request':c['request'],'definition':c['definition'],'checks':c['checks'],'taskBeforeCleanup':o['task'],'plans':o['plans'],'commandRows':o['commandRows'],'actualUnexpectedExecute':c.get('actualProhibitedExecute',c.get('unexpectedExecute',c.get('unexpectedBaselineTailExecute'))),'modelCalls':c.get('modelCalls',[]),'prefixBeforeReplan':c.get('completedPrefix')})
put('DEF-S3-116-final-counterexamples',{'tag':'V1.177','productSha':SHA,'issue':'DEF-S3-116 remains F; original exact prohibited case now P, no duplicate issue assigned','cases':failureRows,'controls':{'originalAllowed':1007,'originalProhibitedRejected':1008,'allowedZone':1009,'otherZoneRejected':1010,'baselineAllowedCompleted':1020,'replanAutonomousProhibitedRejected':1015,'replanBaselineAllowedCompleted':1023},'sameVersionExecutionCounts':'UI/SQL/protocol corroboration of same task does not add business executions','cleanup':'All27 tasks terminal, failures/plans/events retained'})
notes={
'R01':'三预置删除400/身份变更拒绝、参数约束编辑恢复；首轮缺test_passed前置后，航班族通过真实自有适配器测试补齐，三族业务字段/原JSON最终恢复。',
'R02':'同定义998两步/999五步自主生成并完成，定义只有场景/能力/约束/完成条件，无预写步骤。',
'R03':'创建/编辑约束省略/null/空白/501拒绝，1/500合法持久；名1/64、目标1/500、重复409、必填等；四类型API/真实UI，1016浏览器值原样持久。028/029/030保持当前关闭。',
'R04':'扩展沿已有定义/提交/监控页面、统一合成设备HTTP协议和既有CAP_NAVIGATION运行，无新增产品页面/协议/能力类型。',
'R05':'999实际五步、1006条件+五动作完成；1000六步拒绝；1013前缀1+替换4合并五步（风险门转人工），1014超剩余额度拒绝；所有当前计划/执行路径受上限。',
'R06':'不存在/无启用且测试通过实例能力POST/PUT均4004604、定义无变；合法导航实例创建对照；状态夹具恢复。',
'R07':'原116反例1008及允许/区域对照P；1011白名单前缀旁路、1012能力句误作地点、1021首次基线漏检、1024重规划基线尾部漏检，四处F。完成条件/能力范围及1015自主重规划拦截子项P，不抵销完整R07 F。',
'R08':'定义创建/编辑/启用/停用SQL审计完整，1004停用后原计划继续完成；1016真实提交后停用不可新选、已有任务仍可读。'}
stepNotes={'TC-068.S1':'创建/编辑边界、三预置、参数表格与真实UI保存回显通过。','TC-068.S2':'动态参数/五步预算/停用/历史/审计P；116四反例F，原反例P不等于整步通过。','TC-069.S1':'三预置删除与身份保护、参数约束可编辑并恢复，UI预置标识/禁删通过。','TC-069.S2':'重名409、缺必填、空白/501和未知/未启用有效能力拒绝，非法输入不保存/不可选。'}
ref='acceptance/stage3/SRS_F022-V1.177-整轮独立复测与统一交修.md;acceptance/stage3/evidence/'+PRE+'complete-verification-20261107.json'
snapshot={}
for name in ['steps.csv','rules.csv','issues.csv']:
 p=D/name
 with p.open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);heads=reader.fieldnames;rows=list(reader)
 snapshot[name]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'rows':[x.copy() for x in rows if (name=='steps.csv' and x['caseId'] in ['TC-068','TC-069']) or (name=='rules.csv' and x['requirement']=='SRS_F022') or (name=='issues.csv' and x['编号'] in ['DEF-S3-028','DEF-S3-029','DEF-S3-030','DEF-S3-116','DEF-S3-117'])]}
 if name=='steps.csv':
  for x in rows:
   if x['stepId'] in stepNotes:x.update(status='F' if x['stepId']=='TC-068.S2' else 'P',observedAt='2026-11-07',actual='V1.177当前实测：'+stepNotes[x['stepId']]+'；历史原文保存在ledger-before，不冒用旧P。',evidence=x['evidence']+';'+ref,issue='DEF-S3-116' if x['stepId']=='TC-068.S2' else '')
 elif name=='rules.csv':
  for x in rows:
   if x['requirement']=='SRS_F022':x.update(status='F' if x['ruleId']=='SRS_F022.R07' else 'P',verifiedBy='V1.177当前全部适用项实测；TC-068/069四步骤，详细观察与层级见报告',evidence=x['evidence']+';'+ref,issue='DEF-S3-116' if x['ruleId']=='SRS_F022.R07' else '')
 else:
  for x in rows:
   if x['编号'] in ['DEF-S3-028','DEF-S3-029','DEF-S3-030']:
    x['状态']='关闭（V1.177 F022当前独立实测，旧失败保留）';x['事实']+='；V1.177动态四类型/API/真实UI提交及创建编辑约束边界当前通过，历史来源保留。';x['证据']+=';'+ref
   elif x['编号']=='DEF-S3-117':
    x['状态']='关闭（V1.177实际JAR/容器与Mapper注入当前通过）';x['事实']+='；V1.177两次相同JAR启动健康UP、真实认证/业务接口及任务执行通过，独立Spring构造器选择/mapperInjected=true，七参数服务4P；原启动失败保留。';x['证据']+=';'+ref
   elif x['编号']=='DEF-S3-116':
    x['状态']='待修复（V1.177原反例P但四处残留/回归F，R07未通过）';x['事实']+='；V1.177原禁区1008硬拒绝/无冻结指令，首次请求已含描述；1011仅允许GATE却放行F2_TEST并下发、1012仅允许使用NAV被误当地点拒绝，1021基线及1024重规划基线尾部禁区仍PASS冻结/下发。';x['关联需求规则']='SRS_F022.R07;SRS_F013.R03（直接依赖）';x['证据']+=';acceptance/stage3/evidence/'+PRE+'DEF-S3-116-final-counterexamples-20261107.json;'+ref;x['阶段4动作']='修正地点标识匹配和约束语义分类；基线/重规划基线须解析参数映射后对实际目标做同等硬校验。保留原反例与合法、区域、非地点描述及四计划路径对照；新唯一标签后F022整轮。'
 with p.open('w',encoding='utf8',newline='') as f:w=csv.DictWriter(f,fieldnames=heads,lineterminator='\n');w.writeheader();w.writerows(rows)
put('ledger-before',snapshot)
index={'verdict':'READY_FOR_CLAUDE','tag':'V1.177','productSha':SHA,'claudeHandoffSha':HANDOFF,'executionBaseline':'V2.4','timezone':'Asia/Shanghai','rules':{'P':7,'F':1,'NT':0},'steps':{'P':3,'F':1,'NT':0},'notes':notes,'stepNotes':stepNotes,'closed':['028','029','030','117'],'open':['116'],'historicalBusinessPReused':0,'businessObservationGroups':{'total':28,'P':24,'F':4,'note':'24 primary groups including three presets combined from current partial+flight supplement, two initial baseline groups and two replan-baseline groups. Three successful trial prerequisites and same-task UI/SQL corroboration not extra business groups.'},'tasks':{'total':27,'ids':state['taskIds'],'formalBusiness':23,'successfulTrialPrerequisites':[1017,1019,1022],'incompleteFixtureAttempt':[1018],'note':'All created through actual HTTP, no SQL task/plan lifecycle synthesis. Extra failed setup attempts created definitions but no business tasks.'},'ui':{'groups':18,'P':18,'F':0,'screenshots':18,'consoleErrors':0,'note':'Includes viewing two product F traces; UI observation confirms display, does not turn product F into business P.'},'component':{'springContainerAndMapperInjection':'P','serviceControls':4},'backendTests':tests['totals'],'coreLayers':['production JAR','authenticated real HTTP','SQL persistence/events/audit','controlled model','synthetic device callbacks','real IAB UI'],'directAffectedAdjacency':'SRS_F013.R03 family-constraint subrange F from same four counterexamples; historical acceptance row kept at its original tested version. Replanning/baseline paths actually exercised, not historical P reuse.','main':MAIN,'noMergeNoPR':True,'environment':{'retainedDefinitions':len(state['definitionIds']),'templates':len(state['templateIds']),'ownedDevices':4,'terminalTasks':27,'activeAssignments':0,'occupiedAgents':0,'portsReleased':7,'presetRawConfigRestored':True,'mainUserFilesHashUnchanged':40},'next':'Claude receive complete evidence and repair116 four scopes; keep117 and028/029/030 closed paths; new tag then F022 full round, no F023/95-case/core-scenario acceptance claim'}
put('complete-verification',index)
text=f'''# SRS_F022 V1.177 整轮独立复测与统一交修

**READY_FOR_CLAUDE：八规则7P/1F/0NT，四正式步骤3P/1F/0NT。** 全部适用项、独立分支和必要直接依赖均已当前实测，历史业务P复用0。028/029/030当前保持关闭，117当前关闭；116原反例已通过，但四处残留/修复回归仍F，整项不通过，不合main、不推进F023。

固定产品 **`{SHA}` / V1.177**，Claude交接 **`{HANDOFF}`**，远端标签与分支/用户声明核对一致，固定不移动。GPT独立 `C:/Users/savy/Desktop/TIP-main/tip-gpt-f013` / ai/gpt-test，快进接收，开工无活动测试/七端口空闲；日期2026-11-07 Asia/Shanghai，V2.4及既有业务澄清不变。main保持 `{MAIN}`，产品源码对标签diff为空。

| 规则 | 当前 | 当前证据与裁决 |
|---|---|---|
'''
for k,v in notes.items():text+=f'| SRS_F022.{k} | {"F" if k=="R07" else "P"} | {v} |\n'
text+='\n| 正式步骤 | 当前 | 范围 |\n|---|---|---|\n'
for k,v in stepNotes.items():text+=f'| {k} | {"F" if k=="TC-068.S2" else "P"} | {v} |\n'
text+='''
116四处反例（同一任务的HTTP、SQL、协议与UI共证不增加实测次数）：

1. **1011，白名单前缀旁路**：定义94/EXT_633EC296仅允许前往F2_TEST_GATE，候选inputParams.targetLocation却为F2_TEST（与允许目标不同的配置区域）。仍constraint PASS、冻结并下发EXECUTE_CAPABILITY至F2_TEST。定义与首次请求原文均正确，不能把字符串包含/反向包含当作目标相等或自动扩大授权区域。1007允许GATE、1010其他区域拒绝为当前合法/非法对照。
2. **1012，合法能力描述误作地点**：“仅允许使用CAP_NAVIGATION能力。”，可用能力也仅CAP_NAVIGATION，合法一导航候选结构/能力通过，却constraint FAIL，错误把“使用CAP_NAVIGATION能力”列为允许地点，任务转人工。应区分能力限制与地点限制，不能发明无关地点约束。这是116修复引入的合法路径回归，不是新需求。
3. **1021，首次降级基线漏检**：定义EXT_FDB3FE41禁止GATE/只允许ZONE_A；模型受控503触发已真实试运行成功并启用的模板。BASELINE_TEMPLATE计划991仍PASS/冻结，下发CMD-20261107162719-EABF0045，实际targetLocation=F2_TEST_GATE。1020合法基线已完成，排除模板或设备不能执行的前置问题。
4. **1024，重规划基线尾部漏检**：第一步ZONE_A真实完成，第二步真实失败重试/候选切换后自动局部重规划；新自主候选通过校验并被高风险判定转基线。定义禁止GATE/只允许ZONE_A，基线尾部从fallbackLocation解析出GATE，仍PASS/冻结并下发该禁区指令。1023同路合法ZONE_A尾部完成，已完成前缀保留，未用SQL伪造业务状态。

完整反例索引`evidence/SRS_F022-V1.177-DEF-S3-116-final-counterexamples-20261107.json`包含定义、请求、计划、实际指令和来源；原始HTTP/SQL/事件/协议在http各文件，首次与重规划模型请求在model-requests JSONL。1011/1012真实UI截图/DOM展示PASS冻结和错误地点解释。原1008禁区反例现在正确FAIL/不冻结/不下发，1009允许区域通过，自主重规划1015禁区拒绝也P；这些子项不能抵销完整R07 F。

定位审查发现地点匹配采用子串比较，且“仅允许使用…”被当作地点；模板候选以paramMapping表达目标，不能只检查inputParams而忽略实际解析目标。修复应覆盖首次自主、首次基线、局部自主重规划和局部重规划基线四条路径，对实际输入执行同等硬门，保留完成条件与合法对照。SRS_F013.R03任务族约束子范围以同证当前受影响F登记，不额外增加执行次数、不改写其原历史验收版本。

117已独立闭环：本轮两次启动相同生产JAR健康UP，真实认证/业务接口和任务生命周期运行；从该JAR类/依赖构造独立Spring容器，构造器选择成功且mapperInjected=true，七参数读取定义的四服务对照P。不是选中旧单参构造器留下null后冒称成功。后端只执行了一轮mvn -o test：456报告454执行通过、2原有跳过、0失败/错误；生产打包与前端构建成功，复制报告不重复计算测试次数。商业模型质量、物理设备/急停、后续需求、三核心或95项整体验收不在本轮通过声明范围。

28去重业务观察组24P/4F；18真实IAB组/18截图/0console error。27个持久任务998～1024均HTTP创建：23正式业务任务、3次成功试运行前置（1017/1019/1022）、1个因探针错误中断的基线尝试1018。试运行前置与相同任务的UI/SQL/协议不另增业务组。创建/编辑约束各类无效/1/500中文边界、名1/64和目标1/500、重复409、能力缺口、权限/审计、四类型动态表单与真实提交、五步/六步/条件动作、跨版本额度、停用与既有任务均当前实测。失败后持续完成其余分支，无剩余NT。

夹具/探针错误原记录保留并独立更正：初始能力状态SQL没有保证test_passed=true，实际适配器能力测试后补齐航班预置编辑；四必填模板输入只映射一个被正确拒绝；正常DOWNGRADING被错误排除而超时；清理停用后直接重启用/重试运行被状态机正确拒绝。最终新草稿真实试运行、首次基线正反例及追加重规划基线正反例均完成。初始表述“设备未启用”为解释不准确，真实前置为有效测试通过实例，见probe-corrections JSON。没有把产品四F归为探针错误，没有为了通过放宽标准。

全部配置和资源已恢复/清理：GPT schema tip_gpt_f006_v118_20261030、Redis10；9保留定义DISABLED、3模板DISABLED、4自有设备INACTIVE，27任务终态、当前活跃分配/设备占用0、触发器0，预置业务字段和原JSON精确恢复，无风险规则修改。能力临时启用状态恢复；真实能力测试新增结果作为本轮记录保留，不伪造test_passed。先停止3自有进程树/七端口释放；收口调用点审查发现独立重规划基线分支，固定同SHA补测，仅重启后端/模型并用自有适配器，结束再停止2树，七端口最终无监听。两阶段清理证据各自保留，未移动标签或混测新代码。

主工作区无写入或同步，NUL/UTF8正确保存的40用户文件开工/结束哈希完全一致。无强推/reset、共享PG/Redis或Claude资源未动；原Office、凭据/令牌、DPAPI、JAR、本地私有配置和无关用户文件不提交，公开测试日志中的临时测试口令脱敏，原日志留本机。证据先推送检查点755f11e，最终完整证据再先提交推送，随后单写入者更新HANDOFF/ROADMAP/EXECUTION_BASELINE并填实际证据SHA。main保持413e1b3，未合本轮、无PR；下一仅Claude接证据修116四范围并保持117及028/029/030，发新唯一标签后F022整轮。
'''
(D/'SRS_F022-V1.177-整轮独立复测与统一交修.md').write_bytes(text.encode('utf8'))
p=D/'阶段3-复测进度.md';t=p.read_text(encoding='utf8');entry='\n- **2026-11-07 / F022 V1.177 / V2.4：READY_FOR_CLAUDE，7P/1F/0NT、四步骤3P/1F/0NT**。117实际JAR/注入关闭、028/029/030当前通过；116原反例P但1011前缀放行、1012能力句误作地点、1021首次基线和1024重规划基线漏检四F。28业务组24P/4F、18 IAB组/18截图/0JS error，27 HTTP任务（23正式/3成功试运行/1探针中断），456报告454通过2跳过、生产构建P。原诊断/失败与更正保留，全部适用项当前实测、历史P复用0，无剩余NT。配置恢复、分配占用0、七端口最终释放、40用户文件哈希不变；main仍413e1b3无本轮合并/PR，不推进F023。报告`SRS_F022-V1.177-整轮独立复测与统一交修.md`。\n';p.write_bytes(t.replace('\n','\n'+entry,1).encode('utf8'))
files=sorted(set(E.glob(PRE+'*'))|set(D.glob('*f022-v177*.py'))|set((D/'fixtures').glob('*f022-v177*'))|{D/'fixtures/F022V177ContainerProbe.java',D/'SRS_F022-V1.177-整轮独立复测与统一交修.md'})
put('evidence-manifest',[{'path':str(p.relative_to(R)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files if 'evidence-manifest' not in p.name])
print(json.dumps({'verdict':index['verdict'],'rules':index['rules'],'steps':index['steps'],'businessGroups':index['businessObservationGroups'],'tasks':len(state['taskIds'])},ensure_ascii=False))
