# SRS_NF016 审计日志完整性与防篡改（登录连续失败锁定、管理员解锁、审计只读防篡改与超长入参留痕）整轮独立复测与验收报告

- **依据执行基线**：V2.4（继承 V2.3 / V2.2 全景规范与双 AI 串行协同约定）
- **固定产品版本**：`b57c66f580cd74581c890b5739796a746fd2ad5c`（标签 `V1.196`）
- **测试执行工作区**：`C:/Users/savy/Desktop/TIP-main/tip-gpt-f013`
- **测试分支**：`ai/gpt-test`（接收并合入 `origin/ai/claude-fix` 交接提交 `19b0cce6a7eb3fbcb2242df50588c3710d8be629`）
- **隔离运行环境**：PostgreSQL 独立 schema `tip_gpt_nf016_v196_20261111`（经受控 TCP 代理 `127.0.0.1:15516` 连接）、Redis DB `11`、后端生产 JAR 监听端口 `127.0.0.1:18131`（未触碰共享 schema `public` 或端口 `8080`/`5173`/`8091-8096`）
- **复测结论**：**REQUIREMENT_PASSED（整项全量通过，无残留 F/NT）**
  - 业务规则核验：**1P / 0F / 0NT**（`SRS_NF016.R01` 实测满足预期）
  - 关联用例步骤核验：**4P / 0F / 0NT**（`TC-002.S1`、`TC-002.S2`、`TC-002.S3`、`TC-002.S4` 全部实测满足预期）
  - 独立协议与数据库实测探针：**12/12 检查项全部 PASS**（含 94 次越权/伪造管理员防篡改请求拦截、3 张审计/事件表 SHA-256 指纹前后零变动、5,906 字符 URI 与 12KB+ 结构化长字段落库无截断无乱码、全表 191 条记录零凭据原值泄露）
  - 专项审计与认证单测套件：**18/18 全部通过**（`AuditLogIntegrityAndTamperResistanceNF016Test` 5 项、`LoginFaultResponseTest` 2 项、`AuthServiceLockoutAuditTest` 2 项、`AccountAuditDetailTest` 5 项、`UserAccessOrderTest` 4 项，0 失败 0 错误）
  - 生产构建验证：后端生产 JAR（`airport-ai-app-1.0.0.jar`，含 `V30__widen_audit_and_event_columns.sql` 迁移）构建与独立启动健康检查均通过。

---

## 一、规则与关联用例步骤核验全景

| 规则/步骤编号 | 关注核心点与判定准则 | 实测结果 | 关键判定依据与实测数据 |
|---|---|:---:|---|
| **SRS_NF016.R01** | 同一账号连续 3 次密码验证失败后锁定，须由系统管理员手动解锁，锁定与解锁全过程留痕；审计日志与事件记录具备完整性与防篡改保护，超长入参留痕无截断且字段结构完整 | **P** | 1. 连续 3 次错密锁定与管理员手动解锁闭环：前 2 次错密保持 `ACTIVE`（计数 1、2），第 3 次错密跃迁 `LOCKED`（记录 `locked_at`）并独立写入 `ACCOUNT_LOCKED` 审计（含 `before`/`after` 状态与失败次数）；锁定期间正确密码仍拒绝登录；仅 `SYSTEM_ADMIN` 可调用 `/api/v1/users/{id}/unlock`（`OPERATOR` 与 `CONFIG_ADMIN` 均 403 拦截），解锁后恢复 `ACTIVE`、计数归零、`locked_at` 清空，并写入 `MANUAL_HANDLING` 解锁审计；<br/>2. 伪造/真实管理员防篡改拦截：对 `/api/v1/operation-logs`、`/{id}`、`/{nonExistentId}` 及 `/api/v1/tasks/{taskId}/events`、`/{eventId}` 发起 94 次 `PUT`/`DELETE`/`PATCH` 及 `X-HTTP-Method-Override`/`_method=DELETE` 篡改请求，已认证会话统一返回 HTTP `405 Method Not Allowed`（`code: 3004`，`Allow: GET`，提示“记录不可修改或删除”），伪造 JWT/篡改令牌/伪造管理员头返回 `401`；<br/>3. 数据库审计表 SHA-256 指纹零变动：94 次篡改请求前后，`operation_logs`（187 行，指纹 `3695af7b...53ee22ce`）、`task_events`（4 行，指纹 `19d7f3b9...9a337a33`）、`device_events`（1 行，指纹 `a7f9d05b...d62057aa`）及目标单行记录（`id=181`，指纹 `99ab3fe2...b5fc30ca`）SHA-256 指纹 100% 完全一致；<br/>4. 超长入参留痕完整性：5,906 字符 URI 越权请求、`64` UTF-16 代码单元含中文+Emoji 设备名/任务名、`239` 字符端点、`128` 位脱敏凭据、`12KB` 完成条件及 `32` UTF-16 代码单元含 Emoji 登录名均完整落库，零截断、零 `\ufffd` 乱码，JSON 结构完整，全表 191 条审计记录零密码/凭据明文泄露。 |
| **TC-002.S1** | 分别以不存在账号、停用账号和账号 B 错误密码登录；后续锁定检查改用独立账号 A | **P** | 不存在账号（HTTP 401/2002）、停用账号 C（HTTP 403/2004）、账号 B 错密（HTTP 401/2002）均统一返回 `"账号或密码错误"`，均未颁发 Token，各自写入 `LOGIN/FAILED` 审计记录；账号 A 失败计数保持 `0` 未受污染，账号 B 计数为 `1`。 |
| **TC-002.S2** | 账号 A 从 0 计数连续输入错误密码：第 1、2 次后查看锁定状态，第 3 次后再用正确密码登录 | **P** | 第 1、2 次错密后状态均为 `ACTIVE`（计数 `1`、`2`，`lockedAtSet=false`）；第 3 次错密后状态变为 `LOCKED`（计数 `3`，`lockedAtSet=true`）；锁定期间输入正确密码仍返回 HTTP 403（`code: 2005`，message `"账号或密码错误"`），不建立会话。 |
| **TC-002.S3** | 系统管理员手动解锁 A；输入 2 次错误密码后正确登录，再输入 1 次错误密码 | **P** | 操作员与配置管理员尝试解锁均返回 403 且账号保持 `LOCKED`；系统管理员解锁返回 200，状态恢复 `ACTIVE`、计数清零、`locked_at` 清空；随后 2 次错密计数升至 `2`（仍 `ACTIVE`），正确密码登录成功颁发 Token 且计数再次归 `0`，后续 1 次错密计数为 `1`（保持 `ACTIVE` 不锁定）；全过程 `LOGIN/FAILED`（7 条）、`ACCOUNT_LOCKED`（1 条）、`MANUAL_HANDLING`（1 条）、`LOGIN/SUCCESS`（1 条）完整记录账号、时间、来源 IP、结构化 `detail`，且不含密码原值。 |
| **TC-002.S4** | 分别使认证服务异常、数据库异常后登录 | **P** | 认证组件异常（`LoginFaultResponseTest`）与隔离 TCP 代理断开模拟数据库不可达实测（`TC-002.S4-DB`）均返回 HTTP 500（`code: 1000`，message `"系统繁忙，请稍后重试"`），不建立会话、不泄露堆栈或 SQL 细节；代理重开恢复后登录立即恢复正常（颁发有效 Token）。 |

---

## 二、三大独立复测重点专项实证

### 1. 伪造与真实管理员权限篡改日志拦截验证（`NF016.TAMPER-HTTP` / `NF016.READ-VISIBILITY` / `NF016.STATIC-APPEND-ONLY`）
- **单条审计只读查询与可见性边界**：
  - `GET /api/v1/operation-logs/{id}`：系统管理员查询操作员记录返回 `200`；操作员查询自身记录返回 `200`；操作员越权查询管理员记录返回 `403`（`code: 2003`）并自动新增 1 条 `ACCESS_DENIED` 审计记录；查询不存在 ID（`999999999`）返回 `404`（`code: 3005`）。
- **6 类身份 × 5 个审计/事件端点 × 多种写方法全矩阵拦截（共 94 次请求，0 次放行）**：
  - 测试端点：`/api/v1/operation-logs`、`/api/v1/operation-logs/181`、`/api/v1/operation-logs/999999999`、`/api/v1/tasks/1/events`、`/api/v1/tasks/1/events/1`；
  - 真实系统管理员 Token（`realAdminToken`，19 次）与携带伪造管理员头的有效操作员 Token（`operatorTokenWithSpoofedAdminHeaders`，15 次）：发送 `PUT`、`DELETE`、`PATCH` 以及 `POST + X-HTTP-Method-Override: DELETE`、`POST ?_method=DELETE` 全部被严格拦截为 **HTTP `405 Method Not Allowed`**（`code: 3004`，响应头 `Allow: GET`，消息 `"该资源不支持PUT/DELETE/PATCH/POST方法（记录不可修改或删除）"`）；
  - 4 类伪造管理员凭据（`alg:none` 伪造管理员 JWT、随机伪造 Bearer、篡改签名的管理员 Token、无 Token 仅带 `X-Role: SYSTEM_ADMIN` 与伪造管理员 Cookie，共 60 次）：全部在认证过滤链被严格拦截为 **HTTP `401 Unauthorized`**（`code: 2000/2001`）。
- **静态持久层只读核查**：
  - 扫描 `OperationLogMapper.xml`、`TaskEventMapper.xml`、`DeviceEventMapper.xml` 及全量 Java 源码，针对 `operation_logs`、`task_events`、`device_events` 三张表的 `UPDATE` 与 `DELETE` 语句数为 **0**（仅定义 `INSERT` 与 `SELECT`）。

### 2. 数据库审计表 SHA-256 指纹零变动验证（`NF016.TAMPER-FINGERPRINT`）
- 在发起全部 94 次越权/篡改写请求前后，直接对 PostgreSQL 隔离库三张审计/事件表按 `id` 排序聚合整行文本计算 SHA-256 指纹：
  - `operation_logs`（187 行，`maxId=187`）：篡改前 `3695af7b73765b1e9792236996bbed0c27e80e9ff3a3dba132ea5bae53ee22ce` → 篡改后 `3695af7b73765b1e9792236996bbed0c27e80e9ff3a3dba132ea5bae53ee22ce`（**完全一致**）；
  - `task_events`（4 行，`maxId=4`）：篡改前 `19d7f3b96fc57607380a28998f6136359b96925a57182f5a4573243e9a337a33` → 篡改后 `19d7f3b96fc57607380a28998f6136359b96925a57182f5a4573243e9a337a33`（**完全一致**）；
  - `device_events`（1 行，`maxId=1`）：篡改前 `a7f9d05b1495e815b3b5d9e9a2971b605fa838634d1ef1f0378b354ad62057aa` → 篡改后 `a7f9d05b1495e815b3b5d9e9a2971b605fa838634d1ef1f0378b354ad62057aa`（**完全一致**）；
  - 被直接指定篡改的目标记录 `operation_logs.id=181` 单行 SHA-256：篡改前 `99ab3fe263566c0d5c25d2faab16eda12ea1a0b235fed1aa64262a70b5fc30ca` → 篡改后 `99ab3fe263566c0d5c25d2faab16eda12ea1a0b235fed1aa64262a70b5fc30ca`（**逐字节零改动**）。

### 3. 超长入参审计留痕完整性与防截断验证（`NF016.LONG-L1` ~ `LONG-L3` & 单测 12KB+ 载荷）
- **5,906 字符超长越权 URI 审计留痕（`NF016.LONG-L1`）**：
  - 操作员请求 5,906 字符路径 `/api/v1/users/<long-segment>` 返回 403（`code: 2003`）；
  - 数据库 `operation_logs`（`id=188`）中 `length(operation_target) = 5906`、`octet_length = 5906`，存储值 SHA-256 与原始请求 URI SHA-256 均为 `b0a850764d38f04ecd8bd08490995fe207061be1de3ff49b961f6a5f5455e714`；`detail` JSON 字段包含完整的 `["operationType", "result", "target"]`，其中 `detail.target` 长度同为 5,906 且与原值完全相等。
- **边界长度中文+Emoji 代理对、长端点、128 位凭据脱敏与 12KB 字段配置审计（`NF016.LONG-L2`）**：
  - 构造恰好 64 个 UTF-16 代码单元（含中文与 `✈🛫` / `🛃🛫` Emoji 代理对）的设备名称与任务定义名称、239 字符接入端点、128 位高熵凭据、500 个 UTF-16 代码单元含 `🛄` 的目标模板及 12KB 完成条件；
  - 65 位无效边界请求被 `@Size` 拦截返回 400（`code: 3001`）且未污染成功审计记录；64 位有效边界请求返回 200，`DEVICE_CREATE` 与 `TASK_DEFINITION_CREATE` 审计记录完整落库，中文与 Emoji 零截断、零 `\ufffd` 替换符乱码，`accessCredentialRef` 在 `detail` JSON 中已脱敏掩码，原始凭据零泄露。
- **32 位含 Emoji 登录账号边界审计（`NF016.LONG-L3`）**：
  - 32 个 UTF-16 代码单元含 `🛂` Emoji 的未知账号登录失败写入 `LOGIN/FAILED`，`username`、`operation_target` 与 `detail.target` 均与原输入逐字相等；33 位无效边界返回 400。
- **12KB+ 复杂嵌套 JSON 与长错误描述持久化（`AuditLogIntegrityAndTamperResistanceNF016Test`）**：
  - 10KB+ 超长目标与复杂多层嵌套 `Map.of`/`List.of`（含敏感凭据键与 Java 8 时间类型）落库 `operation_logs`、`task_events`、`device_events` 100% 完整保留、敏感键掩码生效、Unicode 代理对安全边界不切碎。

---

## 三、受控证据索引与协同收口

| 证据文件路径 | 说明 |
|---|---|
| `acceptance/stage3/evidence/SRS_NF016-V1.196-protocol-db-evidence-20261111T014646Z.json` | V1.196 独立整轮实测协议与数据库证据（TC-002.S1~S4、94 次篡改请求拦截、3 表 SHA-256 指纹对比、超长入参留痕完整性、零凭据泄露） |
| `acceptance/stage3/probe-nf016-v196.py` | SRS_NF016 V1.196 可重跑独立实测探针（含本地 TCP 数据库代理故障注入与恢复） |
| `backend/src/test/java/com/airport/ai/auth/AuditLogIntegrityAndTamperResistanceNF016Test.java` | V1.196 审计只读 405 拦截、长字段防截断与全生命周期留痕专项测试 |

- **验收裁决**：**REQUIREMENT_PASSED**
- **后续动作**：更新 `acceptance/stage3/rules.csv`、`acceptance/stage3/steps.csv`、`acceptance/stage3/阶段3-复测进度.md`、`docs/HANDOFF.md` 与 `docs/ROADMAP.md`，提交推送 `ai/gpt-test` 并安全合入 `main`。
