# 双 AI 协同修复工作梳理汇总与执行全景路线图 (ROADMAP)

> **当前基准**：V2.4（2026-11-04 用户追加整轮复测授权；继承V2.3，见BL-005；下方既有产品验收/交接记录保留原执行版本）
> **主干验收合入提交**：F016验收合入 `c1844a9b191d711900f80701d1b4793c3598b0e0` / `75c3bf9` 已安全快进main并推送。
> **最新产品代码提交**：`283a1b8`（真实完整SHA：`283a1b8925bdd0e5647913374d652c1556807f81`，标签`V1.161`）
> **交接状态**：`READY_FOR_CLAUDE`（F017 V1.161发布物启动F/DEF-S3-104；规则0P/0F/10NT、步骤0P/0F/6NT；证据930f64b已先推送，main保持75c3bf9）
> **文档定位**：本文件为跨会话、跨需求修复推进的**唯一全景进度与依据底账**。每轮需求修复与复测验收后必须同步更新本文件。

---

## 一、已验收完成需求基线（SRS_F001 ～ SRS_F016）

经过双 AI 协同修复与独立复测，前16项功能需求（含分支共18项条目）全部通过独立验收；F001～F016已安全合main并推送，F016验收合入c1844a9b191d711900f80701d1b4793c3598b0e0，最终交接随本提交同步。F013、F014按V2.3明确区分当前实测与经影响复核的历史观察，详见其独立报告；F015/F016按V2.4全部适用项当前实测：

| 需求编号 | 需求名称 | 规则状态 | 用例覆盖 | 核心成果与修复缺陷 | 验收版本 | 状态 |
|---|---|:---:|---|---|:---:|:---:|
| **SRS_F001** | 用户登录与预置角色权限 | 9/9 P | TC-001～TC-003 | 越权优先拦截（403/ACCESS_DENIED）、密码锁定审计不泄密、密码哈希序列化移除 | V1.110 |  PASSED |
| **SRS_F002** | 平台概览展示 | 8/8 P | TC-004, TC-005 | 在线率/负载卡片实时联动、告警级别筛选、告警确认与处理流转 | V1.112 |  PASSED |
| **SRS_F002A** | 航站楼示意图与关键位置标绘 | 5/5 P | TC-006 | 地图位置标绘与坐标转换校验 | V1.113 |  PASSED |
| **SRS_F003** | 设备对接与心跳维持 | 8/8 P | TC-007～TC-009 | 隔离心跳超时检测、离线状态机流转、设备上下线事件上报 | V1.115 |  PASSED |
| **SRS_F004** | 设备注销与配置变更 | 8/8 P | TC-010～TC-012 | 软删除状态控制、注销设备拒绝分派任务、审计留痕 | V1.117 |  PASSED |
| **SRS_F005** | 设备状态上报与冲突判定 | 8/8 P | TC-013～TC-015 | 并发状态上报版本控制、冲突消除机制 | V1.119 |  PASSED |
| **SRS_F006** | 设备分组与关联管理 | 9/9 P | TC-016～TC-018 | 区域-分组层级校验、组内设备批量调度与隔离 | V1.121 |  PASSED |
| **SRS_F006A** | 设备边界防护与越界处置 | 12/12 P | TC-019 | 电子围栏越界检测与紧急制动安全指令拦截 | V1.123 |  PASSED |
| **SRS_F007** | 统一设备信息查询 | 8/8 P | TC-020～TC-022 | 多条件组合查询、分页排序、能力标签反查 | V1.126 |  PASSED |
| **SRS_F008** | 高峰模板定义与维护 | 8/8 P | TC-023～TC-025 | 预置模板结构完整性校验、模板版本冻结与发布 | V1.128 |  PASSED |
| **SRS_F009** | 智能体基线模板库 | 8/8 P | TC-026～TC-028 | 典型业务降级基线模板、前置与后置动作绑定 | V1.130 |  PASSED |
| **SRS_F010** | 形式化任务目标提交与解析 | 10/10 P | TC-029～TC-031 | 形式化语法树校验、目标参数清洗与脱敏、歧义澄清初筛 | V1.136 |  PASSED |
| **SRS_F011** | 规划上下文快照与隐私保护 | 8/8 P | TC-032～TC-034 | `SceneParamsPrivacyGuard.sanitizeGoal` 脱敏全链路生效、快照只读冻结 | V1.138 |  PASSED |
| **SRS_F012** | 候选计划生成与五步限额 | 10/10 P | TC-037, 038, 061 | 六必需字段硬校验（DEF-S3-034）、循环语义拦截（DEF-S3-071）、条件节点折叠与五步限额、详情展示（DEF-S3-036） | **V1.139** |  PASSED |
| **SRS_F013** | 计划三类校验与冻结机制 | 9/9 P（累计，含注明来源历史复用） | TC-039～TC-042，9/9步骤P | DEF-S3-089～094均有关闭证据；三来源完成条件矛盾硬拒绝、合法重复/合取冻结监督、真实超时局部版本保护、400/4110与持久留痕。当前15场景、2次强放行、43项定向全部通过；证据/合入`d8e29a8` | **V1.149** | PASSED |
| **SRS_F014** | 特殊旅客服务规划与监督判定 | 10/10 P（含注明原SHA的V1.150 UI/CRUD影响复用） | TC-043～TC-046；8/8步骤P | DEF041/042原关闭保留，043/095本轮关闭；三规则同候选启停、会合/陪同、公共发布、精确边界/全部组合、基线成功/失败、监督故障及持久硬闸门通过。58项定向+4项独立组件通过。 | **V1.151** | PASSED；已合main d24bffb |
| **SRS_F015** | 高峰/基线降级与故障边界 | 9/9 P（V2.4全部当前实测） | TC-047～TC-050，6/6步骤P | 066真实双候选中间态/最终反馈及SQL一致、098两弹窗版本准确本轮关闭；065/067/096/097当前回归保持关闭。29真实任务、43项定向、生产构建/JAR健康与真实Edge通过；无历史业务P替代。 | **V1.156** | PASSED；已合main 949c3b3 |
| **SRS_F016** | 步骤设备匹配与任务接受 | 8/8 P（V2.4全部当前实测） | TC-051～TC-053，5/5步骤P | 100/103关闭，099/101/102保持关闭；36任务/30独立观察、独立服务3P、真实JAR/HTTP及Edge5页通过；历史失败保留。 | **V1.160** | PASSED；已合main c1844a9 |

---

## 二、暂存改动（WIP / Staging）规整映射表

暂存改动位于 **`origin/ai/claude-staging`**（基线 `d66703e`，已推送；先 `git fetch origin ai/claude-staging`）。**严禁整分支合并**，必须在进入对应需求修复会话时只摘取该需求对应的提交：

- 移植方法：`git cherry-pick <哈希>` 或手工比对移植核心变更；冲突时以 `main` 当前代码为准，保留 `main` 上已有的行为，严禁用暂存分支旧文件整文件覆盖 `main`。
- 移植后立即把下表该行状态改为 `已移植（版本号）`，并在 Git 提交说明里写明原提交哈希（如 `ported from ai/claude-staging commit <hash>`），避免重复移植或重复登记。
- 每个提交内的自检脚本（`*.check.mjs`）和单测一并带走。
- 暂存分支的完整说明见该分支上的 `docs/CLAUDE_STAGED_FIXES.md`。
- 分支内各提交彼此无顺序依赖，但 `4ec6695`、`332e250`、`01afe2d` 都改了 `TaskService.java` / 审计相关文件，同一会话里移植多个时注意按需求分别解决冲突。

| 暂存来源 | 涉及文件 | 覆盖缺陷 / 规则 | 对应目标需求 | 移植策略与注意事项 | 状态 |
|---|---|---|:---:|---|:---:|
| **commit `4ec6695`** | `CreateTaskDefinitionRequest.java`<br/>`UpdateTaskDefinitionRequest.java` | **DEF-S3-030** (`F022.R03`) | **SRS_F022** | 约束描述 `@NotBlank` (<=500) 校验 | 待移植 |
| **commit `4ec6695`** | `RiskRuleController.java`<br/>`RiskRuleValidationTest.java` | **DEF-S3-041** | **SRS_F014/F022** | 风险规则 code/content 必填与长度校验 | **已移植 (V1.150)** |
| **commit `4ec6695`** | `GlobalExceptionHandler.java`<br/>`GlobalExceptionHandlerStatusTest.java` | **DEF-S3-058/061** | **SRS_F021/F027** | 不支持请求方法返回 405 + Allow，未知路径 404 | 待移植 |
| **commit `4ec6695`** | `TaskService.java` (`terminateTask`) | **DEF-S3-059** (`F021.R08`) | **SRS_F021** | 终止任务联动下发取消指令，审计详情记录取消结果与 cancelCommandId | 待移植 |
| **commit `4ec6695`** | `TaskService.java` (`handleManualAction`)<br/>`ManualActionRequest.java` | **DEF-S3-062** (`F020.R08`) | **SRS_F020** | 人工操作记录原因，`MARK_FAILED` 强制要求原因并写入 `TASK_FAILED` 事件 | 待移植 |
| **commit `64d1f8e`** | `TaskController.java`, `TaskMapper.xml`, `TaskService.java` | **DEF-S3-006** (`F020.R06`) | **SRS_F020** | `GET /tasks` 支持 `goalKeyword` 模糊查询，安全转义通配符 | 待移植 |
| **commit `64d1f8e`** | `TaskDetailView.vue` | **DEF-S3-007** | **SRS_F020** | 任务详情 404 告警并安全回退列表页，停止轮询 | 待移植 |
| **commit `64d1f8e`** | `TaskListView.vue`, `taskListView.js` | **DEF-S3-060** (`F020.R04`) | **SRS_F020** | 待人工接管任务橙色标签与左侧提示条醒目高亮 | 待移植 |
| **commit `332e250`** | `RequiredInfoGuard.java`<br/>`TaskService.java` | **DEF-S3-003** (`F024.R03`)<br/>**DEF-S3-004** (`F025.R01`)<br/>**DEF-S3-005** (`F026.R04`) | **SRS_F024**<br/>**SRS_F025**<br/>**SRS_F026** | 系统端强校验超规行李、特殊旅客、航班变动的必需字段；完整时发 `INFO_CHECK_OVERRIDE` 放行，替代大模型幻觉追问与套取旅客隐私 | 待移植 |
| **commit `01afe2d`** | `AuthService.java`<br/>`OperationLogService.java`<br/>`UserService.java`<br/>`AccountAuditDetailTest.java` | **DEF-S3-009** (`F028.R03`) | **SRS_F028** | 用户创建、重置密码、状态切换、解锁操作记录带 `before`/`after` 结构化摘要，不含密码明文或哈希；解锁详情为合法 JSON 并经同一脱敏 | 待移植 |
| **commit `c9a7d5f`** | `EventReasonCodes.java`<br/>`TaskEventService.java`<br/>`EventReasonCodesTest.java` | **DEF-S3-057** (`F027.R02`) | **SRS_F027** | 每条任务事件都有原因码：调用方显式给的保留，缺失时按事件类型补 `NORMAL_*`/`ERR_*`/`WARN_*`；扫描测试保证新增事件类型必须登记。**取值是约定，SRS 未定义，需求方可改 `EventReasonCodes`** | 待移植 |
| **commit `6f7f389`** | `TaskTraceView.vue` | **DEF-S3-008** (`F027.R01`) | **SRS_F027** | 追溯页每个计划版本展开后显示来源、冻结时间、校验错误清单和步骤明细表（含被替换的历史版本） | 待移植 |
| **commit `efe0790`** | `SituationController.java`<br/>`SituationView.vue`<br/>`situationMarkers.js`<br/>`SituationOfflineInfoTest.java` | **DEF-S3-047**、**DEF-S3-048** | **SRS_F023** | 态势快照为离线代理带 `offline`（原因码、离线时间、是否影响任务）；页面离线上报时间红色高亮、详情显示原因码与任务影响；标记层级 选中>离线>忙碌>空闲，悬停置顶，离线终端不再被机器人遮住 | 待移植 |
| **commit `e2d50d2`** | `RiskRuleView.vue`<br/>`riskRuleForm.js` | **DEF-S3-042** | **SRS_F014** | 风险规则页新增弹窗 | **已被 main 取代，勿移植**（`69b841f` / V1.150 已实现等价功能） |
| **commit `2099c75`** | `TaskDetailView.vue`<br/>`planSummary.js` | **DEF-S3-036** | **SRS_F012** | 计划详情步数/剩余额度/输入参数/参数来源 | **已被 main 取代，勿移植**（`6de0e9e` / F012 已验收；main 另有"规划说明"） |

---

## 三、后续需求全景推进台账（SRS_F016 ～ SRS_NF018）

### 1. 功能需求全景（SRS_F016～F030待推进）

| 需求编号 | 需求名称 | 规则状态 (P/F/NT) | 关联用例步骤 | 待修缺陷 / 攻坚重点 | 目标版本 | 当前状态 |
|---|---|:---:|---|---|:---:|:---:|
| **SRS_F016** | 步骤设备匹配与任务接受 | **P:8 F:0 NT:0（V1.160当前实测）** | TC-051～TC-053，5步骤全P | 100真并行双方200/恰一执行/冲突备用完成、103冻结/终止/超时归属全通过关闭；099/101/102当前保持关闭，全部历史失败保留。 | V1.160 | **REQUIREMENT_PASSED；已合main c1844a9，下一F017另启动** |
| **SRS_F017** | 业务指令下发与状态流转 | **V1.162 已修 DEF-S3-104 待复测** | TC-054～TC-056 | DEF-S3-104 构造函数 @Autowired 修复完成，Spring 容器装配与实际打包 JAR 启动验证通过；全量 372 通过 / 2 跳过；交付 GPT 独立复测。 | V1.162 | **READY_FOR_GPT；代码 b262373 / 标签 V1.162，未合 main** |
| **SRS_F018** | 任务异常识别与单次重规划 | P:0 F:2 NT:8 | TC-058.S2, TC-059 | DEF-S3-064（异常列表原因码/历史归档）已在 main（`107da41`）、DEF-S3-066 已在 `06448d6`，勿重修；其余为 NOT_RUN 规则，等 GPT 测试结果。 | V1.145 | 待启动（修复已在 main，待复测） |
| **SRS_F019** | 局部重规划与上下文继承 | P:0 F:0 NT:9 | TC-060, TC-062 | 台账无缺陷记录，也无修复提交；9 条规则全部 NOT_RUN，等 GPT 测到失败项再修，不做推测性改动。 | V1.146 | 待启动 |
| **SRS_F020** | 任务检索与全生命周期追踪 | P:3 F:4 NT:2 | TC-063～TC-065 | DEF-S3-006, 060, 062（移植暂存 `4ec6695` + `64d1f8e`：关键字检索、待人工高亮、失败原因必填、详情 404 回退；DEF-S3-066 已在 main，勿重修）。 | V1.147 | 待启动 |
| **SRS_F021** | 人工终止与安全制动 | P:7 F:1 NT:0 | TC-067.S1 | DEF-S3-059（移植暂存 `4ec6695`：终止操作记录带原因、前状态和每台设备的取消结果与 cancelCommandId）。 | V1.148 | 待启动 |
| **SRS_F022** | 任务定义与约束管理 | P:3 F:1 NT:4 | TC-068, TC-069 | DEF-S3-030（移植暂存 `4ec6695`：约束描述必填校验）。 | V1.149 | 待启动 |
| **SRS_F023** | 协同态势与多维大屏监控 | P:7 F:1 NT:2 | TC-070.S1, TC-071 | DEF-S3-047、048（移植暂存 `efe0790`：离线原因码与任务影响、标记层级）。 | V1.150 | 待启动 |
| **SRS_F024** | 形式化目标歧义消除（超规行李） | P:2 F:2 NT:5 | TC-072, TC-073 | DEF-S3-003, DEF-S3-032（移植暂存：`RequiredInfoGuard` 超规行李必需字段把关）。 | V1.151 | 待启动 |
| **SRS_F025** | 特殊旅客场景参数完整性 | P:0 F:1 NT:8 | TC-074, TC-075 | DEF-S3-004（移植暂存：特殊旅客服务参数完整性，拒绝身份隐私套取）。 | V1.152 | 待启动 |
| **SRS_F026** | 航班变动应急协同响应 | P:0 F:1 NT:9 | TC-076, TC-077 | DEF-S3-005（移植暂存：航班变动信息系统级校验，禁止追问设备路由内部字段）。 | V1.153 | 待启动 |
| **SRS_F027** | 任务全流程追溯与因果复盘 | P:4 F:2 NT:2 | TC-078, TC-079 | DEF-S3-008、057（移植暂存 `6f7f389` 追溯页步骤明细、`c9a7d5f` 事件原因码）。 | V1.154 | 待启动 |
| **SRS_F028** | 安全审计与管理日志留痕 | P:7 F:1 NT:0 | TC-080, TC-081 | DEF-S3-009（移植暂存 `01afe2d`：用户管理关键操作 before/after 审计留痕，杜绝密码泄密）。 | V1.155 | 待启动 |

### 2. 非功能需求全景（18 项待推进）

| 需求编号 | 需求名称 | 现状 | 核心指标与验收关注点 | 目标版本 | 当前状态 |
|---|---|:---:|---|:---:|:---:|
| **SRS_NF001** | 系统安全性（认证与权限） | NT (DEF-S3-010) | TC-086.S1 越权访问防范与会话劫持保护 | 后续安排 | 待启动 |
| **SRS_NF002** | 密码与传输安全 | **P (已验证)** | 密码强哈希存储、敏感字段脱敏传输 | 历史通过 |  PASSED |
| **SRS_NF003** | 旅客个人身份隐私保护 | F (DEF-S3-032) | 模型交互与日志中严禁出现旅客真实姓名/证件号（脱敏门禁闭环） | 后续安排 | 待启动 |
| **SRS_NF004** | 跨域与接口防护 | NT | API 速率限制、防 SQL 注入与 XSS 防护 | 后续安排 | 待启动 |
| **SRS_NF005** | 故障隔离与恢复 | NT | 数据库断连/恢复时系统自愈，不产生脏数据 | 后续安排 | 待启动 |
| **SRS_NF006** | 规划响应时间 | NT | 形式化目标规划在 60 秒内产出或安全超时降级 | 后续安排 | 待启动 |
| **SRS_NF007** | 指令下发延迟 | NT | 指令生成至网关下发时延 < 500ms | 后续安排 | 待启动 |
| **SRS_NF008** | 并发任务处理能力 | NT | 支持 50+ 并发协同任务规划与监控 | 后续安排 | 待启动 |
| **SRS_NF009** | 设备状态吞吐率 | NT | 心跳与状态上报高并发吞吐无堆积 | 后续安排 | 待启动 |
| **SRS_NF010** | 数据库高可用与连接池 | NT (NT-S3-011) | 连接池耗尽优雅排队与告警 | 后续安排 | 待启动 |
| **SRS_NF011** | 告警推送及时率 | NT | 严重告警 1 秒内推送到前端 | 后续安排 | 待启动 |
| **SRS_NF012** | 用户体验与前端交互 | **P (已验证)** | 响应式设计与直观状态呈现 | 历史通过 |  PASSED |
| **SRS_NF013** | 接口标准化与 OpenApi | **P (已验证)** | RESTful API 规范与 Swagger/OpenAPI 完备性 | 历史通过 |  PASSED |
| **SRS_NF014** | 模块化与可维护性 | **P (已验证)** | 分层解耦、服务化边界清晰 | 历史通过 |  PASSED |
| **SRS_NF015** | 系统可用性 SLA (99.9%) | NT | 无单点故障，异常自愈与健康探针 | 后续安排 | 待启动 |
| **SRS_NF016** | 审计日志完整性与防篡改 | NT | 关键业务日志全覆盖、防截断 | 后续安排 | 待启动 |
| **SRS_NF017** | 降级机制完备性 | **P (已验证)** | 模型失效时 100% 成功降级至基线模板或转人工 | 历史通过 |  PASSED |
| **SRS_NF018** | 监控可观测性 (Prometheus) | NT (NT-S3-025) | 指标采集、JVM 与业务指标监控暴露 | 后续安排 | 待启动 |

---

## 四、持续更新机制与协同工作流

为确保后续每一个独立会话均能准确继承本底账并持续演进，执行以下闭环协议：

### 1. Claude 修复轮职责
- **开工准备**：新建独立工作区（`..\tip-claude-f0XX`），检出最新 `origin/main`；先读 `AGENTS.md`、`docs/HANDOFF.md`、`docs/BASELINE_CHANGES.md` 以及本文件 `docs/ROADMAP.md`。
- **改动实现与验证**：编写产品修复代码与修复单测，运行 `mvn -o test` 确认通过。
- **更新本文件**：将当前需求状态更新为 `Claude 修复完成待复测`，更新产品提交 SHA 与对应版本标签。
- **提交与交接**：先提交产品代码并打上唯一递增标签 `V1.N`；再提交更新后的 `docs/HANDOFF.md` 与 `docs/ROADMAP.md`；推送到远端并将状态交接为 `READY_FOR_GPT`。

### 2. ChatGPT 复测验收轮职责
- **独立复测**：按V2.4在独立工作区完成当前需求全部适用项及必要影响回归；发现F后继续其他可执行项，只有真实依赖阻断才逐项NT，整轮汇总后统一交修，形成P/F/NT及原始证据。
- **合并与标记通过**：复测通过后，将成果分支并入 `main` 并推送到远端；更新 `docs/ROADMAP.md` 将该需求标为 ` PASSED`，将下一个需求标为 `⏳ 待启动`。

### 3. 用户在新对话中启动下一需求的标准指令模板

用户在 Antigravity 中新建对话时，可直接复制以下模板（只需替换需求编号与名称）：

```markdown
# 启动需求修复：SRS_F0XX [需求名称]（Claude 修复轮）

请严格遵守 AGENTS.md 与 docs/ROADMAP.md 全景规划：
1. 开工基准：先执行 git fetch origin，严格从最新 origin/main 分支检出独立工作区（如 tip-claude-f0xx，严禁触碰主工作区 tip 或 GPT 端口资源）。
2. 文档与暂存对齐：读取 AGENTS.md、docs/HANDOFF.md、docs/BASELINE_CHANGES.md 和 docs/ROADMAP.md：
   - 检查 docs/ROADMAP.md 第二节【暂存待移植代码清单】中涉及本需求的暂存提交（来自 origin/ai/claude-staging）；
   - 【防冲突防覆盖关键准则】：
     a. 若使用 git cherry-pick <哈希> 或手工移植代码，冲突时必须以 main 当前最新代码为准，保留 main 已通过验收的所有行为与单测；严禁用暂存分支旧文件整文件覆盖 main！
     b. 若该项需求在 main 中已有等价实现或已被 main 取代，切勿重复移植；
     c. 移植暂存代码后，提交说明必须写明原暂存提交哈希（例如：ported from ai/claude-staging commit <hash>），并同步把 docs/ROADMAP.md 暂存表该行状态更新为“已移植 (V1.N)”，避免后续会话再次登记同一项；
3. 代码修复与验证：编写/补齐产品代码及修复单测，运行 mvn -o test 确保全量通过。
4. 打包与提交：
   - 运行 mvn -o package -DskipTests 确保生产构建通过；
   - 先提交产品与单测代码，创建下一递增版本标签（如 V1.N）并推送到 origin；
   - 再更新 docs/HANDOFF.md（标为 READY_FOR_GPT）与 docs/ROADMAP.md，提交并推送到 ai/claude-fix 分支。
```

## 2026-11-04 F015 V1.155 GPT整轮独立复测（V2.4）

- 产品`78eb774a0546216deaa42c2fc2a5dc6ee8f661dd`/`V1.155`固定，接收`be72400`并merge=`f7e515d`，GPT产品树无修改。当前全部9规则/6步骤执行完成，无首F提前停测、无NT、无历史业务P替代。
- 规则7P/2F/0NT（R06展示098、R08恢复066为F）；步骤4P/2F/0NT（TC048S2、TC050S1 F）。31真实任务=11成功试运行+20正式提交，242重复241不增语义覆盖；43项GPT定向、package、前端build、实际JAR健康/关键HTTP及真实Edge无头角色UI完成。
- 065两候选穷尽不再重规划关闭，067具体模板只读入口关闭；096/097保持关闭并有当前验证。066任务261在替换设备实际失败前提前EXCEPTION_RECOVERED/异常SUCCESS，最终待人工时未更正；新098两种只读弹窗将API V1.0/V1.1显示VV1.0/VV1.1。
- 全入口、三类硬拒绝、无匹配/停用/再校验拒绝、三维排序及合法对照、执行中模板变更冻结、合法自主重规划全部已取证。夹具错误自行修正；旧失败和诊断保留。自有配置恢复/任务占用释放/五进程与端口清理完成。
- **证据已先推送：`492e59ccb585f90ddad9f7950e63b94bb544e205`**。报告`acceptance/stage3/SRS_F015-V1.155-整轮独立复测与统一交修.md`，台账和原始证据同提交。随后单独提交HANDOFF/ROADMAP/EXECUTION_BASELINE统一交修。
- READY_FOR_CLAUDE，下一轮仅继续F015修066/098并交下一递增标签；main仍`7d772f83f81d0cd589dc2db6fd622a65658810a5`，无合并/PR，F016不推进。后续需求及95项整体验收没有因此通过。

## 2026-11-05 F015 V1.156独立验收通过与main合入（V2.4）

- 规则9P/0F/0NT、步骤6P/0F/0NT，当前需求全部当前实测，无历史业务P替代；29真实任务（10成功试运行+19独立正式观察），43项GPT定向/邻接、package、前端build、实际JAR健康/关键认证HTTP及真实Edge无头UI全通过。066与098关闭；065/067/096/097当前回归保持关闭。
- 实际产品SHA `5effea7e267f5ef724a00a58716c67a59b284272`，标签V1.156不移动；实际交接文档 `ee77957e776b5985393f1263d605905035bdacea`。原消息完整SHA写错、Git对象不存在，已核对实际远端标签/提交并更正当前入口，原声明与核对记录保留。
- 证据先推送 **`9c94dccfbde848483a52ed15f345e4405312101e`**。报告`acceptance/stage3/SRS_F015-V1.156-整轮独立验收与裁决.md`，台账/原始证据与更新前快照同提交。
- main复测期间新增c15be09路线图文档；只合并文档、不改产品，保留新增暂存清单与F016+说明。解决ROADMAP冲突后的 **`949c3b3e110bae95f27833f7ca82b00b716aadfe`** 已推送ai/gpt-test并安全快进main，远端已核对；40个用户未跟踪文件哈希不变。无PR/强推/reset；最终交接随本提交同步main。
- 自有配置已恢复、任务占用释放、5进程/端口清理完成，失败历史保留。**下一项F016从最新origin/main另启动**，仍用V2.4整轮；F016+表中的旧目标版本为历史规划占位，实际交付须取下一唯一递增标签，不能当作已发布待测版本。后续需求/三核心场景/95项没有因此通过。

## 2026-11-05 F016 V1.157整轮独立复测与统一交修

- 当前全部适用项已执行：规则3P/5F/0NT，步骤1P/4F/0NT；新增DEF099～102，未改需求/用例口径。R03/R06末拒留痕回滚判F，首拒切换P不能替代完整覆盖。
- 25有效真实任务记录归并23独立观察组，11探针诊断/被更正任务另列；352后端报告350执行通过/2跳过、独立离线时序服务1P，生产构建/JAR/认证HTTP/Edge2页完成。当前F016无历史业务P替代。四缺陷及所有反例/合法对照详见stage3报告和台账。
- **证据先推送：2ab13da65e530c7906dd277c65c3b368dee59eb4**，最小F检查点4f8a44c；报告`acceptance/stage3/SRS_F016-V1.157-整轮独立复测与统一交修.md`。失败历史及探针更正保留，所有自有配置/端口/分配已清理。
- READY_FOR_CLAUDE：下一轮仍F016修099全拒绝迁移/持久化、100接受互斥、101安全取消/释放、102响应时间展示，交下一唯一递增标签；main仍9816886，无合并/PR，不推进F017或宣称95项通过。详见HANDOFF最新一节。

## 2026-11-05 F016 V1.158 Claude修复完成待GPT复测

- 产品与单测提交：`4f0b4d8e0ab2a2f0e4027d3ee21b20fe487dcadc`，版本标签 `V1.158`（严格指向该产品代码提交，已推送至 origin）。
- 缺陷修复闭环：
  1. DEF-S3-099：新增 Flyway 迁移 `V28__allow_assignment_failed_exception_type.sql` 放宽 `chk_exception_type` 允许 `ASSIGNMENT_FAILED`，同步前端异常枚举，彻底解决全拒绝入库 500 事务回滚问题；
  2. DEF-S3-100：在 `TaskExecutionOrchestrator.onTaskResponse` 增加待承接窗口期互斥检测，对已处于 BUSY 或其他任务占用的代理触发 `AGENT_ASSIGNMENT_CONFLICTED` 并自动顺位切换下一候选设备，防止并发多任务重复下发执行；
  3. DEF-S3-101：落实 `BL-006` 基线变更，离线设备取消时写入 `DELIVERY_FAILED` 状态的 `TASK_CANCEL` 指令记录，待设备恢复在线上报 IDLE 时匹配该指令并跃迁至 `CONFIRMED_IDLE` 解除占用；待承接未开始执行的步骤终止时立即释放设备，避免误锁为 BUSY；
  4. DEF-S3-102：新增 Flyway 迁移 `V29__step_assignment_acceptance_timing.sql` 与实体字段，记录 `acceptanceRequestedAt`、`acceptedAt` 及 `acceptanceDurationMs`，TaskDetailView 增加“承接响应时间”列与毫秒格式化展示，通过 Edge UI 正则断言。
- 验证情况：后端 354 项单测全量通过（0 failures, 0 errors, 2 skipped）；前端 Vite 构建通过；生产 JAR `mvn -o package -DskipTests` 构建成功。
- 交接状态：更新为 `READY_FOR_GPT`，交由 ChatGPT 独立复测。


## 2026-11-05 F016 V1.158整轮独立复测与统一交修

- V2.4+BL006整轮当前实测，规则6P/2F/0NT，步骤3P/2F/0NT；无历史业务P替代。099约束迁移/末拒持久化、101新口径取消确认（原F保留）、102真实UI响应时间一致均关闭；100真正并行竞态仍F，新增103跨任务终止误释放。
- 32真实任务=30正式+2试运行，归并28观察组26P/2F；354后端报告352执行通过/2跳过、独立精确离线服务1P，package/前端build/实际JAR/迁移/认证HTTP及Edge5页通过。341一次合法5.5.3重规划旧探针断言已更正，模板准备与UI选择器错误自行修正并保留诊断。
- **证据已先推送 9a01b3f4dd1b1285364f4e245dd516a5d668da0b**；最小F检查点93f99bf。报告`acceptance/stage3/SRS_F016-V1.158-整轮独立复测与统一交修.md`。BL006正文及本轮首次GPT裁决已同步stage0/BASELINE，未追溯修改V1.157失败。
- 资源清理完成，活跃分配0，341旧失败计划的历史行保留；main仍9816886、无合并/PR。下一轮仍F016修100/103，保留其余关闭行为，交新标签再整轮复测；F017和95项均未因此通过。

## 2026-11-05 F016 V1.159 Claude修复完成待GPT复测

- 产品与单测提交：`a893e944b868e666ab165eb7e6ea40f1ccadaa7d`，版本标签 `V1.159`（严格指向该产品代码提交，已推送至 origin）。
- 缺陷修复闭环：
  1. DEF-S3-100（真正并发抢占竞态双下发）：在 `DeviceAgentMapper` 增加 `findByIdForUpdate` / `findByAgentCodeForUpdate`（`SELECT ... FOR UPDATE` 行级悲观锁）与 `claimAgent` 原子更新（`WHERE work_status = 'IDLE' AND (current_task_id IS NULL OR current_task_id = #{taskId})`）。在 `TaskExecutionOrchestrator.onTaskResponse` 接受分支，在行锁内重读代理最新提交态；任一竞争失败均触发 `AGENT_ASSIGNMENT_CONFLICTED`（原因码 `ERR_AGENT_ALREADY_BUSY`），将代理加入 `rejectedAgentIds`，清理步骤关联并顺位切换下一候选设备，绝不下发业务执行指令；
  2. DEF-S3-103（跨任务人工终止误清其他执行任务占用）：在 `TaskService.terminate` 中获取并锁定受影响代理行时增加所有权归属校验：若 `agent.getCurrentTaskId() != null && !taskId.equals(agent.getCurrentTaskId())`，严格跳过（不向该代理发送当前任务的取消指令，严禁清空归属于其他任务的工作状态与占用引用）；同步增强 `TaskExecutionOrchestrator.releaseAgent(agentId, expectedTaskId)` 与 `StepTimeoutMonitorTask` 的所有权保护；
  3. 保留 V1.158 中已关闭的 DEF-S3-099（全拒绝迁移/持久化）、DEF-S3-101（BL-006 新口径下安全取消确认释放）及 DEF-S3-102（承接响应时间毫秒展示与追溯筛选）。
- 验证情况：后端全量 356 项单测通过（0 failures, 0 errors, 2 skipped）；生产 JAR `mvn -o package -DskipTests` 构建成功。
- 交接状态：更新为 `READY_FOR_GPT`，交由 ChatGPT 独立复测。

## 2026-11-05 F016 V1.159整轮独立复测与统一交修

- 当前全部适用项执行完成，规则5P/3F/0NT、步骤3P/2F/0NT，无历史业务P替代。100互斥安全改善但378并行回调死锁500、无冲突事件，完整组F；103原终止/超时保护P，但冻结未来关联仍跨任务清占用，残留F。099/101/102本轮保持关闭，旧F保留。
- 34任务=32正式+2成功试运行，归并29观察组27P/2F；356后端报告354执行通过/2跳过、独立服务3P，生产构建/JAR/认证HTTP/Edge5页完成。原安全-only并发P不足已保留并有说明更正，稳定探针加入回调/事件完整断言。
- **完整证据已先推送482cff015fb2bb6ea19645f350fcc72540dbea17**；检查点8d2585e/10a13b9。报告`acceptance/stage3/SRS_F016-V1.159-整轮独立复测与统一交修.md`；无新增规则/基线变更或缺陷编号。
- 自有资源清理、活跃分配0，历史失败行保留，主工作区40用户文件哈希不变；main仍9816886，无合并/PR。下一轮仍F016修100死锁/回调收口与103冻结归属，保留已通过路径，交新标签后再整轮。F017及95项没有因此通过。

## 2026-11-05 F016 V1.160 Claude修复完成待GPT复测

- 产品与单测提交：`8c8a1c09c1776d95cde8bef002b0f0723de0801e`，版本标签 `V1.160`（严格指向该产品代码提交，已推送至 origin）。
- 缺陷修复闭环：
  1. DEF-S3-100（并发回调外键锁升级死锁彻底消除）：分析表明，`TASK_RESPONSE` 回调时先调用 `record(...)` 插入 `device_command_reports` 会隐式获取 `device_agents` 外键 `FOR KEY SHARE` 共享锁，随后在 `onTaskResponse` 升级获取 `device_agents FOR UPDATE` 排他锁；两并发回调各自持有共享锁互相等待排他锁即产生 Postgres 死锁（500/`DeadlockLoserDataAccessException`）。在 `DeviceAgentReportService.accept` 中，在 `record` 插入前先行调用 `deviceAgentMapper.findByAgentCodeForUpdate(agentCode)`，以一致顺序前置排他行锁，彻底消除共享锁升级死锁环路；竞争方在排他锁内顺畅读取最新 `BUSY` 态，平稳触发 `handleAssignmentConflict`、记录 `AGENT_ASSIGNMENT_CONFLICTED`（原因码 `ERR_AGENT_ALREADY_BUSY`）、自动切换下一候选设备并返回 HTTP 200，保证双回调均 200 且冲突收口。
  2. DEF-S3-103（步骤冻结跨任务所有权保护彻底闭环）：在 `TaskExceptionService.freezeRemainingSteps` 中，将历史单参调用 `taskExecutionOrchestrator.releaseAgent(a.getDeviceAgentId())` 修复为携带本任务 ID 的 `taskExecutionOrchestrator.releaseAgent(a.getDeviceAgentId(), taskId)`；并在 `TaskExecutionOrchestrator.releaseAgent` 中增加兜底防线，即使未传 `expectedTaskId`，若代理当前所属任务处于 `EXECUTING` 活跃状态亦拒绝清空其占用，彻底杜绝冻结未执行步骤误释放其他任务设备。
  3. 保持 DEF-S3-099、DEF-S3-101、DEF-S3-102 全部通过路径完好有效。
- 验证情况：全量 360 项单测通过（0 failures, 0 errors, 2 skipped）；生产 JAR `mvn -o package -DskipTests` BUILD SUCCESS。
- 交接状态：更新为 `READY_FOR_GPT`，交由 ChatGPT 依据 V2.4 执行整轮独立复测。


## 2026-11-05 F016 V1.160整轮独立验收通过

- 8规则8P/0F/0NT，5步骤5P/0F/0NT，全部当前实测、历史业务P复用0。100真并行完整闭环及备用切换、103冻结/终止/超时归属原反例与合法对照通过，099/101/102保持关闭；36任务归并30独立观察全P。
- 后端360报告358执行通过/2跳过，独立服务3P、生产构建/JAR/HTTP/Edge5页通过；环境409仅软归档自有退役夹具解决，原失败/计划证据保留。所有自有资源已清理，主工作区40用户文件哈希不变。
- **证据先推送af6d1a42fd24c7c68f2ac53934047cd96927d008**；报告`acceptance/stage3/SRS_F016-V1.160-整轮独立验收与裁决.md`。REQUIREMENT_PASSED，main安全快进与远端核对随后记录实际SHA，不提前宣称已推送；下一F017另启动，不代表95项通过。

### V1.160最终main实推核对

已安全快进main并推送`c1844a9b191d711900f80701d1b4793c3598b0e0`，远端实际核对一致；无PR/强推/reset，主工作区40用户文件哈希不变。最终交接文档随本提交再次同步main；产品V1.160标签保持8c8a1c09c1776d95cde8bef002b0f0723de0801e。F001～F016完成，下一F017另启动，后续需求/三核心场景/95项未因此通过。

## 2026-11-05 F017 V1.161独立复测收口

生产JAR启动闸门F/DEF-S3-104，数据库/Flyway正常，StepTimeoutMonitorTask双public构造函数无指定生产注入入口；当前10规则/6步骤均因该依赖逐项NT。所有可独立执行组件与构建已完成，36有效组件P、1启动F；初始Spring夹具错误修正后独立复现，旧错误日志保留。证据先推送`930f64b20c8ef197fed79c94c669d9805bfa8d00`，报告`acceptance/stage3/SRS_F017-V1.161-整轮独立复测与启动阻断裁决.md`。Claude接收后修104，实际JAR健康/业务冒烟再发新标签，F017下一轮仍完整复测。main保持75c3bf97ea8df90d462b99035de3a8e4dd2587d5，未合并/无PR，不推进F018。

## 2026-11-05 F017 V1.162 修复完成（READY_FOR_GPT）

彻底修复 DEF-S3-104：`StepTimeoutMonitorTask` 显式标注 `@Autowired` 构造函数，`PlanVersionMapper` 与 `DeviceCommandMapper` 采用 `@Nullable` 参数注入，所有成员字段设为 `private final`；新增 `StepTimeoutMonitorTaskSpringInstantiationTest` 覆盖 Spring 容器自动装配防退化。后端全量单测 372 通过 / 2 原有跳过，生产 JAR 实际启动验证通过（Tomcat 在 18199 成功启动，Spring 上下文就绪，无实例化异常）。产品代码 commit `b2623730a0c85622091e6e18bcb1207e23ecdd42` 打标签 `V1.162`，交由 GPT 按 V2.4 规范开展整轮独立复测。main 保持 `75c3bf97ea8df90d462b99035de3a8e4dd2587d5`，未合并，无 PR。
