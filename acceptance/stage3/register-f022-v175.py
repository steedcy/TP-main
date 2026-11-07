"""Append independent F022 V175 verdict, keeping raw failures/diagnostics unchanged."""
import csv,json,hashlib,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'acceptance/stage3';E=D/'evidence';PRE='SRS_F022-V1.175-'
SHA='02a38cb08e14ece1968a800a18423219fdf76c8b';HANDOFF='a74b295060c904c08e69459af52f2b85ab5df8dd'
def get(suffix):return json.loads((E/(PRE+suffix)).read_text(encoding='utf8'))
def put(name,obj):
 p=E/(PRE+name+'-20261107.json');assert not p.exists(),p;p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8')
def readcsv(p):
 with p.open(encoding='utf-8-sig',newline='') as f:
  reader=csv.DictReader(f);return reader.fieldnames,list(reader)
def writecsv(p,heads,rows):
 with p.open('w',encoding='utf8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=heads,lineterminator='\n');w.writeheader();w.writerows(rows)
raw=get('http-20261107-description-participation.json');negative=raw['cases'][1];positive=raw['cases'][0]
assert negative['result']=='F' and positive['result']=='P'
minimal={'tag':'V1.175','productSha':SHA,'requirement':'SRS_F022.R07','step':'TC-068.S2','issue':'DEF-S3-116','classification':'Previously uncovered existing implementation gap; relevant planner/validator sources unchanged V1.174→V1.175. Not a regression attributed to DTO changes.','baseline':'SRS V1.0 5.6.1 R07 + 5.4.4 R03, stage0 R07/TC068S2; no standards changed','definition':negative['definition'],'taskId':997,'taskCode':negative['after']['task']['taskCode'],'positiveControl':{'taskId':996,'constraintDescription':positive['definition']['constraintDescription'],'status':positive['after']['task']['status']},'request':negative['request'],'initialPlanningCalls':negative['modelCalls'],'plan':negative['after']['plans'],'actualExecuteMessage':negative['actualExecuteMessage'],'checks':negative['checks'],'expected':negative['expected'],'source':'SRS_F022-V1.175-http-20261107-description-participation.json','cleanup':'Task997 terminated and retained; plan966 retained; see fixture-cleanup and process-cleanup JSON','reproduce':['Start isolated V1.175 JAR and f022-v175-controlled-model.py; reserve GPT ports/schema only.','Run probe-f022-v175-description-participation.py with a fresh evidence suffix. It creates an own navigation definition and synthetic adapter.','Allowed description targets F2_TEST_GATE: task996 normal control completed.','Change only description to prohibit F2_TEST_GATE and permit F2_ZONE_A; submit same target/one-step plan.','Observe task997 plan966 constraint PASS/frozen, accept synthetic agent, EXECUTE_CAPABILITY targetLocation=F2_TEST_GATE. No physical hardware was used.']}
put('DEF-S3-116-minimal',minimal)
ruleNotes={
'R01':'三预置族删除400；名称/code变更400；三族参数/约束编辑成功并逐字段/原JSON恢复；真实列表预置标识/禁删。',
'R02':'定义仅场景/能力/约束/完成条件；同一定义984两步和985五步自主生成并完成，无预写步骤。',
'R03':'POST/PUT约束省略/null/空白/501均4003001；1/500合法持久；名1/64、目标1/500、重复409等；四支持类型动态/API门禁与真实提交993。028/029/030关闭。',
'R04':'扩展定义沿既有任务定义/提交/监控页、CAP_NAVIGATION与统一仿真协议运行，无新增产品页面/设备协议/能力类型。',
'R05':'985五步、992条件+五动作完成；986六步先行拒绝；994完成前缀1+替换4合并V2五步且资源高风险门生效；995前缀1+替换5超过剩余额度拒绝。',
'R06':'未知/无启用实例能力POST/PUT均4004604并给能力缺口，无定义变更；合法启用导航对照；能力状态夹具恢复。',
'R07':'能力范围/完成条件冲突及SUCCESS但完成条件不满足子项P；定义93禁止F2_TEST_GATE后，997计划966仍constraint PASS/冻结/下发禁区EXECUTE_CAPABILITY。DEF-S3-116 F。996允许对照完成。',
'R08':'本轮定义创建、编辑、启用、停用四类SQL操作记录，操作者/角色/时间/结果齐全；任务990定义停用后原计划继续完成。'}
stepNotes={'TC-068.S1':'创建/编辑、预置列表、全部必填与边界、参数表格及真实UI合法保存通过；030关闭。','TC-068.S2':'动态四类型/UI/API、五步预算、停用后不可新选/已有任务完成和审计P；任务997定义禁区约束未拦截，DEF-S3-116 F。','TC-069.S1':'三预置族删除拒绝、身份字段拒绝、参数约束可维护且配置恢复，真实UI预置/禁删通过。','TC-069.S2':'重复名称409；缺必填/空白/501拒绝；不存在及未启用能力创建/编辑缺口4004604，非法请求不改定义/不进入可选集合。'}
evidence='acceptance/stage3/SRS_F022-V1.175-整轮独立复测与统一交修.md;acceptance/stage3/evidence/'+PRE+'complete-verification-20261107.json'
snapshot={}
for name in ['steps.csv','rules.csv','issues.csv']:
 p=D/name;heads,rows=readcsv(p)
 if name=='steps.csv':selected=[x.copy() for x in rows if x['caseId'] in ['TC-068','TC-069']]
 elif name=='rules.csv':selected=[x.copy() for x in rows if x['requirement']=='SRS_F022']
 else:selected=[x.copy() for x in rows if x['编号'] in ['DEF-S3-028','DEF-S3-029','DEF-S3-030']]
 snapshot[name]={'originalSha256':hashlib.sha256(p.read_bytes()).hexdigest(),'rows':selected}
 if name=='steps.csv':
  for x in rows:
   if x['stepId'] in stepNotes:x.update(status='F' if x['stepId']=='TC-068.S2' else 'P',observedAt='2026-11-07',actual='V1.175当前实测：'+stepNotes[x['stepId']]+'；原文/历史F/P保存在本轮ledger-before与原始证据。',evidence=x['evidence']+';'+evidence,issue='DEF-S3-116' if x['stepId']=='TC-068.S2' else '')
 elif name=='rules.csv':
  for x in rows:
   if x['requirement']=='SRS_F022':
    k=x['ruleId'].split('.')[-1];x.update(status='F' if k=='R07' else 'P',verifiedBy='TC-068.S1;TC-068.S2;TC-069.S1;TC-069.S2（V1.175当前实测，具体映射见报告）',evidence=(x['evidence']+';' if x['evidence'] else '')+evidence,issue='DEF-S3-116' if k=='R07' else '')
 else:
  for x in rows:
   if x['编号'] in ['DEF-S3-028','DEF-S3-029','DEF-S3-030']:
    x['状态']='关闭（V1.175 F022当前独立复测；历史失败保留）';x['事实']+='；2026-11-07 V1.175：'+('四支持类型动态渲染与必填/类型非法输入在建任务/调模型前拒绝，993真实UI值完整持久。' if x['编号']!='DEF-S3-030' else '新增/编辑约束省略、null、空串、空白、501均4003001；1/500及真实UI新增/编辑合法对照通过。');x['证据']+=';'+evidence
  assert not any(x['编号']=='DEF-S3-116' for x in rows)
  rows.append(dict(zip(heads,['DEF-S3-116','缺陷','高','TC-068.S2','SRS_F022.R07;SRS_F013.R03（直接依赖）','待修复（V1.175当前F）','定义93/EXT_0408BD76约束为禁止前往F2_TEST_GATE、仅允许F2_ZONE_A；997/计划966仍constraint PASS、冻结且下发CMD-20261107143540-A68C003C导航到F2_TEST_GATE。初始规划请求仅通用两约束未含定义描述；996允许同地点合法对照完成。旧代码未覆盖缺口，非DTO新改引入。','acceptance/stage3/evidence/'+PRE+'DEF-S3-116-minimal-20261107.json;'+evidence,'让任务定义约束进入首次规划/三类硬校验，并对明确禁止目标反例拦截；不能只传提示词或仅校验能力清单。覆盖合法对照、基线/重规划直接影响，下一唯一标签后F022整轮复测。'])))
 writecsv(p,heads,rows)
put('ledger-before',snapshot)
cor=get('probe-corrections-20261107.json');cleanup=get('fixture-cleanup-20261107.json');tests=get('backend-tests-20261107.json')
assert cleanup['exactBusinessConfigRestored'] and cleanup['currentActiveAssignments']=='0'
assert all(x['current_task_id'] is None and x['device_status']=='INACTIVE' for x in cleanup['ownedAgents'])
assert all(all(x['checks'].values()) for x in cor['ui'].values()) and all(cor['preset']['checks'].values()) and all(cor['budget']['checks'].values())
assert get('process-cleanup-20261107.json')['allReleased']
index={'verdict':'READY_FOR_CLAUDE','tag':'V1.175','productSha':SHA,'claudeHandoffSha':HANDOFF,'executionBaseline':'V2.4 + existing business clarifications','timezone':'Asia/Shanghai','currentRequirement':'SRS_F022','rules':{'P':7,'F':1,'NT':0},'steps':{'P':3,'F':1,'NT':0},'ruleNotes':ruleNotes,'stepNotes':stepNotes,'historicalBusinessPReused':0,'closed':['DEF-S3-028','DEF-S3-029','DEF-S3-030'],'open':['DEF-S3-116'],'observations':{'independentBusinessGroups':19,'P':18,'F':1,'note':'Aggregated across original + supplements, same observations corrected from retained evidence do not add execution counts. Browser993 persistence is shared UI/HTTP evidence, not two business executions.','persistedTasks':16,'actualScopeTasks':14,'exploratoryUnsupportedSchemaTasks':2,'taskIds':list(range(982,998))},'ui':{'groups':15,'P':15,'F':0,'correctionsFromSavedDOM':3,'consoleErrors':0,'screenshots':15},'backendTests':tests['totals'],'builds':['mvn -o package -DskipTests','npm run build'],'layers':['production JAR','real HTTP','SQL persistence/events/audit','controlled planning model','synthetic device HTTP adapters','real IAB browser'],'notClaimed':['commercial model quality','physical devices','later requirements','three core scenario end-to-end acceptance','95-case overall acceptance'],'mainUnchanged':'413e1b3aee20116bb612ed1d4dac96e9937cde0e','productCodeUntouched':True,'scopeHistory':'Historical P kept as comparison, not imported as current P. No controlled business standard changed.','evidenceSubmittedBeforeHandoff':'Evidence commit is recorded in subsequent HANDOFF commit; no circular self-hash.'}
put('complete-verification',index)
report=f'''# SRS_F022 V1.175 整轮独立复测与统一交修

结论：**READY_FOR_CLAUDE，规则7P/1F/0NT，正式四步骤3P/1F/0NT**。全部适用项完成本轮实测，历史业务P验收复用0。DEF-S3-028/029/030关闭；新发现DEF-S3-116保留待修，整项未通过，不合main、不推进F023。

固定产品 `{SHA}` / **V1.175**，Claude交接 `{HANDOFF}`；远端分支、标签、产品提交与用户消息一致。上一F021已验收，开工main及本轮结束远端main均为 `413e1b3aee20116bb612ed1d4dac96e9937cde0e`。独立worktree `C:/Users/savy/Desktop/TIP-main/tip-gpt-f013` / `ai/gpt-test` 快进接收a74b295，源目录与标签比较无差异。时间2026-11-07 Asia/Shanghai，执行基线V2.4；没有产品修改、需求放宽或失败记录删除。

| 当前规则 | 结果 | 本轮证据与裁决 |
|---|---|---|
'''
for k,v in ruleNotes.items():report+=f'| SRS_F022.{k} | {"F" if k=="R07" else "P"} | {v} |\n'
report+='\n| 正式步骤 | 结果 | 本轮证据与裁决 |\n|---|---|---|\n'
for k,v in stepNotes.items():report+=f'| {k} | {"F" if k=="TC-068.S2" else "P"} | {v} |\n'
report+='''
## DEF-S3-116：任务族文字约束没有成为硬闸门

受控依据为stage0 SRS_F022.R07/TC-068.S2，以及原SRS V1.0 §5.6.1规则7和§5.4.4规则3（满足任务族约束与完成条件）。原Office只在本地只读核对，未上传。不是根据源码反向生成预期，也没有把“约束必填”替代“约束参与校验”。

定义93 `EXT_0408BD76`，可用能力CAP_NAVIGATION。允许“仅允许前往F2_TEST_GATE。”时，996正常完成。随后只修改该定义的constraintDescription为“禁止前往F2_TEST_GATE；仅允许前往F2_ZONE_A。”，997仍生成目标F2_TEST_GATE的一步导航计划。计划966 structure/capability/constraint均PASS且冻结；合成设备接受后，下发 `CMD-20261107143540-A68C003C` / EXECUTE_CAPABILITY，inputParams.targetLocation=F2_TEST_GATE，任务EXECUTING。定义API/SQL保留了禁止原文，模型首次规划请求却只有通用安全/五步约束。保存必填、能力范围与完成条件子项通过不能抵销本反例。

最小复现`evidence/SRS_F022-V1.175-DEF-S3-116-minimal-20261107.json`；完整HTTP/SQL/事件/协议/模型请求在`...http-20261107-description-participation.json`。独立脚本`probe-f022-v175-description-participation.py`依次构造合法对照与禁止反例，不依赖手工数据库业务状态。仅合成设备/符号业务地点，无物理运动覆盖。997随后终止，失败计划和事件保留。planner/validator相关源文件V1.174→V1.175无变化，归类为既有未覆盖缺口，不将其误报为本轮DTO新增回归。

Claude需让定义约束进入首次规划及三类硬校验；明确禁止目标的候选不得冻结/下发，合法对照可执行。单独把文本加进提示词不足以证明硬闸门成立。回归相关基线与重规划路径，发布新唯一标签后按V2.4再次F022整轮。

## 当前覆盖、原缺陷与邻接

030：创建/编辑各6个约束非法等价类（省略/null/空串/空白/控制空白/501）全4003001，定义全集快照不变；1/500中文边界原样HTTP/SQL持久，目标1/500、名称1/64、重复409、空场景/能力/完成条件及参数名/类型缺失拒绝。真实浏览器新增/编辑空约束、501长度提示、合法保存/回显通过。三预置族删除拒绝、身份变更字段拒绝、参数/约束编辑成功；前置能力SQL状态夹具只在GPT私有schema配置，航班类型缺实例时另建G175_F022_FLIGHT实际连接/测试/启用后完成，所有原配置恢复。

028/029：支持的String/Integer/Boolean/Double动态显示，非法输入前端禁用提交及后端400，建任务计数/模型调用计数不变；991合法四类型完成；993真实浏览器提交四值经HTTP/SQL核对原样持久。停用后真实下拉不出现定义、API新提交400；990停用后沿原计划完成，993已有任务仍可读。当前UI真实15观察组、15截图、0console error；原3条错误断言按原始已保存DOM/截图更正，不再制造同版执行。

R05：984/985同一定义自主两步/五步均完成，992一个条件节点+五个动作折叠后五动作实际完成；986六步在计划持久前ERR_STEP_LIMIT_EXCEEDED拒绝，事件和模型原响应保留。994真实完成首步、失败重试/换候选后局部重规划，V1三步/V2合并五步，随后现有RULE_RESOURCE_CRITICAL高风险且无基线转人工；这符合风险门，未声称实际五步完成。995完成前缀1+替换5超剩余额度4拒绝。当前原始F中的“必须完成”是探针错误预期，单独更正保留，未变更需求上限。能力范围越界、定义完成条件与模型冲突、SUCCESS输出routeGenerated=false不能完成步骤的反例均实测，正常执行及创建/启停/删除/权限/审计为直接依赖与核心冒烟，不扩展为无关需求全量验收。

19去重业务观察组18P/1F，16持久任务982～997，其中14正式业务任务、2个原探针使用UI不支持Number/Object定义的探索任务。原SRS §5.6.1未列出场景schema类型枚举，不能仅据实现四选项把探索结果直接判成受控业务F或P；保留原接受记录，不用它替代支持类型覆盖。997界面/SQL/协议同源共证不额外计次数；更正与单测不是新增业务执行。

## 构建、诊断与恢复

独立执行mvn -o test：451报告、449执行通过、2原有跳过、0失败/错误；mvn -o package -DskipTests及npm run build均成功。实际打包JAR在18129健康UP，认证任务/设备代理/dashboard overview HTTP通过。最初错写/dashboard/summary的404留原记录，正确入口另证。商业模型与真实设备不在本层证明范围。

原始首批诊断及错误断言全保留：重复名应409；字典引用在创建后被修改；恢复比较缺排序；PUT多传taskName触发未知字段而未到能力缺口；缺前置能力；journal默认GBK读取；审核列为operation_result；可选defaultValue:null规范化；测试回包字段为capabilityStatus；textarea.textContent不等于value。修正后仅补缺失路径，已充分的同版观察不重跑。首次规划文字约束反例是独立新增产品F，不归入这些探针错误。

GPT资源schema tip_gpt_f006_v118_20261030 / Redis10；后端18129、模型18117、适配器18132～18135、前端15179。7个保留定义DISABLED（一次性删除定义89已完成删路径并留审计）、4设备INACTIVE，所有16任务终态、当前活跃分配0、设备占用0、注入触发器0。三预置业务字段及原JSON精确恢复，所有临时能力状态恢复，新航显能力停用；无规则/模板业务配置变更。3自有进程树归属校验后停止、七端口无监听，Claude和共享PG/Redis未动。

台账更新前原文在ledger-before JSON，原F/NT/P及全部旧证据不删除。ROADMAP“4ec6695约束DTO待移植”与标签实际源码不符，应在正式交接修正为已纳入V1.175并已实测；不能据暂存表认定未实现或宣称整项通过。完整证据先提交/推送，随后单写入者更新HANDOFF/ROADMAP/EXECUTION_BASELINE，填实际证据SHA；main保持413e1b3，无合并/PR，下一仅Claude修116及直接影响后交新标签再复测F022。
'''
(D/'SRS_F022-V1.175-整轮独立复测与统一交修.md').write_text(report,encoding='utf8')
p=D/'阶段3-复测进度.md';t=p.read_text(encoding='utf8');line='\n- **2026-11-07 / F022 V1.175 / V2.4：READY_FOR_CLAUDE**。八规则7P/1F/0NT、正式四步骤3P/1F/0NT，全部适用项当前实测/历史P复用0；028/029/030关闭，新116定义禁区文字约束未拦截计划966/任务997统一交修。19业务组18P/1F、16持久任务（14正式/2探索夹具）、真实IAB15组/15截图，451报告449通过2跳过，生产构建/实际JAR。原诊断及错误断言另行更正保留；配置恢复、分配/占用0、3树/7端口清理。main保持413e1b3，无本轮合并/PR，不推进F023。报告`SRS_F022-V1.175-整轮独立复测与统一交修.md`。\n';p.write_text(t.replace('\n','\n'+line,1),encoding='utf8')
files=sorted(E.glob(PRE+'*'))+list(D.glob('*f022-v175*.py'))+list((D/'fixtures').glob('*f022-v175*'))+[D/'SRS_F022-V1.175-整轮独立复测与统一交修.md']
put('evidence-manifest',[{'path':str(p.relative_to(R)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files if 'evidence-manifest' not in p.name])
print(json.dumps({'verdict':index['verdict'],'rules':index['rules'],'steps':index['steps'],'tests':tests['totals'],'manifest':len(files)},ensure_ascii=False))
