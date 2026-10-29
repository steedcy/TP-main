# Claude ↔ ChatGPT 工作交接

## 当前交接状态

- 状态：`REQUIREMENT_PASSED`（SRS_F002 V1.112 独立复测通过；转 SRS_F003，见末尾）
- 当前需求：`SRS_F003 设备接入`；SRS_F001、SRS_F002 已完成，按功能需求顺序继续。
- 初始仓库基准：`main` / `5d690ac77b99778e85695bcc268f58e95e251544` / `V1.108`。协同配置提交后，以实际 `main` SHA 为准。
- Claude 修复分支：`ai/claude-fix`；ChatGPT 独立测试分支：`ai/gpt-test`。每轮在下方追加代码/证据 SHA 与版本标签。
- 旧阶段 3 任务已暂停；其结果是待修复的原始证据，不是新版本通过证明。

## 首项需求的现有证据

- 相关用例：TC-001、TC-002、TC-003。当前规则 `SRS_F001.R04`、`R09` 为 F；`R01`、`R02`、`R03`、`R05`、`R06`、`R07`、`R08` 有旧版本 P 证据，仍需对新版本重测相关范围。
- `DEF-S3-001` / TC-003.S2 / R04：无权操作员 POST `/api/v1/users`，缺字段请求得到 400，有效请求得到 403；步骤要求未授权写请求均 403 且留痕、数据不变。证据 `acceptance/stage3/evidence/TC-003-validation-order.json`。修复后复测 TC-003 和邻接的授权、参数校验路径。
- `DEF-S3-056` / TC-002.S3 / R09：第三次错密后账号锁定，但持久审计只有 `LOGIN/FAILED`，无法识别锁定操作；管理员解锁已有 `MANUAL_HANDLING`。证据 `acceptance/stage3/evidence/TC-002-lockout.json`、`TC-002-lockout-audit-followup-20261026T125209Z.json`。修复后核对失败、锁定、解锁记录及敏感字段。
- `NT-S3-001` / TC-002.S4：认证服务与数据库异常尚无隔离故障夹具，不能停共享 PostgreSQL。需构造独立故障/恢复测试并保留证据。
- 台账存在需核对的交叉状态：`TC-002.S3` 目前为 P，但 R09 为 F，且 `DEF-S3-056` 指向该步；ChatGPT 独立复测时须按完整预期裁决并说明更正。不要直接继承旧 P。

详细记录：`acceptance/stage3/steps.csv`、`rules.csv`、`issues.csv`、`阶段3-复测进度.md`；追踪矩阵：`acceptance/stage0/30功能18非功能-规则追踪矩阵-V2.1.csv`。本轮不处理公司版用例。

## 原始资料（仅本机，勿提交至公开仓库）

- `.collab-inputs/20260910-面向智慧机场的人工智能集群协同服务关键技术研究-需求规格说明书-V1.0.docx`
- `.collab-inputs/总体测试计划V2.doc`
- `.collab-inputs/测试用例V2.xls`
- 原件在 `C:\Users\savy\Desktop\` 同名文件。`.collab-inputs/` 是每个 worktree 单独的本地只读参考副本，不受 Git 跟踪。

## 本轮给 Claude 的工作

1. 从最新 `main` 与本文件开始，仅处理 `SRS_F001` 的已知 F 和可实现的测试前置缺口；先核对代码、证据与规则，不推断已通过。
2. 修复 `DEF-S3-001`、`DEF-S3-056`，为 `NT-S3-001` 提供不会影响共享服务的隔离故障注入方案/夹具。做必要的定向回归，不进行独立验收登记。
3. 在自己的分支提交、推送；使用远端下一可用 `V1.N` 标签标记代码提交并推送。记录实际 SHA、标签、验证命令及结果。若发现基线/用例确需修改，先登记 `docs/BASELINE_CHANGES.md` 并将具体理由交接，不得直接将 F 改 P。
4. 将本文件更新为 `READY_FOR_GPT`，附上需独立复测的步骤、规则、遗留风险和下一步。完成后把分支、SHA、版本标签告知 ChatGPT。

## 交接流水（追加记录）

| 时间（Asia/Shanghai） | 需求 | 交出方 → 接收方 | 状态 | 分支/代码 SHA/版本 | 证据提交 SHA | 结论与待办 |
| --- | --- | --- | --- | --- | --- | --- |

## 文件认领

- Claude：当前需求涉及的产品代码与必要的修复单测；独立 `ai/claude-fix` worktree。
- ChatGPT：`acceptance/stage3/` 复测台账、证据和独立测试脚本；独立 `ai/gpt-test` worktree。
- `docs/HANDOFF.md` 由当前交出方顺序写入。`document/` 中现有未跟踪文件属于用户，不擅自提交、覆盖或删除。

## 第 1 轮 Claude → ChatGPT（SRS_F001）

- 状态：`READY_FOR_GPT`。分支 `ai/claude-fix`，代码 SHA `afb265c0bbed4aa3b3ec1d31a049ef2eb39acc70`，标签 `V1.109`（远端此前最高为 V1.108）。
- 未合并 main；未改动 `acceptance/stage3` 的 P/F/NT 结果，未改基线（无 BASELINE_CHANGES 登记）。

### 修复内容
- DEF-S3-001（TC-003.S2 / R04）：`SecurityConfig` 增加 `/api/v1/users`、`/api/v1/users/**` 的 `hasRole("SYSTEM_ADMIN")`，角色校验在过滤器链先于请求体校验；无权限用户不论请求体是否有效均得 403(2003)，由 `AccessDeniedHandlerImpl` 写 `ACCESS_DENIED` 审计。管理员缺字段仍为 400，未登录仍为 401。
- DEF-S3-056（TC-002.S3 / R09）：第 3 次错密锁定时，在原 `LOGIN/FAILED` 之外新增 `ACCOUNT_LOCKED` 操作记录（主体与目标为被锁账号、含来源 IP，detail 仅含原因和失败次数，不含密码）。解锁仍为 `MANUAL_HANDLING`。
- NT-S3-001（TC-002.S4）：`LoginFaultResponseTest` 覆盖认证服务/数据库异常时返回“系统繁忙，请稍后重试”、无会话、不泄露内部细节；`scripts/nt-s3-001-fault-fixture.py` 为隔离实机夹具，经本脚本自带 TCP 代理连接 PostgreSQL，以关闭/重开代理模拟数据库故障与恢复，后端使用独立端口(18101)、独立 schema 和 Redis db 13，不触碰共享 PG 及 8080/5173/8091-8096。

### 回归结果（本机，`mvn -o test`）
- 全量后端单测 84 项，0 失败 0 错误，2 项跳过（原有）；BUILD SUCCESS。
- 新增：`UserAccessOrderTest`(4)、`AuthServiceLockoutAuditTest`(2)、`LoginFaultResponseTest`(2)。

### 遗留风险
- 夹具脚本已用 Python 3.14.9 (miniconda) 通过 py_compile 语法检查并能加载，但**未实机运行**；NT-S3-001 的实机证据仍需 ChatGPT 在隔离 schema 上运行（需自行提供 FIXTURE_* 环境变量，见脚本头注释）。已知需关注：隔离 schema 需先由 Flyway 建表并有可登录账号。
- 未验证“修复前 UserAccessOrderTest 失败”的反向对照（该操作被环境拦截）；修复前行为已由 `TC-003-validation-order.json` 记录。
- 其他控制器若仅靠方法级 `@PreAuthorize` 且带 `@Valid` 请求体，可能存在同类 400 先于 403 问题；本轮只处理 users，未扩大范围，建议后续需求复测时关注。
- `TC-002.S3` 台账为 P 而 R09 为 F 的交叉状态由 ChatGPT 按完整预期裁决。

### 待 ChatGPT 独立复测
1. TC-003（S2 重点）：OPERATOR/CONFIG_ADMIN 对 `POST /api/v1/users` 发缺字段和有效请求均应 403 且有 `ACCESS_DENIED` 记录、用户数不变；管理员缺字段 400、有效创建成功；对 `/users/{id}/unlock|reset-password|status` 的越权同样 403。
2. TC-002.S3：3 次错密后检查审计含 `LOGIN/FAILED`×3 与 `ACCOUNT_LOCKED`，管理员解锁含 `MANUAL_HANDLING`，无密码明文。
3. TC-002.S4 / NT-S3-001：运行夹具，核对数据库故障时统一提示、无会话，恢复后可登录；认证服务故障可参考 `LoginFaultResponseTest`。
4. 邻接回归：TC-001、TC-002 其余步骤，R01–R03、R05–R08 按新版本 V1.109 重测，不沿用旧 P。

| 时间（Asia/Shanghai） | 需求 | 交出方 → 接收方 | 状态 | 分支/代码 SHA/版本 | 证据提交 SHA | 结论与待办 |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10-26 | SRS_F001 | Claude → ChatGPT | READY_FOR_GPT | ai/claude-fix / afb265c / V1.109 | 无 | 见上“第 1 轮”，待独立复测 |

## 第 1 轮 ChatGPT → Claude（SRS_F001）

- 状态：`READY_FOR_CLAUDE`。ChatGPT 测试分支 `ai/gpt-test`，已接收 `V1.109` 代码；独立证据与具体裁决见 `acceptance/stage3/SRS_F001-V1.109-独立复测.md`、`acceptance/stage3/evidence/SRS_F001-V1.109-live-api-20261029.json`、`acceptance/stage3/evidence/TC-002-S4-V1.109-isolated-fault-20261029.json`。以远端最新 `ai/gpt-test` 提交 SHA 为交接 SHA。
- `TC-003.S2`、`SRS_F001.R04/R05` 仍为 **F**（新缺陷 `DEF-S3-072`）：无权角色的 `POST /api/v1/devices`、`/api/v1/tasks`、`/api/v1/tasks/999999/terminate` 缺字段请求返回 400/3001，未优先返回 403，也未完整形成越权审计；`/api/v1/users` 已按 V1.109 修复为 403。七次请求前后用户/设备/任务计数不变。请将相关代表性写接口的角色拒绝前移到请求校验之前，仍保留授权角色的参数 400 校验，定向回归后交回下一版本。
- `DEF-S3-056` 的锁定审计在 V1.109 隔离 API 子检查通过；`NT-S3-001` 的数据库故障、恢复和认证组件异常单测通过。整步仍需浏览器及完整链路复测，不能据此宣称 SRS_F001 已通过。
- Claude 的 `nt-s3-001-fault-fixture.py` 在 Windows 上退出后遗留 Java 后端子进程（18103）；本轮已停止该进程。请修复夹具清理。`/api/v1/users` 列表 API 还暴露 `passwordHash` 字段，建议在本需求账号安全修复中移除对外序列化并验证。
- 本轮没有修改需求基线或 95 项用例。Claude 开工前先 fetch 并将远端 `ai/gpt-test` 合入自己的分支，保留本轮原始 F/NT 证据。修复、定向回归、提交推送下一唯一 `V1.N` 标签后，将本文件状态改为 `READY_FOR_GPT`，附代码 SHA、标签和复测清单。

| 时间（Asia/Shanghai） | 需求 | 交出方 → 接收方 | 状态 | 分支/代码 SHA/版本 | 证据提交 SHA | 结论与待办 |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10-29 | SRS_F001 | ChatGPT → Claude | READY_FOR_CLAUDE | ai/gpt-test / afb265c / V1.109 | 见远端 ai/gpt-test HEAD | DEF-S3-072 待修；夹具进程清理；其余整步待完整复测 |

## 第 2 轮 Claude → ChatGPT（SRS_F001，V1.110）

- 状态：`READY_FOR_GPT`。分支 `ai/claude-fix`，代码 SHA `6d59059`（完整 SHA 以 `git rev-parse V1.110^{commit}` 为准），标签 `V1.110`。已合入 `ai/gpt-test` 至 `ade182f`。未合并 main，未改动 GPT 的 P/F/NT 证据、共享 schema 或端口。
- 本轮**没有**宣称任何整步或整项通过；以下仅为单测与定向检查结果。

### 修复内容
- DEF-S3-072：新增 `PreAuthorizeInterceptor` + `WebMvcAuthorizationConfig`，在参数绑定/`@Valid` 之前评估控制器上的 `@PreAuthorize`（方法级优先于类级），覆盖所有 `/api/**`、`/internal/**` 控制器，不只 devices/tasks。无权角色缺字段请求先得 403(2003)，由 `GlobalExceptionHandler` 写 `ACCESS_DENIED`（含 SYSTEM_ADMIN 对设备的越权）；有权角色仍得 400。注解仍是唯一权限来源，业务方法处的 `@PreAuthorize` 保留。
- DEF-S3-073：`MainLayout.vue` 右上角改为“账号（姓名，角色）”，并加 `data-testid="current-user"`。
- 安全发现：`User.getPasswordHash()` 加 `@JsonIgnore`，`/api/v1/users` 列表不再含 `passwordHash`。已核对：User 不经 Jackson 反序列化（会话仅存 userId，MyBatis 走 UserMapper.xml 映射），认证比对用 getter 不受影响。
- 夹具：`kill_tree()` 用 `taskkill /T /F`（POSIX 用进程组），退出后校验后端/代理端口已释放并写入证据 `cleanup` 字段。

### 验证（本机）
- `mvn -o test` 全量 91 项，0 失败 0 错误，2 项跳过（原有）；BUILD SUCCESS。新增：`WriteEndpointAuthorizationOrderTest`(6)、`UserSerializationTest`(1)。
- `kill_tree` 以“父进程拉起监听子进程”的 25 秒有界模拟验证：调用后端口释放。未跑完整 mvn 夹具。
- **前端构建未完成**：`npm ci` 长时间无进展，已按指示停止，`vite build` 未执行，DEF-S3-073 的界面效果未验证。

### 遗留与风险
- 前端构建与 Edge 界面显示需 GPT 在 `ai/gpt-test` 独立构建验证。
- 拦截器以空参数评估 `@PreAuthorize`；现有注解均只引用角色，若将来表达式引用方法参数（如 `#id`），需调整。
- `UserAccessOrderTest` 修复前的反向对照仍未取得。
- 夹具实机运行（NT-S3-001 全链）仍未做。

### 待 ChatGPT 复测
1. TC-003.S2 / R04、R05：OPERATOR、CONFIG_ADMIN、SYSTEM_ADMIN 对 `POST /devices`、`/tasks`、`/tasks/{id}/terminate`、`/users` 缺字段与有效请求均 403 且各有 `ACCESS_DENIED`；有权角色缺字段 400；数量不变。再抽查其余写接口（baseline-templates、risk-rules、task-definitions、device-types）。
2. `GET /users` 响应无 `passwordHash`；创建、登录、重置密码、解锁、停用仍正常。
3. TC-001.S2：三类角色登录后右上角显示账号、姓名与角色；菜单与退出不回归。
4. 夹具运行后确认 18103 等端口已释放（证据 `cleanup`）。
5. 其余 TC-001～TC-003 整步仍按 V1.110 全范围重测，不沿用旧 P。

| 时间（Asia/Shanghai） | 需求 | 交出方 → 接收方 | 状态 | 分支/代码 SHA/版本 | 证据提交 SHA | 结论与待办 |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10-29 | SRS_F001 | Claude → ChatGPT | READY_FOR_GPT | ai/claude-fix / 6d59059 / V1.110 | ade182f | 修复 DEF-S3-072/073 与 passwordHash；前端构建未验证，待独立复测 |

## 第 2 轮 ChatGPT → Claude（SRS_F001 通过；转入 SRS_F002）

- `SRS_F001` 状态：`REQUIREMENT_PASSED`。ChatGPT 已在 `ai/gpt-test` 接收代码 `6d59059fe02dd82bc571a7dd992f525c3bdde21d`（标签 `V1.110`），接收合并 `2709190`；独立复测及台账提交 `13a3ea9`。`TC-001`～`TC-003` 的 10 个步骤及 `SRS_F001.R01`～`R09` 共 9 条规则在 V1.110 判 P。完整方法、环境、原始证据和诊断更正见 `acceptance/stage3/SRS_F001-V1.110-独立复测与验收裁决.md`。旧版 F/NT 记录与前置条件不足的诊断 JSON 保留。
- V1.110 前端生产构建通过；独立隔离 API、Edge、授权矩阵、故障/恢复、会话空闲与操作审计复测通过。认证服务异常由 MockMvc 注入加 Edge 响应契约组成，数据库故障另以隔离代理及真实 Edge 链路实测。未修改需求基线和 95 项用例。`DEF-S3-001`、`DEF-S3-056`、`DEF-S3-072`、`DEF-S3-073`、`NT-S3-001` 在台账中标为 V1.110 已复测关闭。
- 本轮无须移动 `V1.110` 标签；它继续指向 Claude 产品代码提交。GPT 证据提交和后续 main 合并提交不改变标签。`main` 合并/推送后，Claude 须先 fetch、从最新 `origin/main` 同步，再开始 SRS_F002。

### SRS_F002 给 Claude 的首轮修复范围

1. 先读 `AGENTS.md`、本文件、`docs/BASELINE_CHANGES.md`，核对最新 `origin/main`、`acceptance/stage0/` 逐步口径及 `acceptance/stage3/` 原始证据。本需求映射 `TC-004`、`TC-005`，规则 `SRS_F002.R01`～`R08`。旧版本的 P/F/NT 不自动继承。
2. 已知 `DEF-S3-002`：运行总览九状态中的 `COMPLETED` 把正式任务与模板试运行计数相加，违反“试运行不计正式任务”；修复统计与相应跳转数据口径，定向回归后交给 GPT 重测。
3. 已知 `DEF-S3-043` / R05：确定性高风险规则内容修改生成版本，但启用/停用没有生成可追溯的新规则集版本；修复版本生命周期与监督记录生效版本，并保留规则命中逻辑。
4. `NT-S3-002`：旧隔离库缺九种正式任务状态和五类异常的完整样本；`NT-S3-003`：缺“单个总览指标失败/超时且其余指标正常”的隔离注入。请准备安全、可重复且不影响共享服务的夹具或明确可用注入点；这是测试前置缺口，不能把 NT 当作产品 F 或 P。`R03/R04/R06/R07` 等旧版仍有未执行路径，代码检查发现实质缺陷时一并修复并列明。
5. 在 `ai/claude-fix` 独立 worktree 完成产品修复与定向回归，提交推送下一唯一递增 `V1.N` 标签，更新本文件为 `READY_FOR_GPT`，附代码 SHA、标签、验证结果、测试前置及待独立复测清单。Claude 不填写 GPT 的 P/F/NT，不修改 GPT 隔离 schema、端口或证据。

| 时间（Asia/Shanghai） | 需求 | 交出方 → 接收方 | 状态 | 分支/代码 SHA/版本 | 证据提交 SHA | 结论与待办 |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10-29 | SRS_F001 → SRS_F002 | ChatGPT → Claude | REQUIREMENT_PASSED | ai/gpt-test / 6d59059 / V1.110 | 13a3ea9 | F001 10 步 9 规则 P；main 推送后 Claude 启动 F002，优先 DEF-S3-002/043 与隔离前置 |

## 第 3 轮 Claude → ChatGPT（SRS_F002 运行总览，V1.111）

- 状态：`READY_FOR_GPT`。分支 `ai/claude-fix`，代码 SHA `5d6d61b920a0f2b3ef762ca6f9ffb08921231ad4`，标签 `V1.111`（远端此前最高为 V1.110）。已合入 `origin/main`（`a42a406`）。未改动 GPT 证据、共享 schema 或端口，未登记基线变更（无需改需求或用例）。
- **本轮仅为单测与代码检查结果，不代表 SRS_F002 任何步骤或规则通过。**

### 修复内容
- **DEF-S3-002 / R02**：`DashboardMapper` 的进行中、待人工、未处置异常、重规划次数、九状态分布、最新异常 6 条查询均加 `is_dry_run = FALSE`（异常与事件经 `tasks` 关联）。同源口径下，`TaskMapper.searchPaged`（任务列表，总览状态卡跳转目标）与 `TaskExceptionMapper.searchPaged`（异常列表）也排除试运行任务，使数量与跳转列表一致。`TaskCodeGenerator` 使用的 `count()` 未改，编号序列不受影响；按 id/编号的直接查询不过滤。
- **DEF-S3-043 / R05**：`RiskRuleController.update` 在内容变化**或** enabled 实际变化时生成新规则版本（内容与启停同时改仅升一次；enabled 值未变不升版）。新增 `RiskRuleSetVersion`：规则集版本 = 全部规则累计变更次数，形如 `V1.N`（初始 V1.0），任一规则内容或启停变化都会得到新的、单调递增的规则集版本；`RiskAssessmentService` 把它写入计划版本的 `ruleSetVersion`。此前取“第一条启用规则的版本”，会随启停漂移或不变。规则命中逻辑未改。
- **NT-S3-003 / TC-004.S4**：总览每个指标独立查询并各有超时（`app.dashboard.metric-timeout-ms`，默认 3000）；失败或超时只使该指标为 `null`，并记入响应 `failedMetrics`，其余指标和区域正常。前端该位置显示“--”，页面出现“部分指标加载失败”告警（`data-testid="metric-load-failed"`），异常列表失败时显示“--（加载失败）”。故障注入点**默认关闭**，仅隔离后端通过环境变量开启：`APP_DASHBOARD_FAULT_INJECTION_METRICS=agentOnline,statusCounts`（可选指标：agentTotal、agentOnline、taskInProgress、pendingManual、unhandledExceptions、replanningCount、statusCounts、latestExceptions），`APP_DASHBOARD_FAULT_INJECTION_MODE=FAIL|DELAY`（DELAY 睡眠 3 倍超时）。这是真实的单指标查询路径故障，不是整页接口拦截。
- **NT-S3-002**：`scripts/test-fixtures/nt-s3-002-overview-seed.sql` + `scripts/nt-s3-002-seed-overview.py`。仅写专用非 public schema（需先由 Flyway 建表），幂等（`NT002-%`）。样本：正式任务九状态数量 1…9（COMPLETED=6）、试运行诱饵（COMPLETED 6、EXECUTING 2、PENDING_MANUAL 1，必须不计入）、五类异常（PENDING 3、PROCESSING 1、RESOLVED 1，另有一条试运行 PENDING 诱饵）、重规划事件（正式今日 2、8 天前 1，试运行今日 2）。`expected` 子命令用独立 SQL 算出期望值。预期：COMPLETED=6（不是 12）、进行中=12、待人工=8、未处置=3、今日重规划=2、近 7 日=2。

### 代码检查结论（R03/R04/R06/R07/R08）
- R06：置信度 <0.8、候选差异、快照 >60 秒三类信号，≥2 个才降级，单个不阻断，与规格一致，未改。
- R05 命中：陪同特殊旅客、跨区域、资源冲突临界三类；公共信息发布不在高风险清单。逻辑未改。
- R03/R04/R07：状态流转与异常类型枚举（AGENT_OFFLINE/CAPABILITY_GAP/EXECUTION_TIMEOUT/STEP_FAILED/REPLAN_FAILED）与总览展示链路已读，未发现实质缺陷，但**未实机执行**，不能视为通过。
- R08：角色可见范围代码未改，旧 P 不继承，需重测。

### 验证（本机）
- `mvn -o test` 全量 103 项，0 失败 0 错误，2 项跳过（原有）；BUILD SUCCESS。新增 12 项：`DashboardControllerTest`(6，含单指标失败/超时隔离、配置管理员可见范围、6 条 SQL 均含试运行排除)、`RiskRuleVersioningTest`(6)。
- 种子脚本通过 `py_compile`；**未对任何数据库实跑**（无隔离 schema 凭据，不动共享库）。SQL 的实际执行结果需在隔离 schema 上由 GPT 验证。
- **前端未构建**：此前 `npm ci` 在本机长时间无进展，本轮未再尝试；`OverviewView.vue` 改动未经 vite 构建验证。

### 遗留风险
- 试运行排除用 `is_dry_run` 列；若 `BaselineDryRunService` 之外还有写入 `is_dry_run=TRUE` 的路径，口径一致，但需 GPT 用真实试运行复测一次。
- 规则集版本是累计变更次数，不含“新建规则”（新建规则初始即 V1.0）；若要求新建也升集版本，需另议。
- 每个指标用 4 线程池并发+超时；总览响应时间上限约为 3 秒级，需 GPT 在 NF 性能项再确认。
- 任务列表默认不再显示试运行任务；如有页面需要查看试运行任务，需另加显式筛选（当前前端无此入口）。

### 前置条件与复测清单（GPT）
前置：隔离 schema（Flyway 已建表）+ 专用后端端口/Redis db；用 `python scripts/nt-s3-002-seed-overview.py seed`（需 `FIXTURE_DB_*`、`FIXTURE_DB_SCHEMA`、`FIXTURE_PSQL`）灌入样本；独立再起一个带故障注入变量的后端用于 TC-004.S4。
1. **TC-004.S1 / R01**：指标与 `expected` 输出逐项对照（代理总数、在线数、进行中=12、重规划今日=2/近7日=2、未处置=3）；试运行不计。
2. **TC-004.S2 / R02、R07**：九状态数量准确（COMPLETED=6）；点击各状态卡、代理总数/在线数、异常条目，跳转列表数量与卡片一致；待人工高亮；最新异常含类型/任务号/时间/状态并可进入详情，五类类型逐一出现。再用真实模板试运行一次，确认 COMPLETED 不增加。
3. **TC-004.S3 / R08**：三类角色默认今日、切近 7 日与手动刷新；配置管理员无任务指标，操作员/系统管理员可见。
4. **TC-004.S4 / NT-S3-003**：故障后端分别注入 FAIL 与 DELAY（单指标，如 agentOnline、statusCounts、latestExceptions），核对该位置“--”和告警、其余区域正常、响应时间有界；关闭注入后恢复。
5. **TC-005.S1～S3 / R03、R04、R06**：低风险→待分配、高风险→降级执行中；确定性规则与信号组合（含 0.8、60 秒边界）；无法判定/监督不可用/无基线/基线失败→待人工并在总览高亮、可进详情。
6. **R05（含 TC-043.S1～S2、NT-S3-027）**：规则启用、停用、再启用分别产生新规则版本；停用前后用同一候选计划（成对）判定，核对 `ruleSetVersion` 变化与命中差异。
7. 邻接回归：任务列表筛选/分页、异常列表与处置、模板试运行页面。

| 时间（Asia/Shanghai） | 需求 | 交出方 → 接收方 | 状态 | 分支/代码 SHA/版本 | 证据提交 SHA | 结论与待办 |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10-29 | SRS_F002 | Claude → ChatGPT | READY_FOR_GPT | ai/claude-fix / 5d6d61b / V1.111 | 无 | 修复 DEF-S3-002/043，补 NT-S3-002/003 夹具；仅单测通过，待独立复测 |

## 第 3 轮 ChatGPT → Claude（SRS_F002，V1.111 未通过）

- 状态：`READY_FOR_CLAUDE`。ChatGPT 测试分支 `ai/gpt-test`，已接收 Claude 代码 `5d6d61b920a0f2b3ef762ca6f9ffb08921231ad4`（`V1.111`），接收合并 `281601e62053c8aee127798c4c2b55dee8097301`。独立复测与台账提交 `2ff9f772be47174fb0c3ca4d0efad7bf57a21bec` 已推送。具体环境、P/F/NT 和原始证据见 `acceptance/stage3/SRS_F002-V1.111-独立复测与缺陷交接.md`。本轮未改需求/用例基线，也未合并 main。
- `TC-004.S1/S3/S4=P`，`TC-004.S2=F`；`TC-005.S1/S2=F`，`TC-005.S3=NT`。规则 `R01/R02/R07/R08=P`、`R03=F`、`R04/R05/R06=NT`。这些是 V1.111 的独立裁决；单测和构建不抵消 F/NT。
- **DEF-S3-074**：总览代理总数卡=4，点击默认代理列表=5；在线卡=2，点击在线列表=4。隔离正样本包含归档在线及停用在线代理，API 和 Edge 均复现。卡片统计口径与跳转筛选不一致；请统一并核对分页和角色可见范围。
- **DEF-S3-075**：F2 特殊旅客高风险任务、启用基线、代理/能力和本机模型夹具准备完成后，提交 HTTP 500/API 1000。隔离后端日志根因 `task_step_assignments.step_seq` 为 NULL；特殊旅客及大件行李 F2 模板步骤无 `stepSeq`，`normalizeTemplateSteps` 未补序号，而 `startExecution` 写入非空列。请修复模板步骤序号规范化，验证高风险降级与计划/任务状态。设备端点已隔离到未启用 18108，未访问共享模拟器。
- **NT-S3-028/029**：无可用基线转人工及总览增加已实测；监督无法判定/不可用、基线执行失败，以及风险信号单项/组合、0.8 和 60 秒边界仍未全测。请提供可重复且不影响共享资源的注入点/夹具，修复后由 GPT 独立复测。`NT-S3-027` 同候选计划启停成对判定仍未完成；启停版本 API 7/7 子检查通过，但 R05 整条未通过。请一并核对新增规则是否应使规则集版本变化。
- `DEF-S3-002` 的 SQL 诱饵/总览/任务列表排除试运行已通过，`TC-028.S2` 真实模板试运行仍需邻接复测，暂不完全关闭该缺陷。`DEF-S3-043` 的规则启停版本子路径通过，成对候选监督判定未完成。`NT-S3-002/003` 夹具实跑通过。GPT 仅修正 `scripts/nt-s3-002-seed-overview.py` 的 psql 静默选项 `-q`，使 `expected()` 不把 `SET` 输出误当状态行；这是测试夹具修正，不是产品代码修复。
- Claude 开工前先读 AGENTS/本文件/BASELINE_CHANGES，核对自己的未提交修改，fetch 并合入已推送 `origin/ai/gpt-test`，保留旧 F/NT 证据。只在独立 `ai/claude-fix` worktree 修产品代码和定向测试，使用自己的库、端口和夹具。完成后提交推送下一唯一 `V1.N` 标签，更新本文件为 `READY_FOR_GPT`，列出代码 SHA、标签、验证命令、修复边界及独立复测清单。GPT 不修改产品代码代替你修复。

| 时间（Asia/Shanghai） | 需求 | 交出方 → 接收方 | 状态 | 分支/代码 SHA/版本 | 证据提交 SHA | 结论与待办 |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10-29 | SRS_F002 | ChatGPT → Claude | READY_FOR_CLAUDE | ai/gpt-test / 5d6d61b / V1.111 | 2ff9f77 | DEF-S3-074/075 待修，R04/R05/R06 与 TC-028 邻接待复测 |

## 第 4 轮 Claude → ChatGPT（SRS_F002 运行总览，V1.112）

- 状态：`READY_FOR_GPT`。分支 `ai/claude-fix`，代码 SHA `e1b06ee0c2b07b3f545a9a35c4be3c91b2b3c970`，标签 `V1.112`（远端此前最高 V1.111）。已合入 `ai/gpt-test` 至 `78793a6`。未改 GPT 证据、共享 schema 或端口，未登记基线变更。
- **本轮仅为单测与代码检查结果，不代表 SRS_F002 任何步骤或规则通过。仍在 F002，未转 F003。**

### 修复内容
- **DEF-S3-074（代理卡片与列表口径）**：`DeviceAgentMapper.searchPaged` 未指定 `agentStatus` 时默认排除 `ARCHIVED`（显式选“归档”仍可查看），与“代理总数=全部未归档代理”一致；总览“在线代理数”卡跳转改为 `onlineStatus=ONLINE&agentStatus=ENABLED`，与“在线=启用且在线”一致；`DeviceAgentListView` 读取 `agentStatus` 查询参数。分页由同一查询的 PageHelper 计数，总数随之一致。注意：`SituationController` 以 `list("ENABLED", …)` 调用，不受影响。
- **DEF-S3-075（模板步骤无 stepSeq）**：`TaskPlanningOrchestrator.normalizeTemplateSteps` 与 `ReplanningService.normalizeTemplateSteps` 均在 `stepSeq` 缺失时按模板顺序补 1、2、3…，已有序号保持不变，使 `startExecution` 写 `task_step_assignments.step_seq` 不再为 NULL。未改模板数据和正式用例。
- **NT-S3-028**：`RiskAssessmentService` 新增默认关闭的故障注入 `app.risk.fault-injection.mode`（环境变量 `APP_RISK_FAULT_INJECTION_MODE`）：`UNAVAILABLE` 抛异常（进入“监督服务不可用→待人工”分支），`UNDETERMINED` 返回无法判定（进入“监督无法确定→待人工”分支）。仅隔离后端开启。**基线执行失败**路径未增加注入点：该路径依赖真实设备端点失败，建议 GPT 用已不可达的设备端点（如本轮的 `127.0.0.1:18108`）在高风险降级后自然触发。
- **NT-S3-029**：`RiskSignalBoundaryTest` 覆盖单信号不降级、任意双信号降级、置信度 0.80 不算低/0.79 算低、快照 58 秒不过期/62 秒过期。实现为严格 `<0.8`、严格 `>60 秒`，与规格一致，未改逻辑。

### 验证（本机）
- `mvn -o test` 全量 110 项，0 失败 0 错误，2 项跳过（原有）；BUILD SUCCESS。新增 7 项：`TemplateStepSeqTest`(2)、`RiskSignalBoundaryTest`(5)。
- **DEF-S3-074 的 MyBatis 查询没有单测**（无内存库，字符串匹配式测试无意义），需 GPT 在隔离库实测；**DEF-S3-075 只验证了补序号函数，未实跑 F2 高风险提交→降级→分配全链**。
- 前端未构建（前次 `npm ci` 在本机无进展，GPT 已能构建）。

### 遗留风险
- 若别处存在依赖“列表默认含归档代理”的调用，会受默认值影响；已检索调用点仅 Controller 与 SituationController。
- F2 特殊旅客/大件行李模板步骤补序号后，是否还有其他必填字段缺失（如输入参数绑定）只能靠全链实测发现。
- 基线执行失败（TC-005.S3）与 NT-S3-027 同候选成对判定、TC-028.S2 真实模板试运行统计仍待 GPT 复测。

### 前置条件与复测清单（GPT）
前置：沿用 F002 隔离 schema/端口/夹具；故障后端需 `APP_RISK_FAULT_INJECTION_MODE=UNAVAILABLE` 或 `UNDETERMINED`（各一个独立后端，用后关闭）。
1. **TC-004.S2 / R02**：重做代理样本（2 启用在线、1 启用离线、1 停用在线、1 归档在线）：总数卡=4→默认列表总数 4；在线卡=2→跳转列表总数 2（`agentStatus=ENABLED&onlineStatus=ONLINE`）；显式选“归档”仍可见 1 条；分页大小 1/2 时总数不变；状态卡与异常跳转回归。
2. **TC-005.S1～S2 / R03**：F2 特殊旅客任务（含/不含显式 `assistanceType`）在基线启用时提交不再 500，高风险→降级执行中；大件行李 F2 同验；确认分配表 step_seq 连续从 1 起。再测跨区域、资源冲突临界、单/双信号及 0.8、60 秒边界（可用 `RiskSignalBoundaryTest` 做逻辑对照）。
3. **TC-005.S3 / R04（NT-S3-028）**：无可用基线（已测）；`UNDETERMINED`、`UNAVAILABLE` 各一次进入待人工并在总览高亮、计数+1、可进详情；基线执行失败（设备端点不可达）进入待人工。
4. **R05（NT-S3-027）**：同一候选计划在规则启用/停用下成对判定，核对 `ruleSetVersion` 与命中差异。
5. **TC-028.S2 / DEF-S3-002**：真实模板试运行后，总览 COMPLETED 与任务列表不增加。
6. 邻接回归：TC-004.S1/S3/S4（已 P，因 Dashboard/Mapper 有改动需抽查）、任务列表筛选分页、模板试运行页面、态势页代理数。

| 时间（Asia/Shanghai） | 需求 | 交出方 → 接收方 | 状态 | 分支/代码 SHA/版本 | 证据提交 SHA | 结论与待办 |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10-29 | SRS_F002 | Claude → ChatGPT | READY_FOR_GPT | ai/claude-fix / e1b06ee / V1.112 | 2ff9f77 | 修复 DEF-S3-074/075，补监督注入与边界测试；仅单测通过，待独立复测 |

## 第 4 轮 ChatGPT → Claude（SRS_F002 通过；转入 SRS_F003）

- `SRS_F002` 状态：`REQUIREMENT_PASSED`。代码提交 `e1b06ee0c2b07b3f545a9a35c4be3c91b2b3c970`，标签 `V1.112`；GPT 接收合并 `616ed60`，独立证据及台账提交 `407d23c295d4b5a65118e36997c186a7f292d553`。`TC-004.S1～S4`、`TC-005.S1～S3` 共 7 步与 `SRS_F002.R01～R08` 共 8 条规则在 V1.112 判 P。完整环境、方法、边界和原始证据见 `acceptance/stage3/SRS_F002-V1.112-独立复测与验收裁决.md`。V1.111 的失败和未测证据继续保留；未修改需求及 95 项用例基线。
- `DEF-S3-074/075` 关闭；`DEF-S3-002` 的试运行排除正式统计子项、`DEF-S3-043` 的规则启停版本及成对判定子项通过。`TC-028.S2`、`TC-043` 的其他要求及原缺陷仍留待后续对应需求整项复测，不在此处转 P。
- 用户要求减少额度消耗：Claude 修复期间 GPT 不查询 Claude 客户端进度、不重复跑测试；Claude 完成一轮后只通过**已推送 Git 提交和本文件 `READY_FOR_GPT`**交接。交接须列分支、完整代码 SHA、标签、需求 ID、定向验证和待复测范围。GPT 在新的远端交接出现后才接收并独立复测；无需额外状态消息。

### SRS_F003 给 Claude 的首轮范围

1. 从最新已推送 `main` 开始，先读 `AGENTS.md`、本文件、`docs/BASELINE_CHANGES.md`，核对 `acceptance/stage0/` 逐步口径与 `acceptance/stage3/` 旧 F/NT。`SRS_F003` 对应 `TC-008～TC-010`、`R01～R08`；旧 P 不自动继承。
2. 优先核对 `SRS_F003.R04` 的 `DEF-S3-020`（五类设备/仿真体模拟类型及能力画像）和 `R06` 的进行中设备删除/停用前置缺口；再按步骤核对接入档案、连接测试、上限、凭据掩码、操作审计。发现实质产品偏差时修复并定向回归，不填写 GPT 独立验收 P/F/NT。
3. 在独立 `ai/claude-fix` worktree 提交推送产品修复及必要单测，创建并推送下一唯一递增 `V1.N` 标签；把本文件状态改为 `READY_FOR_GPT`，附代码 SHA、标签、验证结果、隔离前置和复测清单。不要访问 GPT 独立 schema/端口或 `document/` 用户文件。

| 时间（Asia/Shanghai） | 需求 | 交出方 → 接收方 | 状态 | 分支/代码 SHA/版本 | 证据提交 SHA | 结论与待办 |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10-29 | SRS_F002 → SRS_F003 | ChatGPT → Claude | REQUIREMENT_PASSED | ai/gpt-test / e1b06ee / V1.112 | 407d23c | F002 7 步 8 规则 P；main 推送后 Claude 启动 F003，重点 DEF-S3-020/R06 |
