# SRS_F017 V1.162 整轮独立验收与裁决

日期：2026-11-05，Asia/Shanghai。依据AGENTS、stage0 V2.1逐步/规则口径及V2.3/V2.4补充、既有BL004/BL006；无业务基线放宽。

**REQUIREMENT_PASSED：10规则10P/0F/0NT、6步骤6P/0F/0NT，全部本版当前实测，历史业务P验收复用0。** 104、068、B07-001本轮关闭；066的F017时间线范围通过，069的TC054正式执行关联闭环通过，其他需求范围保持其原裁决。V1.161启动F和所有历轮失败、NT及本轮夹具诊断保留。

报告生成时尚未合main：先推送证据，后更新HANDOFF/ROADMAP并安全同步main。实际合入SHA及最终交接以本轮后续`main-integration`证据和HANDOFF最新一节为准，不提前宣称已推送main。

## 版本和资源

- 产品：`V1.162` → `b2623730a0c85622091e6e18bcb1207e23ecdd42`；Claude交接：`d4bdab45c05fb0fc595f3dbf13ae6e9726521408`，状态READY_FOR_GPT，标签远端核对一致、不移动。
- 开工main：`75c3bf97ea8df90d462b99035de3a8e4dd2587d5`，已包含F016独立验收；GPT干净工作区fetch后快进接收交接，保留V1.161证据提交930f64b和最终交接05068b8。
- GPT独立工作区：`C:/Users/savy/Desktop/TIP-main/tip-gpt-f013` / `ai/gpt-test`；主工作区只在验收通过后安全同步main，40个用户未跟踪文件在合并前逐一留本机哈希，未作为测试运行环境。
- 资源：schema `tip_gpt_f006_v118_20261030`、Redis DB10、JAR18129、受控模型18117、协议设备18132～18134、Vite15179。复用GPT自有退役设备G160_F016_A/B/C及G145_F013_SCAN/DISPLAY；启用前核对无占用，未新建或夺占他人设备/端口。
- V1.162实际产品改动仅为超时组件构造函数注入及相应装配单测；ROADMAP无F017待移植条目。未整支合并staging，未修改产品代码。`git diff V1.162 -- backend/src/main frontend/src`为空，JAR中超时组件class与本机固定源码编译class逐字节一致，摘要在版本JSON。

## 本轮实测与计数

| 层级 | 本轮结果 | 证据限制 |
| --- | --- | --- |
| 全量后端单测及打包 | `mvn -o package`：372报告、370通过、0失败/错误、2原有跳过；BUILD SUCCESS | 不照抄Claude交接374/372；实际原始汇总372/370为本轮依据 |
| GPT独立组件与邻接 | 34组件P（含Spring装配、80k同JVM编号、8类禁止/5类合法意图、重试及谓词/超时边界）＋3归属/接受后离线邻接P | mock存储/网关、受控时间的服务层，不能代替持久业务验收 |
| 前端构建 | `npm run build`成功，3269模块，保留原有chunk提示 | 本轮真实Edge操作另行取证 |
| 实际生产JAR | Flyway V29、健康UP，认证、tasks、agents、dashboard/overview均HTTP200 | 非源码运行、非旧版后端；模型为受控夹具 |
| 实际HTTP/SQL/设备协议任务 | 60个任务433～492：58正式＋2成功试运行 | 按下方去重表区分有效、诊断及重复 |
| 有效独立观察 | 去重35任务观察35P，其中33正式＋2成功试运行 | 同一观察映射多规则/步骤不增加执行次数 |
| 夹具诊断及重复 | 23任务为前置/探针诊断，2任务是同版重复观察 | 原始暂定F/报错不删除；更正、替代证据逐项映射，不记产品F |
| 真实Edge | 433只收到0/2、首步完成1/2、完成2/2；435重试失败0/2；488超时0/1，五页DOM/API/PNG均通过、无JS错误 | Edge无头真实浏览器，没有响应拦截或伪造DOM；不声明真实硬件或模型质量 |

精确总数为**60任务＝35有效独立观察＋23诊断任务＋2重复有效任务**；任务类型为**58正式＋2成功试运行**。逐项ID分类见`probe-corrections`。试运行是453、486；重复有效任务458、467不新增覆盖，采用最终470、479完整证据。核心四渠道及普通行李分支只是本需求必要关联，不能据此宣称三核心场景全部验收。

## 规则及步骤裁决

| 规则 | 当前证据与结果 |
| --- | --- |
| R01 P | 原生状态写入夹具只匹配F162任务，观察PLANNING、SUPERVISING、PENDING_ASSIGNMENT、DOWNGRADING、EXECUTING、COMPLETED、FAILED、PENDING_MANUAL、MANUAL_TERMINATED全部九状态；433/448/454/455/488覆盖合法路径，UI进度与当前状态一致。内部短暂状态通过事务内数据库观察，不冒称浏览器逐帧可见 |
| R02 P | 433承接与执行指令分别唯一、格式27字符；434/435真实首发HTTP500后同号attempt0→1、最多一次自动重试；479设备FAILED后重试成功；485同字节反馈重放HTTP200且仅一次完成/下发，attempt -1/2及错误代理拒绝且不改完成状态 |
| R03 P | 435两次下发均失败，STEP_FAILED、异常与影响判断持久；470两次SUCCESS却不满足条件亦失败、无后步；488超时后待人工且占用释放。恢复过程与终态分开核对 |
| R04 P | 480前往区域、481会合、482陪同、483空间引导、484现场通知，分别通过CAP_NAVIGATION/CAP_ESCORT/CAP_NOTIFICATION的统一代理真实协议下发并完成，SQL结果与反馈一致 |
| R05 P | 471～478逐一注入速度、加速度、姿态、路径点、避障、急停、限速、失联停靠对应字段。HTTP承接后COMMAND_DISPATCH_BLOCKED/ERR_MOTION_SAFETY_FIELD持久，事务内步骤FAILED/原因写入可查，无EXECUTE记录或设备业务收包；正常合法对照480～484通过 |
| R06 P | 448模型503、449不可解析、450结构缺字段、451虚构能力、452运动约束失败均零未经校验指令；487模型503有合法基线时仅经三类校验/冻结的基线执行完成，原失败候选不执行。依TC056详细预期及既有BL004，未把合法降级指令隐去 |
| R07 P | 433适配器收到业务消息只返回HTTP200/received=true/“已收到”，延迟实际执行反馈期间步骤仍EXECUTING、后步零指令；TASK_ACCEPT承接与业务完成独立。468～470明确谓词对照也通过 |
| R08 P | 433必须首步满足完成条件并释放占用后才发第二步；468计划false而反馈true，同号一次重试后仍失败且后步零指令；469计划false/反馈false两步合法完成；470计划true/反馈false不完成、不提前下发；439/488超时不提前后步 |
| R09 P | 433全部两步条件满足后才TASK_COMPLETED；491超规测量→上报→智慧航显→引导四渠道自主计划三类PASS/冻结、按序实际执行完成；492普通行李仅测量，后3步SKIPPED且无业务指令，任务正常完成 |
| R10 P | 当前任务事件覆盖GOAL_SUBMITTED、PLAN_VALIDATED、SUPERVISION_JUDGED、分配/承接、STEP_DISPATCHED、EXECUTION_FEEDBACK_RECEIVED、STEP_RETRY_DISPATCHED、失败/超时/待人工/失败终态/人工终止/完成；与状态观察、SQL指令/异常和真实Edge时间线一致，未仅看接口成功 |

六步骤全部P：TC054.S1映射433/491/492；TC054.S2映射433/448/454/455/491/492；TC055.S1映射434/435/479/485；TC055.S2映射468/469/470/439/488；TC056.S1映射471～478；TC056.S2映射448～452、480～484、487。每项具体断言见`scope-verification`，当前需求没有历史P代替本版实测。

## 缺陷与原始反例

- **104关闭**：实际JAR启动成功、健康UP、认证和关键入口200；独立Spring装配通过；488实际等待约30～40秒后FAILED/TIMEOUT/ERR_EXECUTION_TIMEOUT、指令TIMED_OUT、持久异常、转人工、释放占用，进一步证明PlanVersionMapper/DeviceCommandMapper生产注入有效。V1.161原失败完整保留。
- **068关闭**：真实Edge分别显示0/2当前步骤1、1/2当前步骤2、2/2无当前步，并有重试失败和超时进度对照；原V1.5只有步骤行、无明确进度指标的失败不改写。
- **DEF-B07-001关闭**：468重现原false谓词/true反馈反例并正确拒绝完成；469 false/false合法对照实际完成；470 true/false反向边界失败。均为真实HTTP、冻结计划及设备回调和数据库证据，不再仅是组件比较。
- **066**：F017状态时间线当前通过；保留F015关闭和F018/F020各自范围，不代替其整项验收。
- **069**：491/492使F017/TC054正式执行关联闭环；F024/TC072完整场景仍待对应需求，未宣称全范围关闭。
- 无新增可复现产品F或本需求NT。错误烟测URL`/dashboard/metrics`返回500属于已有未知路径DEF061涉及的其他需求范围；本轮修正探针使用现有`/dashboard/overview`，没有将错误URL当F017失败或冒写200。

## 夹具更正、边界层级和保留记录

完整逐任务更正表在`probe-corrections-20261105.json`。436/437/456/457的false计划与任务定义true条件冲突，产品正确硬拒绝；最终468/469同时对齐任务定义及两步条件后执行原始反例/合法对照。438取到旧attempt0，并改变reportedAt触发载荷冲突，最终按seq/attempt过滤，470通过。

440～447创建HTTP任务后Windows psql `-c`中文argv编码失败，未进入注入步骤；改为UTF-8 stdin，找回全部ID并通过产品接口终止，未当产品缺陷。439及459～466的原始暂定F来自仅检查恢复后的快照：步骤先FAILED后允许候选恢复变PENDING_ASSIGNMENT。新增只匹配本轮任务的赋值状态写入夹具，471～478实证FAILED及精确原因先于恢复；488无替代候选的基线超时另证终态持久，未放宽失败标准或覆盖原始记录。

任务定义PUT不得传不可变taskName、设备启用应先连接测试、超规智慧航显必须SMART_DISPLAY等前置问题均自行修正；489/490错误移动机器人渠道被正确硬拒绝，491/492使用既有GPT智慧航显后通过。临时夹具错误、同版重复观察、恢复后快照与产品偏差分别登记，没有删除失败文件或新增同根编号。

471～478使用限定SQL修改**本轮自有已冻结计划**以到达下发阶段防线；原冻结计划、注入值、任务ID和后续轨迹均保存。这不是产品提供冻结计划编辑接口的证明，也不表示自然业务可以绕过前置校验。两个临时审计触发器只观察F162任务的原生写入，导出后已删除，未改产品实现。

## 清理、可重跑入口和证据

规则启用值已恢复；自有模板/扩展定义已停用，设备恢复INACTIVE、代理无占用，本轮任务全部终态。CAP_ESCORT/NOTIFICATION原UNTESTED不能通过只接受ENABLED/DISABLED的状态API恢复，原四次400保留；确认无占用后限定SQL恢复原配置值，能力测试历史不删除。scanner/display能力状态按测试前快照恢复。

JAR、模型、Vite进程树均核对PID/命令归属后停止；18129/18117/18132～18134/15179无监听。60任务当前活跃分配0、代理占用0，观察触发器/表/函数0残留；历史任务及失败版本保留，不批量清理。临时Java测试源已移除，稳定源码/协议夹具留在stage3，私有配置仍只在本机。设备token哈希/密文与自动生成安全密码在任何提交前脱敏，原始Office、DPAPI、私有环境和用户文件未提交。

证据前缀均为`acceptance/stage3/evidence/SRS_F017-V1.162-`：

- `version-and-execution`：完整SHA/标签、JAR及class摘要、命令、实际测试数量和批次ID。
- `http`、`supplement`、`final`、`extra`、`baggage-final`：原始HTTP、SQL、设备收包、事件/状态观察与合法/反例；旧诊断批次也保留。
- `ui-receipt/middle/completed/retry-failed/silent-timeout`：五页真实Edge DOM/API/PNG。
- `backend-build`、`frontend-build`、`independent-components`、`independent-neighbors`、`jar-runtime`和各批console：原始运行输出；`model-requests`为受控模型请求/响应。
- `probe-corrections`、`scope-verification`、`ledger-before`、`final-environment`、`complete-verification`：更正/去重、覆盖映射、历史台账和清理/完整性。

可重跑代码：`probe-f017-v162.py`公共夹具，`round.py`/`supplement.py`保留最初探针版本便于解释诊断，稳定业务边界见`final.py`、`extra.py`、`baggage.py`及真实UI脚本；`fixtures/start-f017-v162-jar.py`、`f017-v162-controlled-model.py`、`IndependentF017V162Test.java`。运行依赖本机既有私有环境，必须使用声明的自有schema/端口并顺序执行；现有证据路径存在时探针拒绝覆盖，应选新输出标签。

下一需求为SRS_F018，由后续独立启动；本次只裁定F017，不代表后续需求、三核心场景或95项整体验收完成。

## 最终main实际合入

验收交接`ccaed0f4e6c1fdd695c95fcca0947801992cdbf8`已安全快进合main并普通推送，远端实际SHA核对一致。证据提交`6db8a6a498a8d8a8555ec65dd5a0f688c494387c`在先；40用户未跟踪文件哈希前后不变，无PR/强推/reset，产品V1.162标签不移动。合入证明见`evidence/SRS_F017-V1.162-main-integration-20261105.json`；本最终记录提交后再同步两分支。
