# Claude ↔ ChatGPT 工作交接

## 当前交接状态

- 状态：`READY_FOR_GPT`
- 当前需求：`SRS_F001 用户登录与预置角色权限`，按功能需求顺序从第 1 项开始。
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
