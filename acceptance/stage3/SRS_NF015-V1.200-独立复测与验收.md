# SRS_NF015 V1.200 独立复测与验收

日期：2026-11-13（Asia/Shanghai）

固定产品标签：`V1.200`，产品代码提交 `fbffe1cf9d4b457f02d3a3f76929427d7a33e290`；测试分支 `ai/gpt-test`，复测合并 HEAD `6ef7f65ba3a69ebf9d6bbb580cc1a96756e960ff`。

隔离资源：PostgreSQL `127.0.0.1:55432/nf015_v197` schema `tip_nf015_v197_20261112`，Redis `127.0.0.1:56379/0`，后端 `127.0.0.1:8180`，模型桩 `127.0.0.1:18117`，仿真终端 `18132/18137/18138`。夹具盘点：3 个任务定义、3 台设备、3 个在线代理、12 项测试并启用能力、2 个真实 dry-run SUCCESS 且 ENABLED 基线模板。

## 当前裁决

- `SRS_NF015.R01 = 0P / 0F / 1NT`（TC-047.S2 三维排序证据尚缺，按门槛不得裁决整项通过）。
- `TC-047.S1 = 当前版本实测通过`：高风险、规划失败/畸形响应、模型 HTTP 503、模型连接失败、模型超时、监督服务不可用均分别执行。
- `TC-047.S2 = NT`：本轮确认了任务族精确匹配、三步限制、最近成功 dry-run 依据，但未建立三个独立候选并完成三维比较，不能把局部观察写成 P。
- `TC-056.S1/S2 = 当前版本关联断言通过`：异常场景无未经校验指令；合法基线命令经过校验后执行。
- 恢复验证 = P：模型/监督恢复后提交正常任务完成，代理回到 `ONLINE/IDLE`，平台 API 可访问。

## 关键业务证据

任务 33（模型 HTTP 503）HTTP 200，持久化后记录 `GOAL_UNDERSTANDING_FAILED`、`BASELINE_DOWNGRADED`，最终 `COMPLETED`；事件包含原始失败原因、模板 `NF015合成特殊旅客基线-20261113103122522`、V1.0、任务族/步骤数/最近 dry-run 选择依据。任务 34（连接失败）和任务 36（超时）同样 HTTP 200、持久化并完成已校验基线；对应 `GOAL_UNDERSTANDING_FAILURE` 操作审计包含任务编号、原目标、原因和 `DOWNGRADE_AFTER_GOAL_UNDERSTANDING_FAILURE`。任务 37（监督不可用）HTTP 200，状态 `PENDING_MANUAL`，记录 `ERR_SUPERVISION_UNAVAILABLE` 与 `TASK_PENDING_MANUAL`，没有步骤分派或设备命令。任务 38/39 为恢复及正常冒烟，最终 `COMPLETED`。

异常场景未发现未经校验的 `plan_versions`、`task_step_assignments` 或 `device_commands`；基线场景的计划、分派和设备命令均来自已启用且真实 dry-run 通过模板。模型日志、请求响应摘要和逐任务事件证据见 `acceptance/stage3/evidence/SRS_NF015-V1.200-*.json` 及 `SRS_NF015-V1.200-round-summary.json`。

历史 V1.197 的 HTTP 503/连接失败 F 保留，不追溯改写；本报告仅记录 V1.200 当前实测。
