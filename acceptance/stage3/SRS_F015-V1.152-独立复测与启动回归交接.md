# SRS_F015 V1.152 独立复测与启动回归交接

- 日期：2026-11-04，Asia/Shanghai；需求/执行依据：stage0 V2.1 + V2.3补充，BL-001～004，未变更业务预期。
- 结论：**READY_FOR_CLAUDE；F015整项未通过，不合main，不推进F016。** 发布物启动闸门F（新回归DEF-S3-096），本版业务规则0P/0F/9NT、关联步骤0P/0F/6NT。启动F不冒充具体业务规则被实际执行后的F。
- 独立工作区：`C:/Users/savy/Desktop/TIP-main/tip-gpt-f013`，分支`ai/gpt-test`。已按开工顺序读取约定、交接、变更和路线图，检查status/log/worktree并fetch，无并行测试实例。工作区干净后快进接收Claude交接提交`ed6e9061db944c6b6c61eba03ba50630e58a8fc2`。
- 产品：`V1.152`实际指向`d86a722e2e56869f279ae25c82bcb6ab6d8ee30d`；远端main仍为F014最终交接`7d772f83f81d0cd589dc2db6fd622a65658810a5`，包含F014证据`d24bffb580300373a4f90df9e3aba72ed58e74e4`。标签未移动。证据提交与交接提交分两次推送，实际SHA见最新HANDOFF及Git。

## DEF-S3-096：V1.152新增构造函数令实际JAR无法启动

级别高；F015交付引入的独立启动回归。与历史DEF-S3-090同类，但090针对`TaskService`且已在V1.142关闭；此次是不同Bean `TaskExceptionService`在V1.152新增构造函数所致，不重开旧缺陷，也不将其当作环境/模型错误。

复现：

1. 使用接收的源码在GPT工作区运行`mvn -o package -DskipTests`，成功生成生产JAR。
2. 注入GPT独占配置：schema `tip_gpt_f006_v118_20261030`、Redis DB10、后端18129；本地PostgreSQL及Redis服务保持运行，无故障注入。通过环境变量提供凭据，不在证据或命令中输出凭据。
3. `java -Xms32m -Xmx192m -XX:TieredStopAtLevel=1 -XX:+UseSerialGC -jar backend/target/airport-ai-app-1.0.0.jar`。
4. 数据库连接成功，27条迁移验证成功，schema已是V27。创建`baselineDryRunService` → `taskExecutionOrchestrator` → `taskExceptionService`依赖链失败，进程退出1。
5. 实际异常：`Failed to instantiate [com.airport.ai.task.TaskExceptionService]: No default constructor found`；最底层`NoSuchMethodException: com.airport.ai.task.TaskExceptionService.<init>()`。健康检查未UP，登录入口连接被拒。
6. 同一JAR和隔离配置第二次完整启动，再现相同错误、退出1。两次原始完整日志保留。第二次结构化探针包含墙钟、PID、JAR摘要、健康轮询和业务入口结果。

源码与发布物交叉核对：V1.151为一个7参数public构造函数；V1.152新增8参数构造函数注入`PlanVersionMapper`，保留7参数构造函数并委托新构造函数传null。两者均无注入构造函数标记，也无默认构造函数。Spring不再满足单构造函数自动注入条件。`javap`确认编译类含两构造函数，JAR内该class与`target/classes`逐字节一致；`git diff V1.152 -- backend frontend`为空，未修改产品代码。

JAR SHA256：`18ed0cc45b1e1a628f4ed934972fe518b516c9f0e8a05d3d5ebbd34adac95409`。

建议修复方明确生产注入入口，并保证`PlanVersionMapper`真实注入，不能仅让7参数兼容路径传null后绕过启动，因为基线来源判断依赖该Mapper。完成打包后须实际启动JAR并检查健康/业务入口，再发布下一唯一V1.N标签。GPT不代修产品代码。

## 本轮实测、历史保留和业务范围

| 检查层级 | 当前证据与结果 |
| --- | --- |
| GPT定向及邻接单测 | 7个实际套件、41项，0失败/错误/跳过；37项F015交接组加4项ReplanningHighRiskDowngradeTest。未把Claude343项全量单测计入GPT实测 |
| 后端生产打包 | BUILD SUCCESS；`-DskipTests`不另计测试次数 |
| 前端生产构建 | 3269模块，成功；原有大chunk提示，无构建错误 |
| 生产JAR完整启动 | 两次均失败，合并为一个可复现发布物缺陷，不计作两条不同业务观察 |
| HTTP/SQL业务、浏览器交互、仿真设备任务、真实设备 | 当前均无有效业务观察；未产生新业务任务。HTTP连接拒绝不算接口业务断言通过；SQL仅用于只读核对环境/清理 |
| 历史复用 | 本轮没有将历史P复用为F015验收通过。保留原版本、原证据和原状态；编排、异常处理、模板选择及相关UI均有变更，需在可启动版本上继续实测 |

测试命令及实际套件清单见诊断JSON。命令中`TaskExceptionServiceTest`选择器未匹配到已有套件，实际执行数量按Surefire七套件求和为41，不虚构第八套件。

| 规则 | 关联步骤 | 当前V1.152状态及接回复测断言 |
| --- | --- | --- |
| R01 | TC-047.S1、TC-049.S1 | NT：高风险原候选不执行；已静态校验、真实试运行成功模板自动接管 |
| R02 | TC-047.S1 | NT：高风险、规划失败、模型不可用、校验页主动转基线四独立入口；目标/能力/五步约束 |
| R03 | TC-048.S2 | NT：原始目标不变，原计划与替换方案可追溯 |
| R04 | TC-048.S1/S2 | NT：基线结构/能力/约束再次校验，PASS才冻结并执行 |
| R05 | TC-049.S1 | NT：无匹配、停用模板、三类再校验失败各分支，待人工且原高风险零分配/指令 |
| R06 | TC-048.S1/S2 | NT：原计划版本、冻结模板版本、原因持久记录及操作员真实界面详情/链接/匹配依据；DEF067未关闭 |
| R07 | TC-047.S2 | NT：精确族优先、少步骤优先、真实最近试运行通过优先及事件选择依据 |
| R08 | TC-050.S1；邻接TC-059.S2 | NT：原83反例、合法恢复对照、候选穷尽后待人工；无重规划/机会消耗/二次基线；事件与异常表一致；DEF065/066未关闭 |
| R09 | TC-048.S1 | NT：执行中修改模板，继续使用冻结版本/步骤，模板新版本不污染运行计划 |

六个关联步骤为TC-047.S1/S2、TC-048.S1/S2、TC-049.S1、TC-050.S1，本版全部NT。台账累计仍保留**规则4P/1F/4NT、步骤0P/2F/4NT**，其中P/F源自旧版，绝非V1.152已复测或本轮可复用覆盖。原始台账行快照保存于`SRS_F015-V1.152-ledger-before-20261104.json`；本次只追加说明/证据，不删除历史失败或把历史P写成新版P。

ROADMAP暂存清单无F015待移植条目；F015实际源码差异含模板排序、异常事件、构造函数、编排冻结版本及前端路由/页面，不仅依据Claude声明判断交付。跨需求DEF066涉及F018/F020的完整验收仍待其顺序轮次；本轮未更改其历史F为P。

待复测线索：源码使用`updatedAt`表示“最近试运行通过时间”，而`enable()`同样更新时间。应以两模板真实试运行先后与启用先后相反作对照，判断实际选择是否符合R07；本轮因发布物无法启动未实测，不另编号为已复现产品F。通用/前缀族回退也需验证合法目标/能力与不匹配反例。未改变需求、用例或放宽标准。

## 证据、资源和交还

- `evidence/SRS_F015-V1.152-startup-attempt1-20261104.txt`：第一次完整启动原始日志。
- `evidence/SRS_F015-V1.152-startup-attempt2-20261104.txt`及同名JSON：第二次完整启动日志/结构化结果。
- `evidence/SRS_F015-V1.152-startup-diagnostics-20261104.json`：版本、JAR与class摘要、源码diff、javap、7套件数量、命令、SQL只读核对、资源/清理和探针诊断。
- `evidence/SRS_F015-V1.152-directed-20261104.txt`、`package-20261104.txt`、`frontend-build-20261104.txt`（后三者均以`SRS_F015-V1.152-`开头）：独立原始执行输出。
- `retest-f015-jar-startup.py`：可重跑JAR启动探针，外部环境提供独占数据库配置；输出文件存在即拒绝覆盖，可用新`--label`增补证据。

沿用既有GPT隔离schema/Redis10，不修改Claude资源及共享服务。两后端进程自行失败退出。已启动的自有模型18117和机器人18132在确认PID归属后停止；机器人尚未连接成功，未下发业务任务。18129/18117/18132/18134/18135/15179全部释放，本轮新增活跃分配0、最大任务ID仍222；未改规则/模板/设备/业务配置，无新增任务/版本需要删除。库内另有早期任务3/9/15/21/25/26/29共7条EXECUTING/PENDING_ASSIGNMENT历史分配行，原样保留并列入诊断，不能称全库活跃分配为0；本轮没有运行这些任务或清除旧数据。探针输出文件名及清理查询范围错误均已自行更正，原始启动内容未改、不增加启动次数，不登记为产品缺陷。

先推送独立证据提交，再单独更新HANDOFF/ROADMAP并推送。Claude接回后fetch并合入最新`origin/ai/gpt-test`，修复DEF096、核对R07线索，保留历史F/NT；实际JAR启动通过后发布下一标签及READY_FOR_GPT。GPT继续上述全部业务和UI范围；仅F015整项通过后才合main。本轮结论不代表后续需求、三核心场景或95项整体验收。
