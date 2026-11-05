# SRS_F017 V1.161 独立复测与启动阻断裁决

日期：2026-11-05，Asia/Shanghai。执行依据为 AGENTS、stage0 V2.1 逐步/规则口径、V2.3补充和V2.4整轮规则；BL006继承，无业务基线改动。

**整项未通过，READY_FOR_CLAUDE。当前业务规则0P/0F/10NT、步骤0P/0F/6NT；发布物启动闸门另计1F（DEF-S3-104）。不合main、不推进F018。** 当前NT是生产JAR不能启动造成的真实前置阻断，不将组件P、构建成功或历史P写成业务验收通过。

## 版本与交接核对

- 产品完整SHA：`283a1b8925bdd0e5647913374d652c1556807f81`；标签`V1.161`实际解引用一致，不移动。
- Claude交接：`origin/ai/claude-fix` / `08841fcb44f0913946b633e58ef15eb5a78acf1f`，最新HANDOFF为READY_FOR_GPT。
- F016已验收并合main：验收文档`c1844a9b191d711900f80701d1b4793c3598b0e0`；开工远端main为最终交接`75c3bf97ea8df90d462b99035de3a8e4dd2587d5`。
- GPT独立worktree：`C:/Users/savy/Desktop/TIP-main/tip-gpt-f013` / `ai/gpt-test`，干净后快进合入Claude交接；没有占用冲突或竞争测试实例。主工作区保留用户未跟踪文件，未在主工作区运行测试或修改文件。
- 本轮实际产品差异只有`CommandIds`、`StepTimeoutMonitorTask`及Claude专项单测。ROADMAP无F017专属待移植条目，未合并staging。068/066/B07旧实现只作为本轮待验收对象，不依据“已实现”直接关闭。
- 首个失败检查点已推送`49a5ce4b70b9dd02650f11606ee53ee79382bb62`；完整证据提交随后先推送，再更新HANDOFF/ROADMAP记录实际SHA。

## DEF-S3-104：生产JAR构造函数注入回归

预期：打包JAR在GPT独占资源上启动，健康UP，可进行认证及任务、设备关键入口冒烟。

实际：2026-11-05 15:00，JAR PID1596连接PostgreSQL成功、Flyway校验通过且schema为V29，随后`stepTimeoutMonitorTask`创建失败，进程退出，健康未UP。原始异常为`BeanCreationException` → `BeanInstantiationException: No default constructor found` → `NoSuchMethodException: com.airport.ai.task.StepTimeoutMonitorTask.<init>()`。健康、登录、tasks、device-agents探测均未取得HTTP响应；不把连接超时当HTTP状态码。

复现：

1. 在本独立worktree对固定产品执行`mvn -o test package`，生成`backend/target/airport-ai-app-1.0.0.jar`。该命令日志中370项报告，368实际通过，2项原有跳过。
2. 使用`python acceptance/stage3/fixtures/start-f017-v161-jar.py`；本机私有配置仅从既有环境读取，不提交凭据。启动命令为`java -Xms32m -Xmx192m -XX:TieredStopAtLevel=1 -XX:+UseSerialGC -jar backend/target/airport-ai-app-1.0.0.jar`。
3. 检查日志及健康轮询，得到上述失败。数据库连接、迁移均已成功；未开启模型和设备并不影响该Bean创建，也没有外部服务调用失败证据。
4. GPT独立Spring探针仅注册必要边界mock singleton和真实`StepTimeoutMonitorTask`，同样出现`No default constructor found`。此为组件层独立复现，不冒称第二次完整JAR启动。

V1.160只有一个public构造函数；283a1b8新增第二个public构造函数，两者均无生产注入入口标记、也无默认构造函数。JAR内该class与固定源码编译的class逐字节一致；`git diff V1.161 -- backend/src/main frontend/src`为空，排除测试者产品改动。JAR摘要见版本JSON。

这是本轮不同Bean新增的启动回归，虽与历史已关闭DEF090/096同型，仍独立编号104，不重开旧缺陷。建议Claude明确生产构造函数注入，确保`PlanVersionMapper`、`DeviceCommandMapper`实际注入且超时指令终态回滚仍生效；实际打包启动并验证健康/业务入口后发布下一唯一标签。GPT未修改产品代码或替换Bean绕过缺陷。

## 已执行的独立检查及其限度

| 层级 | 当前结果 | 限度 |
| --- | --- | --- |
| 仓库全量单测 | 370报告，368P、0失败/错误、2原有跳过 | GPT本轮实际执行；含Claude F017专项10项，不能称为真实端到端测试 |
| 后端打包、前端生产构建 | 均成功；前端3269模块，原有chunk提示 | 构建通过不等于可运行或业务通过 |
| GPT独立有效组件检查 | 去重37项：36P、1启动F | 有效失败对应Surefire Error；另两次夹具错误排除，不增计产品缺陷 |
| 8线程指令编号 | 同JVM 80,000个编号唯一且符合27字符格式 | 不声明跨JVM/重启唯一性或全局并发负载验收 |
| 安全与合法意图 | 8类检测+8类真实编排器下发边界拦截、5类guard+5类统一消息入口对照，均P | 存储、网关依赖mock；拦截事件为服务调用，非持久数据库/物理设备证据 |
| 完成条件及重试 | false谓词原反例/合法对照、只收到、合取条件；同号单次重试/最终失败影响判断，均P | 未执行真实HTTP顺序多步或设备幂等副作用 |
| 超时及直接邻接 | 自定义30秒前20/后40秒边界P；既有独立本任务/其他任务超时归属2P、精确承接后离线1P | 受控时间和存储的服务层；不冒称真实定时器等待或持久指令TIMED_OUT观察 |
| HTTP业务/数据库业务写入/浏览器/仿真设备/真实设备 | 无有效业务执行，逐项NT | 健康前置失败；未造任务、未启动设备/模型或以旧版后端替代 |

去重说明：第一批23报告中22P、1夹具Error；扩展批34报告中33P、1同夹具Error，重复19个有效P不新增计数；修正后仅运行Spring检查1项、实证产品F。因此有效独立观察为33个F017组件P＋3个邻接P＋1启动F。两次错误来自Spring对注册的mock执行真实字段注入，缺少mock内部`BaselineDryRunLifecycle`；改为预构造singleton后已排除此夹具错误。原日志完整保留，早期“独立Spring已复现”的口头判断已更正，最终以corrected日志为准。没有因夹具错误交修产品。

## 完整范围与逐项阻断

| 规则 | 关联步骤 | 当前结果及未完成断言 |
| --- | --- | --- |
| R01 | TC-054.S2 | NT：九状态全部路径、真实迁移及页面进度 |
| R02 | TC-055.S1 | NT：真实首发失败→同号一次重试→成功、幂等副作用及持久指令 |
| R03 | TC-055.S1 | NT：重试仍失败后持久异常/影响判断与恢复结果 |
| R04 | TC-056.S2 | NT：五类合法业务意图经真实统一代理协议下发 |
| R05 | TC-056.S1 | NT：8类待下发字段逐一拦截、持久失败/事件/原因与设备零收包 |
| R06 | TC-056.S2 | NT：模型异常、三类校验失败零未经校验指令；合法降级基线重新校验 |
| R07 | TC-054.S1 | NT：独立只收到→等待→满足计划条件反馈链路 |
| R08 | TC-054.S1/TC-055.S2 | NT：真实多步顺序、false谓词原反例/合法对照，未满足前后步零指令 |
| R09 | TC-054.S2 | NT：全部可执行步骤完成后整体完成及持久结果 |
| R10 | TC-054.S2 | NT：下发/反馈/重试/状态迁移全量持久时间线及真实UI |

六步骤TC-054.S1/S2、TC-055.S1/S2、TC-056.S1/S2均NT，阻断链均为104→生产应用无健康上下文→无法创建/认证业务任务和设备回调→对应持久/UI断言无前置。已尝试生产重新构建、DB/Flyway核对、JAR/class核对和独立Spring隔离；不属于可自行修复的环境错误。剩余组件、构建和归属检查已完成；不绕过产品Bean，也不以旧标签替代固定版本。解除条件是Claude新标签可启动，随后按V2.4完整重测上述每个分支。

历史业务P复用0。旧规则4P/1F/5NT、旧步骤0P/1F/5NT的原始行保存在ledger-before快照，原actual、evidence及缺陷记录留在当前行并追加说明；当前status改为NOT_RUN表达本版NT。068进度旧F未关闭；066的F015已关闭范围保留，F017时间线本版NT；B07完成谓词组件对照P但完整链路仍NT。069的F017正式多步关联亦无本版闭环。无需求放宽、无正式矩阵删除或编号复用。

## 资源、清理及证据索引

GPT自有schema`tip_gpt_f006_v118_20261030`、Redis DB10、后端18129；保留模型18117、设备18132～18134、前端15179供本轮，但因启动失败未启动后者。未碰Claude资源或共享服务故障注入。JAR自行退出；本轮临时测试源已移除，稳定探针保存在fixtures；无产品源修改。

上述6端口最终均无监听，设备代理占用数0，本轮新任务/分配0、业务配置修改0。只读核查发现7条历轮待人工任务的旧非终态步骤（任务3/9/15/21/25/26/29，2026-10-30至11-01），它们不是本轮遗留，不批量修改或删除；完整清单及SQL保留。最新任务仍432。本轮没有模板/设备/规则变更需恢复，所有失败日志及历史任务保留。

证据同目录`evidence/SRS_F017-V1.161-*`：

- `version-and-startup-20261105.json`：完整SHA、JAR摘要、资源归属及实际产品差异。
- `jar-startup-20261105.txt`、`startup-driver-20261105.txt`：完整JAR失败与启动驱动日志。
- `backend-build-20261105.txt`、`frontend-build-20261105.txt`：实际构建与全量测试。
- `independent-initial-20261105.txt`、`independent-expanded-20261105.txt`、`spring-corrected-20261105.txt`：组件原始日志，含保留的夹具诊断与修正复测。
- `scope-and-blocking-20261105.json`：10规则、6步骤的独立断言、阻断依赖和接回复测条件。
- `ledger-before-20261105.json`：更新前原始台账快照；`environment-and-cleanup-20261105.json`：端口、SQL、遗留归属及产品源码一致性。
- `complete-verification-20261105.json`：最终数量、去重/夹具更正、文件完整性及main核对。

可重跑探针：`fixtures/IndependentF017V161Test.java`和`fixtures/run-f017-v161-independent.ps1`（复制临时测试源后finally清理）；`fixtures/start-f017-v161-jar.py`需要本机既有GPT私有环境。不得提交原始Office、私有环境、DPAPI或未脱敏日志。

下一步仅由Claude在独立`ai/claude-fix`接收本轮完整证据，修104并验证生产发布物，交下一标签READY_FOR_GPT，再开展F017整轮。F016已有验收不被本轮改写；本轮不代表后续需求、三核心场景或95项整体验收。
