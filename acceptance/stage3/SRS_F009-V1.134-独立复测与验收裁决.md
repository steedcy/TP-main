# SRS_F009 V1.134 独立复测与验收裁决

结论：**SRS_F009 整项 P**，`DEF-S3-086`、`DEF-S3-087` 在 V1.134 的真实设备链路上关闭。执行基线 V2.3。`V1.134` 是注解标签，实际指向产品代码 `82166d93e4ff72b325d7f6565edf1bb498b8d132`；修复方通知及上一节 HANDOFF 所写完整 SHA `82166d93e4ff72b325d7f6565edf1bb498b8d132` 是笔误，短 SHA `82166d9` 正确。Gemini/Claude 交接 `c6069b27fae4baa558d67a8324eac6dd699938b6`。GPT 在 `ai/gpt-test` 快进合入后独立构建，在自有 PostgreSQL schema `tip_gpt_f006_v118_20261030`、后端 18129、机器人仿真体 18132 实测；未修改产品代码、F008 台账、修复方 worktree 或其资源。

## V1.134 当前版实测

| 覆盖 | 观察 | 原始证据 |
| --- | --- | --- |
| DEF-S3-087，现有库迁移 | Flyway V26 在 GPT 既有 schema 中显示 `success=true`；`chk_op_log_result` 从旧版只允许 `SUCCESS/FAILED` 扩展为允许 `CANCELLED`。没有重建 GPT schema。 | `evidence/SRS_F009-V1.134-migration-followup-20261102T113822Z.json`；旧约束见 `evidence/SRS_F009-V1.133-cancel-constraint-20261102T073022Z.json`。 |
| TC-030.S1 / R08，DEF-S3-086/087 | 有效五步模板的任务 61 在第 1 步 `STEP_DISPATCHED` 后由配置管理员取消：HTTP 200，API `CANCELLED`，任务 `MANUAL_TERMINATED`，模板当时为 `DRAFT`；事件含 `TASK_CANCEL_REQUESTED`、`MANUAL_TERMINATED`、`DRY_RUN_CANCELLED/ERR_DRY_RUN_CANCELLED`，无 `DRY_RUN_FAILED`。结果操作日志 `operation_result=CANCELLED`、detail.result=`CANCELLED`，目标含冻结 V1.0、任务 61、`DRY_RUN_CANCELLED`。取消后延迟核对任务未反转、代理 `IDLE/current_task_id=NULL`。**P**。 | `evidence/SRS_F009-V1.134-results-20261102T113719Z.json`；`evidence/SRS_F009-V1.134-migration-followup-20261102T113822Z.json`。 |
| TC-028.S1/S2，R03/R04/R05/R08 成功与启用 | 任务 58 真实承接、执行反馈并完成，`is_dry_run=true`、计划来源 `BASELINE_TEMPLATE/V1.0`，结果事件与日志 `SUCCESS`，模板试运行通过后启用且有 `BASELINE_TEMPLATE_ENABLE/SUCCESS`。正式完成数及总览 `COMPLETED` 均保持 26，含试运行完成数 30→31。**P**。 | 同上。 |
| TC-029.S2，R04/R08 设备失败与超时 | 任务 59 的设备 `FAILED`、任务 60 的设备 `TIMEOUT` 均使试运行 `FAILED`，步骤原因、结果事件和结果操作日志一致，模板回 `DRAFT`。**P**。 | `evidence/SRS_F009-V1.134-results-20261102T113719Z.json`。 |

一次人工取消仍产生两条不同指令号的 `TASK_CANCEL/SENT`，均指向同一任务和步骤。V1.134 下最终只有一次 `MANUAL_TERMINATED` 和一次 `DRY_RUN_CANCELLED`，代理释放，取消后没有补入成功反馈或状态反转；F007 的逐条指令编号要求也保持唯一。需求要求请求设备结束当前业务任务，没有规定仅发一次，故此观察不构成独立 F；后续可优化冗余下发。测试模板已停用，仿真体恢复 `SUCCESS` 与 500 ms 延迟。

## 历史覆盖影响复核与逐项裁决

V1.134 相比 V1.133 的产品变更只有 `V26__allow_cancelled_operation_log_result.sql`；`BaselineDryRunLifecycle`、`BaselineDryRunService`、模板静态校验、能力选择、版本门禁、运动安全守卫、总览查询及页面均未改。V1.133 的成功/失败/超时路径和统计曾独立通过，本轮又以真实机器人复测其受数据库约束直接影响的操作日志与核心冒烟。V1.132（`5b9511a6daeafd9f740dd51a090d83f21a32195d`）的静态无效草稿、缺参/缺设备、能力不匹配的 V1.5 原始分支、六步/运动安全边界、新版必须重新试运行的观察继续引用；其来源和边界见 `SRS_F009-V1.132-独立复测与缺陷交接.md`。页面输入预填、版本、结果/耗时展示仍引 V1.5 原始 UI 证据，当前版 API/任务/事件结果已冒烟；**这些历史 P 不算 V1.134 新执行次数**。V1.132 的取消误记 `FAILED` 和 V1.133 的 HTTP 500 原始 F 证据均保留。

步骤 `TC-028.S1/S2、TC-029.S1/S2、TC-030.S1/S2` 全部 **P**；规则 `SRS_F009.R01–R08` 全部 **P**。`R01/R02/R06` 主要沿用上述历史覆盖及当前版核心冒烟；`R07` 的五步执行中取消当前版重测，运动安全静态拒绝沿用 V1.132。没有调整需求或用例预期，不对 95 项整体验收或 F010 以后需求预先判通过。

按协作约定，本轮证据和交接推送后，将 `ai/gpt-test` 合入并推送 `main`。下一需求另开对话。
