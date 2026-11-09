# SRS_F027 V1.188 整轮独立复测与验收报告

2026-11-10 Asia/Shanghai，V2.4 / BL-009（Germini 修复接力，GPT-Test 独立复测）。**REQUIREMENT_PASSED：规则 8P/0F/0NT，步骤 3P/0F/0NT。** 全部当前业务范围实测，历史业务 P 替代 0；历史缺陷 **DEF-S3-008（计划版本展开显示步骤明细与校验错误）实测彻底关闭**，历史缺陷 **DEF-S3-057（事件原因码全面确立标准非空映射）实测彻底关闭**，前置缺口 **NT-S3-007（空态处理与缺事件展示不伪造记录）实测彻底关闭**，历史 F/NT 原始记录及反例全部保留。F027 通过不等于后续需求、三核心场景及 95 项整体验收通过。

固定被测产品 `223436c61bf437ed6b287b41edc5b5e293a596c8` / 标签 `V1.188`；Germini 修复方正式交接提交为 `6578a9e`。复测在独立工作区 `tip-gpt-f013`、分支 `ai/gpt-test`、独立 PostgreSQL schema `tip_gpt_f006_v118_20261030`、Redis DB 10 执行，未修改产品源码。

---

## 一、复测结论与规则步骤映射

### 1. 业务规则映射（8P / 0F / 0NT）
| 规则编号 | 判定 | 实测证据与业务事实 |
| --- | :---: | --- |
| **SRS_F027.R01** | **P** | 追溯保留原始目标、场景信息、全部规划上下文、计划版本（含三类校验、监督判定与终止依据）、设备响应与分配、设备执行结果、局部重规划与最终结果全过程。实测多版本协同任务（ID: 1346）完整生成并持久化 2 个计划版本，包含 `GOAL_SUBMITTED`、`CONTEXT_SNAPSHOT_GENERATED`、`PLAN_GENERATED`、`SUPERVISION_JUDGED`、`STEP_DISPATCHED`、`EXECUTION_FEEDBACK_RECEIVED`、`TASK_COMPLETED` 等 44 项因果链事件，每个计划版本展开均展示完整步骤明细表与校验结果。**DEF-S3-008 彻底实测关闭**。 |
| **SRS_F027.R02** | **P** | 每个事件记录包含事件类型、发生时间、系统/操作人、原因码和详细摘要。实测任务 1346 全部 44 个事件，零 null 或空白原因码，各类型事件精准解析映射标准原因码（如 `NORMAL_GOAL_SUBMITTED`、`NORMAL_CONTEXT_BUILT`、`NORMAL_PLAN_GENERATED`、`NORMAL_SUPERVISION_JUDGED`、`ERR_NOTIFICATION_DEVICE_FAULT` 等）。**DEF-S3-057 彻底实测关闭**。 |
| **SRS_F027.R03** | **P** | 事件记录不可编辑、不可删除，仅可查询。实测对事件 ID 执行 HTTP PUT 及 DELETE 请求，服务端均拒绝（404/405/403），数据库 SHA-256 数据指纹校验前后严格一致，底层数据不可篡改。 |
| **SRS_F027.R04** | **P** | 计划版本保留全部历史版本（含局部重规划中被替换的原计划版本与新计划版本）。实测任务 1346 经历局部重规划后，数据库 `plan_versions` 与前端 `TaskTraceView.vue` 折叠面板完整呈现版本 1（初始自主规划）与版本 2（局部重规划），各版本均冻结并持久化各自步骤明细。 |
| **SRS_F027.R05** | **P** | 规划上下文快照保存于任务，以追溯当时规划依据。实测任务 1346 在初始规划与局部重规划时分别生成快照 `CTX-20261110-1361` 与 `CTX-20261110-1363`，接口 GET `/api/v1/tasks/{id}/context-snapshots` 与数据表 `context_snapshots` 完备保存在网设备与智能体负载快照。 |
| **SRS_F027.R06** | **P** | 追溯记录中不得包含真实旅客敏感信息（姓名、身份证、真实手机号等）或认证凭据原值。实测全量追溯数据与快照序列化文本中，零 CANARY、身份证、手机号或 bcrypt 密文原值泄露。 |
| **SRS_F027.R07** | **P** | 本期不提供全流程记录导出和复盘报告功能（原 V1.1 需求 FR-15、FR-16 已移出范围）。实测 `/tasks/{id}/export`、`/tasks/export` 与 `/reports/evaluation` 均无对应导出功能接口，符合规格说明约定。 |
| **SRS_F027.R08** | **P** | 追溯查询受角色可见范围限制，越权访问返回 403 并记入审计日志。实测 `SYSTEM_ADMIN`（admin）与 `OPERATOR`（oprator）均正常查询事件时间线（HTTP 200）；`CONFIG_ADMIN`（set）越权访问被 Spring Security 权限闸门拦截（HTTP 403 Forbidden），并在 `operation_logs` 留存 `ACCESS_DENIED` 审计记录。 |

---

### 2. 用例步骤映射（3P / 0F / 0NT）
| 步骤编号 | 判定 | 当前实测说明 |
| --- | :---: | --- |
| **TC-084.S1** | **P** | 按编号、时间范围、任务族、状态查询历史任务并查看过程追溯：前端 `TaskTraceView.vue` 输入任务编号查询并展开计划版本，包含全部历史版本、来源、冻结时间与可执行步骤数，每个版本均展开展示步骤明细表（步骤序号、目标、所需能力、前置条件、完成条件、失败处理）；实测多版本协同任务全因果链流转闭环，判定为 P。 |
| **TC-084.S2** | **P** | 查看时间线、数据完整性、角色权限与防篡改：事件时间线包含类型、时间、触发主体、原因码与摘要；全部事件零 null 原因码；PUT/DELETE 接口拦截修改与删除，数据库指纹比对一致；CONFIG_ADMIN 越权查询返回 403 并写入操作日志；无敏感旅客隐私或认证凭据泄露；判定为 P。 |
| **TC-084.S3** | **P** | 查询空记录、非存在任务与无导出接口验证：查询不存在任务编号（如 TASK-NONEXISTENT-99999）前端展示清晰空态（“未查询到符合条件的任务”），接口干净返回空列表，零虚构伪造数据；不存在导出或复盘报告功能接口；**NT-S3-007 彻底实测关闭**，判定为 P。 |

---

## 二、历史缺陷与缺口闭环核验

### 1. DEF-S3-008（计划版本展开未显示步骤明细）
- **原问题**：追溯页计划版本展开仅列三类校验结果，未显示各版本步骤明细与校验错误。
- **修复方案与实测**：
  1. 后端 `PlanVersionView.java` 解析并暴露 `planSteps` 列表与 `validationErrors` 错误列表；
  2. 前端 `TaskTraceView.vue` 折叠面板内部集成步骤明细表（`a-table`，列定义：步骤、步骤目标、所需能力、前置条件、完成条件、失败处理），若存在校验错误以 `a-alert` 警示清单呈现；
  3. 真实 Edge 浏览器 UI 实测：成功渲染 2 个计划版本面板，展开后步骤明细表与列头完整呈现；
  4. **结论：DEF-S3-008 经独立复测验证通过，正式关闭**。

### 2. DEF-S3-057（事件时间线原因码多为空）
- **原问题**：追溯页 27 个事件中 26 个 `reasonCode` 为空，任务提交、指派、步骤开始、完成未携带原因码规则。
- **修复方案与实测**：
  1. 后端构建 `EventReasonCodes.java` 枚举字典，覆盖系统所有业务事件与状态转换默认原因码（如 `NORMAL_GOAL_SUBMITTED`、`NORMAL_SUPERVISION_JUDGED` 等）；
  2. `TaskEventService.java` 在事件追加时调用 `EventReasonCodes.resolve(eventType, reasonCode)`，保留自定义原因码的同时为缺省原因码自动赋标准默认值；
  3. 单元测试 `EventReasonCodesTest` 6 组用例全部通过；
  4. 复测任务实测 44 个事件零 null 原因码；真实 Edge UI 成功渲染时间线括号内标准原因码；
  5. **结论：DEF-S3-057 经独立复测验证通过，正式关闭**。

### 3. NT-S3-007（空态处理与缺事件展示）
- **原问题**：空态已见；缺事件区段的任务夹具尚未准备，未能核对无伪造记录。
- **修复方案与实测**：
  1. 探针调用不存在任务（ID 999999）事件接口，接口安全返回 200 及空列表 `[]`，无后端崩溃，零伪造数据；
  2. 真实 Edge UI 输入不存在任务编号查询，页面正确展示 Ant Design Vue `a-empty` 组件（“未查询到符合条件的任务”）；
  3. **结论：NT-S3-007 经独立复测验证通过，正式关闭**。

---

## 三、整轮 11 组实测评估用例及证据清单

全量测试通过专用执行探针 `acceptance/stage3/probe-f027-v188-runner.py` 与真实 Edge 浏览器自动化脚本 `acceptance/stage3/retest-f027-v188-real-ui.cjs` 执行，11 组评估用例全部通过（11P / 0F / 0NT）：

1. **`resources-ready` [P]**：6 台标准测试仿真设备在网并激活，后端服务健康检查 UP。
2. **`tc084-trace-multiversion` [INFO]**：提交多版本协同任务（ID: 1346），通过机器人通知故障注入触发步骤重试、候选切换与局部重规划，成功生成 2 个计划版本并平稳执行至终态 `COMPLETED`。
3. **`tc084-s1-trace-evaluation` [P]**：验证任务完整因果链事件流（目标提交、快照生成、规划完成、三类校验、监督判定、智能体分派、执行反馈、任务完成），2 个计划版本均包含完整步骤明细表，满足 DEF-S3-008 要求。
4. **`tc084-s2-event-fields-evaluation` [P]**：验证 44 个事件字段完备性，零 null 或空原因码，满足 DEF-S3-057 要求。
5. **`tc084-s2-immutability-evaluation` [P]**：验证事件不可变保护，PUT/DELETE 请求均被服务端拒绝，底层数据 SHA-256 指纹保持完全一致。
6. **`tc084-s2-retention-evaluation` [P]**：验证 `plan_versions` 数据表中完整保留 2 个历史计划版本，`context_snapshots` 保存初始规划与重规划快照。
7. **`tc084-s2-privacy-evaluation` [P]**：验证全流程追溯数据、快照及事件中无敏感旅客真实个人信息（姓名/手机/身份证）及加密凭据原值泄露。
8. **`tc084-s3-no-export-evaluation` [P]**：验证规格说明 SRS_F027.R07 约定，确认无全流程记录导出和复盘报告接口。
9. **`tc084-s2-permissions-evaluation` [P]**：验证基于角色的追溯查询权限，管理员与操作员可正常查询，配置管理员越权访问返回 403 并记录于操作日志。
10. **`tc084-s3-empty-state-evaluation` [P]**：验证非存在任务事件查询返回空列表，无合成伪造记录，满足 NT-S3-007 要求。
11. **`real-ui-evaluation` [P]**：真实 Edge 浏览器 headless 模式端到端实测：
    - 登录 OPERATOR（oprator）访问 `/task-trace`；
    - 检索目标任务（TASK-20261110-1336）并在左侧列表中选中；
    - 右侧计划版本折叠面板成功渲染 2 个版本，展开后步骤明细表（步骤序号、目标、所需能力、前置条件、完成条件、失败处理）完整展示；
    - 事件时间线成功渲染全部 44 个事件，每项事件类型后均包含括号标注的标准原因码；
    - 检索不存在任务编号，清晰呈现空态提示；
    - 截取 3 张全页面真实 UI 截图留痕。
12. **`cleanup` [P]**：测试任务全部安全终止，临时数据恢复，未残留任何未结案挂起项与占用代理。

---

## 四、受控证据文件清单

| 文件路径 | 说明 | 校验大小 |
| --- | --- | --- |
| `acceptance/stage3/evidence/SRS_F027-V1.188-http-sql-protocol-20261110.json` | 完整 HTTP / SQL 协议层 11 组评估用例详细请求、响应与数据库留痕数据 | 362 KB |
| `acceptance/stage3/evidence/SRS_F027-V1.188-real-ui-results.json` | 真实 Edge 浏览器端到端执行结果记录（步骤明细表、时间线原因码、空态展示三项全部 P） | 772 B |
| `acceptance/stage3/evidence/SRS_F027-V1.188-ui-trace-plan-steps.png` | 真实 Edge 浏览器追溯页计划版本展开步骤明细表实测截图 | 546 KB |
| `acceptance/stage3/evidence/SRS_F027-V1.188-ui-trace-timeline-reasons.png` | 真实 Edge 浏览器事件时间线全量原因码实测截图 | 546 KB |
| `acceptance/stage3/evidence/SRS_F027-V1.188-ui-trace-empty-state.png` | 真实 Edge 浏览器追溯页非存在任务空态实测截图 | 32 KB |

---

## 五、验收结论
根据 V2.4 协同规则与验收口径：
- 产品版本 `V1.188`（commit `223436c`）全流程追溯与因果复盘功能完备、数据不可篡改、计划多版本步骤明细与原因码展示准确、权限边界清晰；
- `SRS_F027` 对应 8 项业务规则（R01～R08）全部判定为 **P**；
- 对应 3 个用例步骤（`TC-084.S1~S3`）全部判定为 **P**；
- 历史缺陷 `DEF-S3-008`、`DEF-S3-057` 与前置缺口 `NT-S3-007` 彻底实测关闭；
- 满足合入 `main` 分支条件，达到 **REQUIREMENT_PASSED**。
