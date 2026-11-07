"""Register V176 full-round disposition after genuine production startup blocker.
Preserve all V175 P/F/NT evidence and all new startup/component observations.
"""
from pathlib import Path
import csv,json,hashlib
R=Path(__file__).resolve().parents[2];D=R/'acceptance/stage3';E=D/'evidence';PRE='SRS_F022-V1.176-'
SHA='5bf8ad62f2a8269430d19f6db4d7d0ef45aedf32';HANDOFF='0ada3a8ef4d2692f61af53868e0a6639cd2806c2';MAIN='413e1b3aee20116bb612ed1d4dac96e9937cde0e'
def get(name):return json.loads((E/(PRE+name+'-20261107.json')).read_text(encoding='utf8'))
def put(name,value):
 p=E/(PRE+name+'-20261107.json');assert not p.exists();p.write_bytes(json.dumps(value,ensure_ascii=False,indent=2).encode('utf8'))
block=get('per-item-blockers');component=get('container-component');tests=get('backend-tests');env=get('environment-cleanup');alignment=get('version-final-check')
assert block['runtimeGate']=='F' and len(block['items'])==12 and not component['container']['started']
assert all(c['result']=='P' for c in component['componentObservations'])
assert tests['totals']=={'tests':454,'failures':0,'errors':0,'skipped':2}
assert alignment['productSourceDiff']=='' and not any(env['portsListening'].values())
report='acceptance/stage3/SRS_F022-V1.176-整轮独立复测与启动阻断交修.md'
evidence=report+';acceptance/stage3/evidence/'+PRE+'per-item-blockers-20261107.json;acceptance/stage3/evidence/'+PRE+'DEF-S3-117-minimal-20261107.json'
snapshot={}
for filename in ['steps.csv','rules.csv','issues.csv']:
 p=D/filename
 with p.open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);heads=reader.fieldnames;rows=list(reader)
 selected=[x.copy() for x in rows if (filename=='steps.csv' and x['caseId'] in ['TC-068','TC-069']) or (filename=='rules.csv' and x['requirement']=='SRS_F022') or (filename=='issues.csv' and x['编号'] in ['DEF-S3-028','DEF-S3-029','DEF-S3-030','DEF-S3-116'])]
 snapshot[filename]={'sha256Before':hashlib.sha256(p.read_bytes()).hexdigest(),'rows':selected}
 if filename=='steps.csv':
  for x in rows:
   if x['caseId'] in ['TC-068','TC-069']:x.update(status='NT',observedAt='2026-11-07',actual='V1.176本轮NT：实际生产JAR因DEF-S3-117无法装配PlanValidationService，No default constructor found并退出；登录/HTTP/浏览器/设备前置均不足。隔离无数据库Spring同根复现；单测454报告/构建及4服务对照不替代完整步骤。解除需下一版本真实JAR健康后整轮重测；原V1.175结果在ledger-before保留。',evidence=x['evidence']+';'+evidence,issue='DEF-S3-117'+(';DEF-S3-116（实机复测阻断）' if x['stepId']=='TC-068.S2' else ''))
 elif filename=='rules.csv':
  for x in rows:
   if x['requirement']=='SRS_F022':x.update(status='NT',verifiedBy='V1.176：DEF-S3-117运行前置阻断；逐项范围/尝试/解除条件见per-item-blockers JSON；不冒用单测或V1.175 P',evidence=x['evidence']+';'+evidence,issue='DEF-S3-117'+(';DEF-S3-116' if x['ruleId']=='SRS_F022.R07' else ''))
 else:
  for x in rows:
   if x['编号'] in ['DEF-S3-028','DEF-S3-029','DEF-S3-030']:
    x['事实']+='；V1.176本轮真实业务复测因DEF-S3-117启动阻断记NT，保留V1.175关闭来源，不冒称新版当前通过。';x['证据']+=';'+evidence
   if x['编号']=='DEF-S3-116':
    x['状态']='待实机复测（V1.176组件4P，117阻断HTTP/SQL/设备/界面NT，未关闭）';x['事实']+='；V1.176手动注入两个mapper的七参数服务：原禁止、原允许、允许区域及非白名单区域4组P；真实Spring/JAR无默认构造器无法启动，故原997端到端反例未能重测，未关闭。';x['证据']+=';'+evidence
  assert not any(x['编号']=='DEF-S3-117' for x in rows)
  rows.append(dict(zip(heads,['DEF-S3-117','缺陷','阻断','TC-068.S1;TC-068.S2;TC-069.S1;TC-069.S2（运行前置）','SRS_F022.R01～R08（运行前置）；116复测依赖','待修复（V1.176生产JAR启动F）','V1.176实际打包JAR PID9440启动退出，PlanValidationService两个public构造器均未标构造器注入，参数上的Autowired不选择构造器；Spring No default constructor found / NoSuchMethodException PlanValidationService.<init>()。无DB的真实Spring上下文注册同根失败；手动两个mapper构造+七参数服务4组P仅局部逻辑，不代替运行集成。',evidence,'明确Spring构造器选择并保证TaskDefinitionMapper实际注入；仅启用旧单参数构造器会令mapper=null、约束读取旁路。补真实Spring/JAR健康回归，下一唯一标签再F022整轮；不要让GPT改产品绕过独立测试。'])))
 with p.open('w',encoding='utf8',newline='') as f:w=csv.DictWriter(f,fieldnames=heads,lineterminator='\n');w.writeheader();w.writerows(rows)
put('ledger-before',snapshot)
index={'verdict':'READY_FOR_CLAUDE','runtimeGate':'F','newIssue':'DEF-S3-117','tag':'V1.176','productSha':SHA,'claudeHandoffSha':HANDOFF,'executionBaseline':'V2.4','timezone':'Asia/Shanghai','rules':{'P':0,'F':0,'NT':8},'steps':{'P':0,'F':0,'NT':4},'currentBusinessObservations':0,'historicalBusinessPReused':0,'isolatedSpringConstruction':'F: identical constructor error without DB/Redis/model dependencies','independentServiceObservations':{'P':4,'F':0,'NT':0,'scope':'Manual two-mapper construction; seven-argument production validator with fixture mapper lookup; no HTTP/SQL/frozen plan/device or UI proof'},'backendTests':tests['totals'],'builds':{'backendTest':'P','productionPackage':'P','frontendBuild':'P','actualJarStartup':'F'},'issue116':'Not closed: component subset P, live retest NT blocked by117','closedHistoricalIssues':'028/029/030 retain V1.175 closure only; current V1.176 retest NT','blockerItems':'per-item-blockers-20261107.json has12 explicit entries with dependency, attempts and unblock conditions','environment':{'portsReleased':7,'runtimeProcessExited':True,'newBusinessTasks':0,'newDefinitions':0,'modelAdapterBrowserLaunched':False,'configurationWrites':False,'productSourceModified':False},'mainUnchanged':MAIN,'noMergeNoPR':True,'next':'Claude receive evidence, repair117 and ensure real mapper injection, publish unique next tag, rerun full F022; do not advance F023/three core scenarios/95-case acceptance'}
put('complete-verification',index)
text=f'''# SRS_F022 V1.176 整轮独立复测与启动阻断交修

**结论 READY_FOR_CLAUDE，生产JAR启动门禁F（新DEF-S3-117）。八规则0P/0F/8NT，正式四步骤0P/0F/4NT。** 不是需求通过，也不把启动故障硬写为每条未经执行业务规则F。DEF-S3-116保持未关闭：本轮隔离服务子范围4P，真实HTTP/SQL/冻结/设备/界面复测NT。所有仍能独立完成的检查已执行，剩余12项有逐条真实阻断链，符合V2.4“实际JAR不可启动时逐项NT、其余独立项继续”，没有首F即省略可执行业务分支。

产品 **`{SHA}` / V1.176**，Claude交接 **`{HANDOFF}`**；用户声明、远端标签与提交链全部一致。GPT独立worktree `C:/Users/savy/Desktop/TIP-main/tip-gpt-f013` / `ai/gpt-test`，从56c09d4快进接收0ada3a8；main仍 **`{MAIN}`**。时间2026-11-07 Asia/Shanghai，执行基线V2.4，stage0四步骤/八规则原文、历史F/P/NT全部保留；本轮没有业务基线变更、产品修改或历史P冒充新版实测。

## 新DEF-S3-117：打包产物无法启动

独立命令mvn -o test、mvn -o package -DskipTests及npm run build成功；454项报告452执行通过/2原有跳过、0失败/错误。随后实际启动本轮生产JAR，使用此前健康的GPT私有schema/Redis10/18129隔离配置，PID9440在Spring上下文初始化退出，未达到健康UP。

原始日志依赖链：baselineDryRunService → taskService → taskPlanningOrchestrator → **planValidationService**。根因：**Failed to instantiate PlanValidationService: No default constructor found**，底层 **NoSuchMethodException: PlanValidationService.&lt;init&gt;()**。两public重载构造器没有构造器上的注入标记；@Autowired(required=false)写在TaskDefinitionMapper参数上不选择构造器。源码只是定位，裁决依据是实际JAR失败和独立Spring运行复现。

为排除数据库/Redis/模型/设备前置，另从同一生产JAR提取BOOT-INF/classes与依赖（仅本地.local-test），用AnnotationConfigApplicationContext注册两个合成mapper Bean和真实PlanValidationService：**同根构造器失败**。不是MockMvc返回模拟错误，也没有修改产品源码/Bean配置后冒称原发布物启动成功。最小证据`evidence/SRS_F022-V1.176-DEF-S3-117-minimal-20261107.json`，实际启动日志`...jar-startup-log...txt`，独立容器`...container-component...json`。生产JAR SHA256及PID/端口/数据库SELECT1证据见environment-cleanup JSON。

下一修复要同时保证：1）Spring可以唯一选择构造器；2）TaskDefinitionMapper真正注入。**只让旧单参数构造器可用并留下mapper=null会旁路定义约束查询，不能作为完整修复。** 补真实Spring/JAR启动回归，保留七参数调用原禁止/允许反例；发布新唯一标签后重新F022整轮。

## 可执行独立检查与116局部覆盖

独立Java探针手动注入两个合成mapper，调用生产校验器的**七参数**入口，依靠mapper返回任务定义约束（不同于修复方三项单测显式传八参数constraint）：

| 观察 | 预期/实际 | 层级结果 |
|---|---|---|
| 禁止F2_TEST_GATE、仅允许F2_ZONE_A；目标GATE | constraint FAIL并含任务族原因 | 服务子范围P |
| 仅允许F2_TEST_GATE；目标GATE | PASS、allPassed=true | 服务子范围P |
| 禁止GATE、仅允许ZONE_A；目标ZONE_A | PASS、allPassed=true | 服务子范围P |
| 仅允许ZONE_A；目标ZONE_B | constraint FAIL | 服务子范围P |

4P不能证明真实Spring装配、首次模型请求已含描述、原任务997反例的HTTP/SQL/冻结/下发已闭环，更不能关闭116或判R07/TC068S2 P。全量454单测和上述服务探针也不替代业务验收。前端生产构建当前P；因服务无法登录/读取定义，未启动浏览器、模型或设备仿真器，不用旧版本界面截图充当当前实测。

## 逐项NT与解除条件

共同阻断链：117令真实生产服务退出 → 认证/定义/规划/执行/审计API不可用 → 相关浏览器/设备路径前置不足。尝试了真实JAR、隔离无DB Spring构造、数据库SELECT1及组件对照；未使用旧JAR或修改产品绕过。下一版本健康UP后必须重新实测下列全部项，历史P仅保留作对照。

| 规则 | 当前 | 本轮未能执行的完整范围 |
|---|---|---|
| R01 | NT | 三预置列表、删除保护与编辑恢复 |
| R02 | NT | 定义不写死步骤及同定义不同自主计划 |
| R03 | NT | 创建/编辑必填和边界、四类型动态表单、028/029/030原反例 |
| R04 | NT | 扩展沿既有页面、能力、协议的实际完整流程 |
| R05 | NT | 五/六步、条件动作、跨版本预算及最终实际执行路径 |
| R06 | NT | 未知/未启用能力的真实保存拒绝及合法对照 |
| R07 | NT | 116真实禁区/合法对照、规划上下文、冻结/指令、完成条件、基线/重规划 |
| R08 | NT | 创建/编辑/启停持久操作审计 |
| TC-068.S1 | NT | 定义维护与创建/编辑、真实配置界面 |
| TC-068.S2 | NT | 动态提交→模型→计划→校验→执行、停用/历史和116 |
| TC-069.S1 | NT | 三预置族删除/参数约束维护及恢复 |
| TC-069.S2 | NT | 重名、缺必填、未知/未启用能力完整保存拒绝 |

机器可读逐项范围、前置、尝试、解除条件：`evidence/SRS_F022-V1.176-per-item-blockers-20261107.json`。没有以“已遇F”解释独立项；实际运行服务是上述全部业务分支共同的不可绕过前置。

## 资源、证据与交接

GPT schema tip_gpt_f006_v118_20261030 / Redis10；数据库只读SELECT1成功；本轮没有业务任务/定义创建、设备/能力/预置/规则/模板配置修改，无需配置恢复。任务最大ID仍997，G176/F176记录0；既有自有代理均INACTIVE、IDLE、无current_task_id，注入触发器0。JAR进程自行退出；18129/18117/18132～18135/15179七端口无监听，没有新模型/适配器/前端进程遗留。共享PG/Redis及Claude资源未停/未重置，产品源码与V1.176差异为空。

主工作区没有测试运行、合并或写操作，main保持413e1b3。开工默认Git带引号的非ASCII路径导致哈希仅覆盖10文件而非初始口头所说40；该10个前后哈希一致，已用NUL/UTF8枚举补全40文件的当前清单，不冒称另30个具备开工前后哈希。明确更正见main-file-inventory-correction JSON，原记录保留。

原日志留本机，公开测试日志预先脱敏3个已结束Spring测试上下文的临时默认口令；真实凭据/令牌、原Office、JAR、用户文件和.local-test未提交。原V1.175 P/F/NT和原始证据保留，本轮台账更新前原文在ledger-before。完整证据先提交推送，再单写入者更新HANDOFF/ROADMAP/EXECUTION_BASELINE并填实际证据SHA。没有本轮main合并或PR，下一仅Claude修117并保留116修复后发新标签再F022整轮，不推进F023，不代表三核心或95项整体验收通过。
'''
(D/'SRS_F022-V1.176-整轮独立复测与启动阻断交修.md').write_bytes(text.encode('utf8'))
p=D/'阶段3-复测进度.md';t=p.read_text(encoding='utf8');entry='\n- **2026-11-07 / F022 V1.176 / V2.4：READY_FOR_CLAUDE，实际JAR启动F117**。规则0P/0F/8NT、四步骤0P/0F/4NT：PlanValidationService构造器装配失败/进程退出，12项逐条真实前置阻断，未用历史P/单测冒认当前业务P。454报告452通过2跳过、生产前后端构建P；无DB Spring同根复现，手动双mapper七参数服务4P仅局部，116未关闭。全部可独立项完成，配置未改/无业务新数据，七端口释放，main保持413e1b3未合本轮/无PR。报告`SRS_F022-V1.176-整轮独立复测与启动阻断交修.md`。\n';p.write_bytes(t.replace('\n','\n'+entry,1).encode('utf8'))
files=sorted(set(E.glob(PRE+'*'))|set((D/'fixtures').glob('*f022-v176*'))|{D/'fixtures/F022V176ContainerProbe.java',D/'register-f022-v176.py',D/'SRS_F022-V1.176-整轮独立复测与启动阻断交修.md'})
put('evidence-manifest',[{'path':str(p.relative_to(R)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files if 'evidence-manifest' not in p.name])
print(json.dumps({'verdict':'READY_FOR_CLAUDE','runtimeGate':'F117','rules':index['rules'],'steps':index['steps'],'component':'4P only','tests':tests['totals'],'files':len(files)},ensure_ascii=False))
