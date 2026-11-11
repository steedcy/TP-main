# SRS_NF005 故障隔离与自愈恢复整轮独立复测与验收报告

- **执行基线**：V2.4（含 2026-11-11 用户启动指令）
- **固定产品版本**：c34deba33c401791d976e36ab826a8e8cc66847d（标签 V1.197）
- **测试工作区/分支**：tip-gpt-f013 / ai/gpt-test
- **隔离环境**：PostgreSQL schema tip_gpt_nf005_v197_20261111，Redis DB 12，后端端口 18138，仿真终端 G126_ROBOT:18132 与 NF005_HEALTHY_18137:18137
- **共享资源约束**：未停止或改写共享 PostgreSQL 基础实例，未使用共享端口。
- **验收结论**：**REQUIREMENT_PASSED**
  - SRS_NF005.R01：**1P / 0F / 0NT**
  - 本轮指定故障注入步骤：**3 个核心场景全部 P**
  - 关联步骤复核：TC-024.S1~S2、TC-040.S1~S2、TC-056.S1~S2 当前证据均为 P
  - 缺陷/前置缺口：本轮无新增 F/NT

## 1. 规则口径

本轮先在 docs/BASELINE_CHANGES.md 登记 BL-011，澄清 R01 同时覆盖单点故障隔离、异常事务回滚、终端自动恢复，以及既有运动安全字段硬拦截。原运动安全要求保留，未降低阈值或删除历史证据。

## 2. 故障注入实测

| 场景 | 注入与观察 | 结果 |
|---|---|:---:|
| 单个仿真终端宕机 | 终止 G126_ROBOT（AGT-803437A3）。心跳超时后平台将其标记 OFFLINE，原因 ERR_HEARTBEAT_TIMEOUT；任务 1375 自动切换健康代理 AGT-DD76E82F 并完成，其他调度继续。 | **P** |
| 任务创建/模型网络超时 | 停止独立模型夹具 18117。创建任务返回 HTTP 503 / code 4113，任务转 PENDING_MANUAL 并保留 GOAL_SUBMITTED、GOAL_UNDERSTANDING_FAILED、BASELINE_DOWNGRADED、TASK_PENDING_MANUAL 诊断事件；plan_versions、task_step_assignments、device_commands、task_exceptions 均无新增。任务行保留是可追溯人工处理留痕，不属于下游脏业务数据。 | **P** |
| 分派阶段网络异常 | 故障终端处于陈旧 ONLINE 快照时创建任务 1377；其承接请求以 DEVICE_API_ERROR 拒绝，平台立即选择健康代理，任务完成且只有一个完成分配，无悬挂执行状态。 | **P** |
| 故障终端恢复 | 重启 G126_ROBOT 并重新绑定 AGT-803437A3；平台收到心跳后自动识别为 ONLINE/IDLE，能力恢复。 | **P** |

原始注入和恢复快照已复制到 acceptance/stage3/evidence/SRS_NF005-V1.197-raw-*.json；汇总断言见 SRS_NF005-V1.197-fault-injection.json。

## 3. 关联安全与结构边界复核

- FaultIsolationAndSelfHealingNF005Test：30/30 通过。
- MotionSafetyFieldsTest：2/2 通过。
- CommandDispatchAndExecutionF017Test：10/10 通过。
- 后端生产打包与仿真器生产打包均 BUILD SUCCESS。
- 结构硬校验失败不强行放行；运动安全字段在代理、仿真运行时和调度下发阶段拦截并留痕，未观察到未经校验的设备指令发送。

## 4. 证据索引

| 文件 | 用途 |
|---|---|
| acceptance/stage3/evidence/SRS_NF005-V1.197-fault-injection.json | 故障注入、回滚、接管、恢复的综合断言与资源隔离声明 |
| acceptance/stage3/evidence/SRS_NF005-V1.197-test-build.json | 30/30 专项单测、生产构建和报告/JAR 哈希 |
| acceptance/stage3/evidence/SRS_NF005-V1.197-raw-nf005-crash-dispatch.json | 单终端宕机原始快照 |
| acceptance/stage3/evidence/SRS_NF005-V1.197-raw-nf005-model-timeout.json | 模型网络超时与数据库计数原始快照 |
| acceptance/stage3/evidence/SRS_NF005-V1.197-raw-nf005-dispatch-exception.json | 分派异常、拒绝原因和健康代理接管原始快照 |
| acceptance/stage3/evidence/SRS_NF005-V1.197-raw-nf005-recovery-final.json | 终端恢复后的心跳与 ONLINE/IDLE 原始快照 |
| acceptance/stage3/evidence/SRS_NF005-V1.197-environment-cleanup.json | 测试进程停止、隔离端口释放和共享资源未触碰的收尾核对 |

## 5. 收口裁决

R01 的当前独立实测满足故障隔离、事务边界、恢复识别和安全拦截要求，裁决为 **1P / 0F / 0NT**。测试进程随后停止并核对端口释放；不合并任何产品源码修改。
