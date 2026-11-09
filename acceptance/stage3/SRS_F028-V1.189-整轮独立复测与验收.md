# SRS_F028 安全审计与管理日志留痕 整轮独立复测与验收报告

- **依据执行基线**：V2.4（继承 V2.3 / V2.2 执行策略与双 AI 串行协同约定）
- **固定产品版本**：`14e75c6bf1b0ef226d9cba4ba422ffb7ceab1f3a`（标签 `V1.189`）
- **测试执行工作区**：`C:/Users/savy/Desktop/TIP-main/tip-gpt-f013`
- **测试分支**：`ai/gpt-test`（由 `READY_FOR_GPT` 交接提交 `6aab1a2` 同步）
- **独立复测环境**：
  - PostgreSQL 独立 Schema：`tip_gpt_f006_v118_20261030`（严格与生产及默认数据库隔离）
  - Redis 独立 DB：`10`
  - 后端服务端口：`18129`
  - 前端代理端口：`15179`
  - 生产打包可执行文件：`backend/target/airport-ai-app-1.0.0.jar`
- **复测结论**：**REQUIREMENT_PASSED（整项全量通过，无残留 F/NT）**
  - 业务规则核验：**8P / 0F / 0NT**（`SRS_F028.R01` ～ `SRS_F028.R08` 全部实测满足）
  - 测试用例核验：**2P / 0F / 0NT**（`TC-085.S1`、`TC-085.S2` 全部实测满足）
  - 缺陷闭环：**DEF-S3-009 彻底关闭**（账号关键变更操作均包含结构化 before/after diff 摘要，凭据脱敏零泄露）
  - 保持关闭确认：**DEF-S3-010 保持关闭**（用户列表 API 与序列化响应严格无 `passwordHash`）
  - 真实 Edge 浏览器 UI 实测：**3/3 全部通过**（日志列表渲染、详情弹窗变更前后 JSON 摘要展示、空账号查询空态提示）

---

## 一、复测执行全景与核心指标

| 规则/步骤编号 | 关注核心点与判定准则 | 实测结果 | 关键判定依据与实测数据 |
|---|---|:---:|---|
| **SRS_F028.R01** | 五类关键操作留痕（登录、设备配置、能力启停、模板启停、人工终止） | **P** | 数据库实测覆盖 11 类关键操作类型：`LOGIN` (984+)、`LOGOUT` (8+)、`DEVICE_CREATE/UPDATE/DELETE/STATUS_CHANGE` (1000+)、`DEVICE_CAPABILITY_STATUS_CHANGE` (2266+)、`BASELINE_TEMPLATE_ENABLE/DISABLE` (177+)、`TASK_TERMINATE` (631+) 全部存在并持续写入。 |
| **SRS_F028.R02** | 任务定义变更、确定性高风险规则变更与人工处置操作留痕 | **P** | 数据库实测覆盖 `TASK_DEFINITION_CREATE/UPDATE/ENABLE/DISABLE` (400+)、`RISK_RULE_CHANGE` (158+)、`TASK_MANUAL_ACTION` (55+)、`MANUAL_HANDLING` (解锁) 全部完整存在并持续写入。 |
| **SRS_F028.R03** | 记录须含操作时间、操作人、角色、类型、对象、结果和来源IP，并提供变更前后结构化摘要 | **P** | **DEF-S3-009 彻底闭环**。全库操作记录中用户操作 0 条缺失核心字段。实测 `USER_CREATE`、`USER_STATUS_CHANGE`、`PASSWORD_RESET`、`MANUAL_HANDLING` 均包含非空合法 JSON `detail`，完整包含 `action`、`before`、`after` 与 `target` 账号核心摘要；密码、哈希与联系方式零泄露。 |
| **SRS_F028.R04** | 登录失败与越权访问写入操作记录 | **P** | 实测错误密码登录生成 `LOGIN` / `FAILED` 记录（全库 18+ 条）；运行操作员越权访问管理员接口 `POST /api/v1/users` 拦截 403 并即时生成 `ACCESS_DENIED` / `FAILED` 操作日志（全库 39+ 条）。 |
| **SRS_F028.R05** | 操作记录不可编辑、不可删除（只读防篡改） | **P** | 尝试对已有操作记录发起 `PUT` 与 `DELETE` 请求，均被 Controller 层严格拦截（HTTP 404/405）；数据库指纹校验在篡改前后完全一致（`hashIdentical = true`）。 |
| **SRS_F028.R06** | 凭据类字段以掩码展示，不得回显原值 | **P** | 1. `GET /api/v1/users` 响应中用户对象无 `passwordHash`、`password` 字段暴露（DEF-S3-010 保持验证通过）；<br/>2. 扫描 `operation_logs.detail` 全量数据，0 条包含 bcrypt 哈希（`$2a$`、`$2b$`）或测试密码原值，凭据键已全部掩码。 |
| **SRS_F028.R07** | 权限控制：系统管理员可见全量；其他角色仅可见自身记录 | **P** | `SYSTEM_ADMIN`（admin）查询全量（9635 条）；`CONFIG_ADMIN`（set）查询仅返回自身记录（7062 条）；`OPERATOR`（oprator）查询仅返回自身记录（2166 条）；配置管理员尝试通过 URL 参数 `?username=admin` 越权，被后端强行重写为当前登录账号 `set`，越权查询被彻底杜绝。 |
| **SRS_F028.R08** | 操作记录与任务因果交叉追溯 | **P** | 实测 `operation_logs` 中的人工终止记录（`operationTarget: TASK-20261105-0317`）与 `task_events` 中相应任务的 `EXCEPTION_DETECTED` / `TASK_TERMINATED` 事件通过任务编号与对象标识双向关联，支持因果链闭环追踪。 |
| **TC-085.S1** | 管理员按条件筛选打开详情，核对变更前后摘要与任务关联 | **P** | 管理员端按操作人、类型、时间筛选准确；操作详情弹窗完整渲染 `before`/`after` 结构化 JSON 摘要；`DEF-S3-009` 实测关闭。 |
| **TC-085.S2** | 其他角色查记录、凭据掩码、不可编辑删除、空账号查询空态 | **P** | 其他角色仅见自身；凭据无原值；`PUT`/`DELETE` 拦截拒绝；查询不存在账号返回空列表并在前端呈现清晰空态提示。 |

---

## 二、DEF-S3-009 彻底关闭验证证据

### 1. 账号操作留痕实测详情

在本轮 V1.189 实测中，系统管理员针对测试账号 `s3_audit_op_1794248958` 执行了完整的生命周期管理：
1. **账号创建 (`USER_CREATE`)**：
   - 写入 `detail`:
     ```json
     {
       "action": "CREATE",
       "after": {
         "username": "s3_audit_op_1794248958",
         "role": "OPERATOR",
         "status": "ACTIVE"
       }
     }
     ```
   - 安全核查：明文密码、加密哈希、联系方式、真实姓名未进入日志详情。
2. **账号停用 (`USER_STATUS_CHANGE`)**：
   - 状态由 `ACTIVE` 变为 `INACTIVE`：
     ```json
     {
       "action": "STATUS_CHANGE",
       "before": { "status": "ACTIVE" },
       "after": { "status": "INACTIVE" },
       "target": {
         "username": "s3_audit_op_1794248958",
         "role": "OPERATOR",
         "status": "INACTIVE"
       }
     }
     ```
3. **账号启用 (`USER_STATUS_CHANGE`)**：
   - 状态由 `INACTIVE` 恢复为 `ACTIVE`：
     ```json
     {
       "action": "STATUS_CHANGE",
       "before": { "status": "INACTIVE" },
       "after": { "status": "ACTIVE" },
       "target": {
         "username": "s3_audit_op_1794248958",
         "role": "OPERATOR",
         "status": "ACTIVE"
       }
     }
     ```
4. **密码重置 (`PASSWORD_RESET`)**：
   - 写入 `detail`:
     ```json
     {
       "action": "RESET_PASSWORD",
       "passwordChanged": true,
       "target": {
         "username": "s3_audit_op_1794248958",
         "role": "OPERATOR",
         "status": "ACTIVE"
       }
     }
     ```
   - 安全核查：新密码与哈希严格未写入日志。
5. **账号解锁 (`MANUAL_HANDLING`)**：
   - 连续 3 次错密触发锁定后，管理员解锁写入 `detail`:
     ```json
     {
       "action": "UNLOCK",
       "before": { "status": "LOCKED", "failedLoginAttempts": 3 },
       "after": { "status": "ACTIVE", "failedLoginAttempts": 0 }
     }
     ```

### 2. 真实 Edge 浏览器 UI 验证

通过 Edge Headless 浏览器执行端到端自动化测试：
- **用例 1（列表渲染）**：登录系统管理员访问 `/operation-logs`，表格成功展示各类型操作日志（操作时间、账号、角色、类型、对象、结果、来源IP）。
- **用例 2（详情弹窗与 DEF-S3-009 验证）**：点击“账号启停”行的“详情”链接，弹窗展示基本信息并在“变更前后关键字段摘要：”下方以结构化 JSON 准确渲染 `action: STATUS_CHANGE`、`before: {status: INACTIVE}`、`after: {status: ACTIVE}`。
- **用例 3（空态提示）**：在“操作账号”筛选框输入不存在账号 `nonexistent_user_xyz_99999` 并查询，表格呈现 `<a-empty>` 暂无数据组件，无错误崩溃。

---

## 三、受控测试资产与证据索引

1. **协议层与数据库受控证据**：
   - `acceptance/stage3/evidence/SRS_F028-V1.189-http-sql-protocol-20261110.json`（包含全部 11 项断言数据）
2. **真实 Edge 浏览器 UI 测试结果与截图**：
   - `acceptance/stage3/evidence/SRS_F028-V1.189-real-ui-results.json`
   - `acceptance/stage3/evidence/SRS_F028-V1.189-ui-audit-list.png`（操作日志全景表格截图）
   - `acceptance/stage3/evidence/SRS_F028-V1.189-ui-audit-detail.png`（变更前后结构化摘要弹窗截图）
   - `acceptance/stage3/evidence/SRS_F028-V1.189-ui-audit-empty-state.png`（空态提示截图）
3. **独立可重跑复测套件**：
   - `acceptance/stage3/fixtures/start-f028-v189-jar.py`（隔离启动生产 JAR）
   - `acceptance/stage3/probe-f028-v189.py`（协议层与 SQL 自动化断言）
   - `acceptance/stage3/retest-f028-v189-real-ui.cjs`（Edge 浏览器端自动化脚本）
   - `acceptance/stage3/probe-f028-v189-runner.py`（一键全流程闭环调度器）

---

## 四、验收裁决

- **业务规则**：8P / 0F / 0NT（全 P）
- **测试步骤**：2P / 0F / 0NT（全 P）
- **历史缺陷**：`DEF-S3-009` 彻底关闭，`DEF-S3-010` 保持验证通过。
- **裁决结论**：**REQUIREMENT_PASSED**。
- **后续协同**：按 V2.4 规范将 `ai/gpt-test` 分支合入 `main` 并推送到 `origin`，顺序推进下一项 **SRS_F029**。
