# SRS_F009 V1.132 独立复测与缺陷交接

结论：**SRS_F009 未通过，交回修复方**。执行/用例补充基线 V2.3；产品标签 `V1.132` 指向 `5b9511a6daeafd9f740dd51a090d83f21a32195d`。GPT 在独立 `ai/gpt-test`、PostgreSQL schema `tip_gpt_f006_v118_20261030`、后端 18129、机器人仿真体 18132 实测。本轮只新增测试脚本、证据与台账，未修改产品代码、F008 台账或 Claude/Gemini 资源。旧版失败/NT 原始证据保留。

## 当前版独立观察

| 步骤 / 规则 | V1.132 裁决与证据 |
| --- | --- |
| TC-028.S1 / R03 | **P**。新建 V1.0 草稿，输入默认地点，选在线机器人仿真代理；真实承接、执行并完成，计划来源 `BASELINE_TEMPLATE`，任务 `is_dry_run=true`，步骤有独立指令号与反馈，事件可追。当前 API 与数据库见 `evidence/SRS_F009-V1.132-live-20261102T063944Z.json`；页面参数预填、版本、总体/步骤耗时及事件展示引用 V1.5 `TC-028-baseline-dryrun-ui.json`，见下方影响复核。 |
| TC-028.S2 / R04、R05、R08 成功分支 | **P（该步骤）**。任务 47 成功后模板可启用；操作记录依次有创建、试运行发起、`BASELINE_TEMPLATE_DRY_RUN_RESULT/SUCCESS`（含任务 47、V1.0）、启用。正式完成数及总览 `COMPLETED` 均保持 26，含试运行完成数 26→27；完整事件仍保留。`DEF-S3-002` 的 F009 统计子项、`DEF-S3-027` 的成功结果日志子项在本版关闭。证据同上。 |
| TC-029.S1 / R01、R02、R07 前置 | **P**。六步模板 400/4403、运动安全输入 `maxSpeed` 400/4407、缺启用能力 400/4406；未静态通过的预置空步骤草稿试运行 400/4408。缺必填、未选设备、未知代理均 400；拒绝前后任务数不变。匹配能力错误的旧版独立观察经代码路径复核引用，不记当前新增实测。`NT-S3-020` 补证。`evidence/SRS_F009-V1.132-boundaries-20261102T064241Z.json`、`evidence/SRS_F009-V1.132-cancel-20261102T064409Z.json`。 |
| TC-029.S2 / R04、R08 失败分支 | **P**。机器人反馈 `FAILED` 和 `TIMEOUT` 分别使任务 48/49 失败，保存步骤原因与耗时，模板维持草稿，启用 400/4402；两次均有发起和 `BASELINE_TEMPLATE_DRY_RUN_RESULT/FAILED` 操作记录，带任务 ID、版本和结果。证据 `evidence/SRS_F009-V1.132-boundaries-20261102T064241Z.json`。 |
| TC-030.S1 / R07、R08 取消分支 | **F**，新缺陷 `DEF-S3-086`。有效五步模板在第 1 步 `STEP_DISPATCHED` 后由配置管理员取消，设备收到 `TASK_CANCEL`，API 结果 `CANCELLED`、任务 `MANUAL_TERMINATED`，中止事件存在；但同一任务 52 又写入 `DRY_RUN_FAILED` 事件和 `BASELINE_TEMPLATE_DRY_RUN_RESULT/FAILED` 操作记录（detail 的 result 也是 `FAILED`）。操作审计把主动取消记成执行失败，与真实结果冲突。`evidence/SRS_F009-V1.132-cancel-20261102T064409Z.json`、`evidence/SRS_F009-V1.132-cancel-audit-20261102T064535Z.json`。五步/运动安全边界子检查 P；整步因结果语义矛盾为 F。`NT-S3-022` 的边界前置已补证。 |
| TC-030.S2 / R06 | **P**。修改模板 V1.0→V1.1 后回到草稿，直接启用 400/4402；V1.1 重新试运行成功后成为 `DRY_RUN_PASSED`，再启用成功。旧版页面历史观察经影响复核引用。证据 `evidence/SRS_F009-V1.132-boundaries-20261102T064241Z.json`。 |

规则汇总：`R01–R07=P`，`R08=F`。其中 R02 的能力不匹配分支与 TC-028.S1/TC-030.S2 页面展示沿用原 V1.5 证据；其余表列是本版实测。`TC-028.S1/S2、TC-029.S1/S2、TC-030.S2=P`，`TC-030.S1=F`。不据此判 95 项整体验收或 F010 以后需求通过。

## DEF-S3-086 可复现条件与修复要求

使用静态校验通过的五步草稿、每步选择同一在线机器人仿真代理，将设备执行延迟设为 8000 ms；发起试运行，在 `STEP_DISPATCHED` 后调用 `POST /api/v1/baseline-templates/{id}/dry-runs/{taskId}/cancel`。任务 52 的 API 为 `CANCELLED`、数据库状态 `MANUAL_TERMINATED`，但结果事件和操作日志为 `FAILED`。`BaselineDryRunService.cancel` 调用 `BaselineDryRunLifecycle.finish(taskId,false,...)`，当前结束路径把取消与设备失败合并为失败结果。请保留设备失败/超时为 `FAILED`，使人工取消的任务事件与结果操作记录明确记为 `CANCELLED`（含模板冻结版本与任务 ID），并核对不会重复下发不必要的取消命令；复测执行中取消、设备失败、超时、正常成功及启用审计。当前一次取消观察到两条 `TASK_CANCEL/SENT`，作为修复时检查项，不单独据此判缺陷。

## 历史覆盖与影响复核

V1.5 原始 `TC-028-baseline-dryrun-ui.json`、`TC-029-baseline-dryrun-guards.json`、`TC-030-baseline-dryrun-cancel.json`、`TC-028-030-baseline-dryrun-lifecycle.json` 保留原测试版本和 SHA `0d798ceb53bc37498f353b4796f2081b92e2011b`，不写为 V1.132 新实测。`git log` 显示基线模板页面自初始代码后无改动；当前 API 的版本、默认输入、步骤耗时、事件与启用门禁另有实测冒烟，因此页面展示观察继续引用。`BaselineDryRunService` 自 V1.5 有统一业务反馈和独立指令号改动；R03 指令/反馈、R04 失败及 R06 版本门禁已用本版真实设备重新覆盖。`BaselineDryRunLifecycle` 在 `8c513bc` 添加结果操作记录，故 R08 成功、失败、取消三条分支均重新实测。总览 Mapper 的试运行过滤在 F002 后已修复，本版以真实成功任务和总览前后值重新核对 R05。R02 的能力不匹配校验逻辑未被上述提交修改，沿用 V1.5 原始能力不匹配证据并以本版未知代理/未选设备及真实匹配代理冒烟复核；不增加该分支的新执行次数。

## 交接

交出分支 `ai/gpt-test`。修复方先 fetch 并合入本轮证据提交，再在独立 `ai/claude-fix` 与自有 schema/端口修复 `DEF-S3-086`；提交、推送下一唯一 `V1.N` 产品标签和 `READY_FOR_GPT`。本轮没有需求/用例基线内容变更。GPT 仿真体已恢复 `SUCCESS` 与 500 ms 延迟，测试模板已停用；GPT 服务保持原状态。
