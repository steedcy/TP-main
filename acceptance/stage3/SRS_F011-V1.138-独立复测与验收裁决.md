# SRS_F011 / V1.138 独立复测与验收裁决

**结论：SRS_F011 通过。**执行基线 V2.3，产品注解标签 `V1.138` 解引用为 `64dd06156d598bef2dd117bb7fbff50d59f1396a`；修复方交接提交 `d66703eea213aa90e824122dff78db465ff27ae1` 已快进合入 GPT 的 `ai/gpt-test`。本结论只覆盖 F011 的 `TC-035.S1/S2`、`TC-036.S1/S2` 与 `R01–R08`，不预判后续需求。

GPT 独立复制 V1.138 源码，在受限 JVM 内存下完成 `mvn -o -Dmaven.test.skip=true package`（`BUILD SUCCESS`）。实时批量探针使用同一源码独立编译并封装的低内存运行包；随后对 Maven 正式构建包再做送模冒烟，[原始证据](evidence/SRS_F011-V1.138-maven-binary-smoke-20261103.json)含包 SHA-256，结果相同。隔离环境为专属 schema `tip_gpt_f006_v118_20261030`、Redis DB 10、后端 18129、受控模型 18117、既有 GPT 仿真体 18132。所有身份信息均为虚构哨兵，未使用真实旅客资料；未向共享服务注入故障。

| 步骤与规则 | V1.138 独立观察 | 原始证据 |
| --- | --- | --- |
| `TC-035.S1`、R01–R04 | 任务 89 中，执行中忙碌代理的 `availableUntil` 恰为步骤 `dispatchedAt + 60s`，空闲代理取当前时间；任务 93/94 排除停用/归档代理，离线代理亦不在候选。机器人快照只含已启用能力；V1.137 任务 84 对未测试/失败/停用能力的过滤可按未变更的 `ContextSnapshotService` 继续引用。快照随任务保存并有 `CONTEXT_SNAPSHOT_GENERATED` 事件。`DEF-S3-031` 关闭。 | [忙碌可用时间](evidence/SRS_F011-V1.138-busy-availability-20261103.json)、[停用与归档](evidence/SRS_F011-V1.138-agent-exclusions-20261103.json)、[旧版同实现能力过滤](evidence/SRS_F011-V1.137-initial-20261102.json)、[数据库与邻接读取](evidence/SRS_F011-V1.138-neighbor-persistence-20261103.json) |
| R05 | 当前任务快照均有 `generatedAt`，当前初次规划与重规划均将该时间交给监督判定。接近过期超过 60 秒触发风险信号的独立观察取自 V1.112（`e1b06ee0c2b07b3f545a9a35c4be3c91b2b3c970`）；至 V1.138，`RiskAssessmentService` 未变，配置阈值仍为 60 秒。本轮按 V2.3 影响复核引用该历史覆盖，**不记为 V1.138 新执行了一次 62.5 秒延迟测试**。 | [V1.112 原始风险信号](evidence/SRS_F002-V1.112-risk-signals-20261029.json)、[V1.138 快照与监督时间线](evidence/SRS_F011-V1.138-busy-availability-20261103.json) |
| `TC-035.S2`、R06、R08 | 任务 86 的英文身份哨兵、任务 95 的中文姓名和 `.invalid` 邮箱在目标理解与初次规划实际请求中均消失，业务地点/航班参数保留，内部 `taskGoal` 与 `originalGoal` 保留原文。任务 92 通过自有任务的执行中分配及公开代理停用入口触发真实局部重规划：旧快照不变，新快照独立持久化且时间更晚，正确记录另一代理的位置、在线和负载变化；三次模型请求（目标理解、初次规划、局部重规划）均无虚构身份字段。新规划请求的候选数量与新快照一致。`DEF-S3-088` 关闭，V1.137 失败记录保留。 | [英文哨兵](evidence/SRS_F011-V1.138-goal-privacy-20261103.json)、[中文与邮箱](evidence/SRS_F011-V1.138-goal-privacy-classes-20261103.json)、[局部重规划](evidence/SRS_F011-V1.138-replan-context-20261103.json)、[独立持久化与候选一致性](evidence/SRS_F011-V1.138-neighbor-persistence-20261103.json) |
| `TC-036.S1`、R07 | 任务 90 暂时停用任务族唯一所需 `CAP_NAVIGATION`，快照报告完整缺口并生成 `ERR_CAPABILITY_GAP_ALL_MISSING`；受控模型只有目标理解请求、**0 次规划请求**，任务转 `PENDING_MANUAL`，能力状态随后恢复。旧版 P 保持原来源。 | [能力全缺失](evidence/SRS_F011-V1.138-capability-gap-20261103.json) |
| `TC-036.S2` | 仅在 GPT 后端配置 `APP_CONTEXT_FAULT_INJECTION_FAILED_AGENT_CODES=AGT-D68FD3AB`。任务 91 的 `failedAgentCodes` 准确列出失败代理，候选只含查询成功的机器人；四类所需能力的 `available/missing` 与成功候选实际能力集合一致，缺失展示能力。 | [部分查询失败](evidence/SRS_F011-V1.138-partial-query-failure-20261103.json) |

邻接冒烟：态势总览、任务列表及任务详情可读；任务 92 的两份快照在 API 和数据库中数量一致，新规划模型请求使用新快照候选事实。测试期间对 GPT 专属 schema 的临时能力、代理状态、设备位置和执行中分配均已恢复或删除；测试任务及其不可变快照、事件留作证据。GPT 后端与模型夹具已停止，既有仿真体保持原配置。

`acceptance/stage3/steps.csv` 四步和 `rules.csv` 八规则均登记 P，`issues.csv` 中 `DEF-S3-031/088` 登记已修复并独立复测通过。各行保留旧失败事实和旧证据索引，按版本区分 V1.112/V1.137 历史覆盖与 V1.138 当前实测。本轮未修改产品代码、F010 台账、其他 worktree、未跟踪 `document/` 或 F020–F022 WIP。
