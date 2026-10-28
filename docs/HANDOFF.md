# Claude ↔ ChatGPT 工作交接

## 当前交接状态

- 状态：`READY_FOR_CLAUDE`
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
