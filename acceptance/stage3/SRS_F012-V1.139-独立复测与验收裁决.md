# SRS_F012 V1.139 独立复测与验收裁决

- 日期：2026-11-03（Asia/Shanghai）
- 执行基线：V2.3；产品标签 `V1.139` → `6de0e9e8395cca9c22e3d24e0d36dac3ee7866f5`
- 接收分支：`ai/claude-fix`，交接提交 `447af2334d371a1287120a7c65cf89ee963d4549`；独立测试分支：`ai/gpt-test`
- 裁决：**SRS_F012 通过**。`TC-037.S1/S2`、`TC-038.S1/S2`、`TC-061.S1/S2` 和 `SRS_F012.R01–R10` 均为 P；本轮无产品 F 或 NT。此裁决不提前判定 SRS_F013。

## 环境与方法

GPT 专属 PostgreSQL schema `tip_gpt_f006_v118_20261030`、Redis DB 10、后端 `127.0.0.1:18129`、受控模型 `127.0.0.1:18117`、仿真设备 `127.0.0.1:18132`、前端 `127.0.0.1:15179`。后端从已接收的 V1.139 源码在隔离目录重新打包；前端 `npm run build` 成功，Edge 无头浏览器访问任务详情。模型以虚构目标、虚构身份哨兵和确定性计划覆盖有效、无效及边界类。所有产品请求、任务、计划、分配、事件和设备指令均在 GPT 环境观察；没有改动产品代码。暂时关闭 GPT schema 的 `RULE_RESOURCE_CRITICAL` 以验证实际执行，结束后恢复为启用。

## 结果

| 步骤 / 规则 | V1.139 独立观察 | 证据 |
| --- | --- | --- |
| TC-037.S1；R04 | 任务 98 自主计划五动作全字段、参数来源、候选设备、规划说明、5/5 与剩余 0 在详情页可见，三类校验通过后冻结。任务 99 缺前置条件、任务 102 缺失败处理均为结构 FAIL、`ERR_STEP_FIELD_MISSING`，没有冻结、分配或指令。 | [候选计划原始响应](evidence/SRS_F012-V1.139-plan-batch-20261103.json)、[异常矩阵](evidence/SRS_F012-V1.139-plan-F012_SIX-to-F012_ERROR-8-20261103.json)、[界面断言](evidence/SRS_F012-V1.139-task98-ui-20261103.json)、[截图](evidence/SRS_F012-V1.139-task98-detail-20261103.png) |
| TC-037.S2；R01–R03、R05 | 任务 98 的条件节点加五动作通过并冻结；条件节点折叠，分支动作计数。任务 101 六动作报 `ERR_STEP_LIMIT_EXCEEDED`，无版本也无自动截断。任务 100 的 `while(true)`、任务 103 的 `inputParams` 内 `eval` 均报 `ERR_STEP_LOOP_DETECTED`；正常“最多重试2次”放行。任务 104 虚构能力与任务 114 未启用能力均报 `ERR_CAPABILITY_GAP`。 | [五动作与循环](evidence/SRS_F012-V1.139-plan-batch-20261103.json)、[超限与虚构能力](evidence/SRS_F012-V1.139-plan-F012_SIX-to-F012_ERROR-8-20261103.json)、[未启用能力与正常重试](evidence/SRS_F012-V1.139-plan-F012_DISABLED_CAP-F012_LEGAL_RETRY-20261103.json) |
| TC-038.S1；R06、R09 | 任务 105 的 `waypointList` 报 `ERR_MOTION_SAFETY_FIELD`，任务 106 的合法 `waypointCount` 完成条件通过并冻结。所有结构、能力或约束失败任务均无步骤分配及设备指令；三类校验前没有下发。 | [异常矩阵](evidence/SRS_F012-V1.139-plan-F012_SIX-to-F012_ERROR-8-20261103.json)、[汇总断言](evidence/SRS_F012-V1.139-assertion-summary-20261103.json) |
| TC-038.S2；R07、R08 | 任务 113 的模型受控延迟 65 秒，约 60 秒记录 `ERR_PLANNING_MODEL_FAILED`；无匹配基线后转 `PENDING_MANUAL`，无计划或指令。任务 117 的任务提交仍在等待超时时，既有任务详情和设备列表分别于 0.006 秒、0.027 秒内响应，提交约 60.05 秒结束并安全转人工。任务 107 不可解析响应、任务 108 模型异常也安全转人工。任务 97 与 111 的目标理解、初次规划、局部重规划实际请求均没有虚构身份哨兵或 `passengerName` 字段；内部 `taskGoal` 保留原文，业务地点保留。V1.5（`0d798ceb53bc37498f353b4796f2081b92e2011b`）历史 P 保持原来源，不记为本版新实测。 | [超时](evidence/SRS_F012-V1.139-plan-F012_TIMEOUT-20261103.json)、[并发可访问性](evidence/SRS_F012-V1.139-timeout-concurrent-20261103.json)、[异常矩阵](evidence/SRS_F012-V1.139-plan-F012_SIX-to-F012_ERROR-8-20261103.json)、[初次送模](evidence/SRS_F012-V1.139-plan-batch-20261103.json)、[重规划送模](evidence/SRS_F012-V1.139-F012_REPLAN4-replan-20261103.json)、[V1.5 历史 P](evidence/TC-038-planning-boundary-followup-20261026T041347Z.json) |
| TC-061.S1/S2；R02、R10 | 任务 109 真实完成序号 2–6 五动作，条件节点未下发，总路径五步。任务 111 前两步完成后重规划请求携带剩余额度 3 和两份实际完成记录；模型返回四个替换动作，直接 `ERR_STEP_LIMIT_EXCEEDED`，没有截断或新版本。独立服务边界测试验证两完成＋三替换冻结为五动作版本，以及五步全完成时 `ERR_STEP_QUOTA_EXHAUSTED`、零次模型调用、转人工。失败和恢复事件没有增加动作计数。 | [真实执行](evidence/SRS_F012-V1.139-condition-execution-20261103.json)、[局部重规划](evidence/SRS_F012-V1.139-F012_REPLAN4-replan-20261103.json)、[独立边界测试源码](evidence/SRS_F012-V1.139-independent-quota-test.java)、[测试结果](evidence/SRS_F012-V1.139-surefire-summary-20261103.json) |

汇总探针对 21 项条件逐一断言，结果均为 true：[断言汇总](evidence/SRS_F012-V1.139-assertion-summary-20261103.json)。隔离构建副本的 F012 定向测试 15＋3 项和独立新增的边界测试 2 项均通过，0 失败、0 错误。前端生产构建完成 3269 个模块转译。

## 缺陷和证据口径

- `DEF-S3-036` 的 F012 展示缺口关闭。`DEF-S3-034` 与 `DEF-S3-071` 的 F012 规则已复测通过；其关联的 F013 邻接场景留待 F013 单独裁决。旧 V1.5 失败证据原样保留，未追溯改写为 V1.139 P。
- 任务 110 的探针在插入夹具时因 SQL 返回格式解析错误中断；清理了该夹具分配。任务 112 人为插入计划之外的第 6 步再走公开设备停用入口，入口在重规划前报 `NoSuchElementException`。这不是合法业务状态，作为无效夹具原始观察保留并标注“不计入产品裁决”：[原始记录与更正](evidence/SRS_F012-V1.139-F012_REPLAN5-replan-20261103.json)。零额度改由直接的 `ReplanningService` 边界测试覆盖，因为五个动作都完成后已没有计划内的失败步骤可由公开入口触发。
- 并发超时探针首次把阻塞的提交放在主线程，因此只测到了超时后的读取；[首次夹具记录](evidence/SRS_F012-V1.139-timeout-concurrent-attempt1-20261103.json)保留且不计产品结论。随后改成工作线程提交，在请求仍挂起时重测，结果见上表。
- 受控探针使用虚构身份哨兵，证据仅记录该虚构值；未上传桌面原始需求/用例文件、真实凭据或令牌。测试资源按 GPT/Claude 分区；本轮没有在共享服务上做故障注入。
- 结束检查：GPT schema 的资源风险规则已恢复为启用，机器人代理为 `ENABLED|ONLINE|IDLE`、无当前任务，测试任务无活跃分配，两个无效夹具任务的临时分配已清理：[环境恢复记录](evidence/SRS_F012-V1.139-environment-restored-20261103.json)。
