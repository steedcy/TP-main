# SRS_NF001 系统安全性（认证与权限） 整轮独立复测与验收报告

- **依据执行基线**：V2.4（继承 V2.3 / V2.2 全景规范与双 AI 串行协同约定）
- **固定产品版本**：`0e16b31dc2c01e965f8848897940c2885b1ba99a`（标签 `V1.190`）
- **测试执行工作区**：`C:/Users/savy/Desktop/TIP-main/tip-gpt-f013`
- **测试分支**：`ai/gpt-test`（由 `READY_FOR_GPT` 交接提交 `3f1caed` 同步）
- **独立复测环境**：
  - PostgreSQL 独立 Schema：`tip_gpt_f006_v118_20261030`（严格与生产及默认数据库隔离）
  - Redis 独立 DB：`11`
  - 后端服务端口：`18130`
  - 前端代理端口：`15180`
  - 生产打包可执行文件：`backend/target/airport-ai-app-1.0.0.jar`
- **复测结论**：**REQUIREMENT_PASSED（整项全量通过，无残留 F/NT）**
  - 业务规则核验：**1P / 0F / 0NT**（`SRS_NF001.R01` 实测满足预期）
  - 测试用例核验：**2P / 0F / 0NT**（`TC-086.S1`、`TC-086.S2` 实测满足预期）
  - 缺陷彻底闭环：**DEF-S3-010 彻底关闭**（`GET /api/v1/users`、`POST /api/v1/users` 响应体及 JSON 序列化严格不含 `passwordHash` 或明文凭据）
  - 前置缺口闭环：**NT-S3-009 彻底闭环**（全链路覆盖越权写操作拦截、参数校验优先时序、Token 防伪防篡改、账号停用/密码重置/登出联动活跃 Token 即时失效）
  - 真实 Edge 浏览器 UI 实测：**3/3 全部通过**（管理员用户管理脱敏核查、操作员菜单与路由隔离及浏览器内越权拦截、登出重定向与后退阻断）

---

## 一、复测执行全景与核心指标

| 规则/步骤编号 | 关注核心点与判定准则 | 实测结果 | 关键判定依据与实测数据 |
|---|---|:---:|---|
| **SRS_NF001.R01** | 密码加盐不可逆摘要保存；敏感凭据不回显，数据库与日志严禁明文密码或凭据 | **P** | 1. 数据库核查：测试库 14 个账号的 `password_hash` 字段 100% 为合法 BCrypt 哈希（`$2a$` / `$2b$` 开头，长度 60），0 处明文密码泄露；<br/>2. 接口脱敏：`GET /api/v1/users`、`POST /api/v1/users` 响应 100% 不含 `passwordHash`（**DEF-S3-010 彻底关闭**）；<br/>3. 设备接入凭据以掩码形式回显（`accessCredentialRefMasked`），无明文 token；<br/>4. 日志脱敏：全量核查 908 条 `operation_logs.detail`，0 处敏感密码暴露。 |
| **TC-086.S1** | 查看测试账号密码保存方式及登录日志；重新打开设备接入参数及操作追溯详情 | **P** | 实测数据库密码哈希符合 BCrypt 标准；登录、修改密码、重置密码操作记录均不含明文凭据；设备列表与详情中接入凭据掩码回显且无原值入口；真实 Edge 浏览器 DOM 审查与网络捕获均无凭据泄露。 |
| **TC-086.S2** | 核对与功能登录、设备配置、审计用例的证据，覆盖越权与状态变更分支 | **P** | **NT-S3-009 彻底闭环**。实测覆盖未带 Token（401/2000）、篡改伪造 Token（401/2001）；操作员/配置管理员调用受限写接口统一被拦截为 403 Forbidden（错误码 2003）且记入 `ACCESS_DENIED` 审计日志；账号停用（`INACTIVE`）和密码重置（`resetPassword`）后原有 Token 立即失效（401），绝无越权修改生效。 |

---

## 二、DEF-S3-010 彻底关闭验证实证

### 1. 历史缺陷现象（DEF-S3-010）
历史版本中，管理员调用 `GET /api/v1/users` 查询用户列表时，响应体包含 `passwordHash` 字段，虽然并非明文密码，但向客户端暴露了密码哈希摘要，存在安全隐患。

### 2. V1.190 修复加固手段
- 在 `User.java` 实体类的 `getPasswordHash()` getter 上标注 `@com.fasterxml.jackson.annotation.JsonIgnore`，同时重写 `toString()` 彻底剔除密码哈希；
- 加固 `CredentialMasker.java`，扩大敏感凭据识别范围，支持嵌套结构递归脱敏。

### 3. 本轮独立复测实测数据
1. **用户列表接口 (`GET /api/v1/users`)**：
   - 检索返回的 14 个用户实体对象，逐一遍历其键值：
   - `passwordHash` 键存在率：**0% (0/14)**；
   - `password` 键存在率：**0% (0/14)**；
   - 证明接口传输已彻底消除哈希与凭据暴露。
2. **用户创建接口 (`POST /api/v1/users`)**：
   - 创建测试账号 `test_sec_user_*`，返回的 `User` 视图对象同样 **100% 不含 `passwordHash`**。
3. **真实 Edge 浏览器 DOM 与网络包核验**：
   - 监听网络面板，捕获 `/api/v1/users` 的真实 JSON 响应，解析证实 `passwordHash` 不存在；
   - 审查页面表格 DOM 文本，证实无任何 `$2a$` 或 `$2b$` 开头的哈希字符串。
   - **裁决结论**：**DEF-S3-010 彻底关闭**。

---

## 三、NT-S3-009 彻底闭环实证（越权防护与会话安全拦截）

### 1. 跨角色越权写操作严格拦截与留痕
- **测试场景 1（操作员尝试创建用户）**：
  - 操作员发起 `POST /api/v1/users`：
  - 响应状态码：`403 Forbidden`，业务错误码：`2003`；
  - 数据库核查：`SELECT COUNT(*) FROM users WHERE username = 'hacked_user_*'`，结果严格为 `0`；
- **测试场景 2（操作员尝试停用用户）**：
  - 操作员发起 `POST /api/v1/users/{id}/status`：
  - 响应状态码：`403 Forbidden`，业务错误码：`2003`；
- **测试场景 3（配置管理员尝试创建用户）**：
  - 配置管理员发起 `POST /api/v1/users`：
  - 响应状态码：`403 Forbidden`，业务错误码：`2003`；
- **测试场景 4（操作员尝试创建设备）**：
  - 操作员发起 `POST /api/v1/devices`：
  - 响应状态码：`403 Forbidden`，业务错误码：`2003`；
- **测试场景 5（拦截时序优先于参数校验）**：
  - 操作员发送空请求体 `{}` 发起 `POST /api/v1/users`：
  - 响应状态码：`403 Forbidden`，业务错误码：`2003`；
  - **证实**：未授权角色发起写请求优先被 Spring Security 过滤器链与 `PreAuthorizeInterceptor` 拦截，杜绝被参数绑定与 `@Valid` 校验提前误判为 400 Bad Request！
- **测试场景 6（越权访问留痕）**：
  - 查询数据库 `operation_logs` 表，成功捕获多条 `operation_type = 'ACCESS_DENIED'` 的审计日志，记录包含操作人 ID、用户名、角色、端点 URI 及来源 IP。

### 2. 会话时效、伪造拦截与即时失效联动
- **Token 防伪防篡改**：
  - 未携带 Token 请求：返回 `401 Unauthorized`（code: `2000`）；
  - 携带空白 Token `Bearer `：返回 `401 Unauthorized`；
  - 携带伪造/篡改签名 Token：返回 `401 Unauthorized`（code: `2001`）；
- **账号状态停用联动失效**：
  - 登录新建用户获取合法会话 Token A，调用受保护业务接口成功（200）；
  - 管理员将该用户状态置为 `INACTIVE`；
  - 立即使用 Token A 请求业务接口：**即时被拦截为 401 Unauthorized**，会话被立即终止；
- **密码重置联动即时失效**：
  - 激活该用户并重新登录获取 Token B，调用业务接口成功（200）；
  - 管理员调用重置密码接口重置其密码为 `BrandNewPass#888`；
  - 立即使用重置前的 Token B 请求业务接口：**即时被拦截为 401 Unauthorized**（SessionService 集合反查索引清空了活跃会话）；
  - 使用新密码登录成功获取 Token C，接口调用恢复正常；
- **主动登出即时失效**：
  - 调用 `POST /api/v1/auth/logout` 登出；
  - 原 Token C 立即失效，再次调用接口返回 `401 Unauthorized`。
  - **裁决结论**：**NT-S3-009 彻底闭环**。

---

## 四、真实 Edge 浏览器 UI 端到端验证实证

本轮复测使用真实 Microsoft Edge 无头浏览器（`msedge.exe`），通过 Playwright 驱动执行端到端全链路操作，执行结果记录于 `acceptance/stage3/evidence/SRS_NF001-V1.190-real-ui-results.json`：

1. **场景 1：管理员用户管理界面与网络脱敏审查**
   - 登录 `admin` / `cares0126`，访问 `/users` 用户管理界面；
   - 验证表格数据正常渲染，DOM 及网络请求中密码与哈希零泄露（`responseExposesHash: false, domExposesBcrypt: false`）；
   - **截图证据**：`acceptance/stage3/evidence/SRS_NF001-V1.190-ui-admin-users.png`。
2. **场景 2：操作员角色隔离与越权阻断实测**
   - 登录 `oprator` / `12345678`，访问系统；
   - 侧边栏菜单中无“用户管理”选项；
   - 尝试通过浏览器直接访问 `/users` URL，前端路由守卫安全拦截并重定向到 `/overview`；
   - 在页面控制台发起真实 `fetch('/api/v1/users', ...)` 越权创建，服务端返回 403（code: 2003）；
   - **截图证据**：`acceptance/stage3/evidence/SRS_NF001-V1.190-ui-operator-restricted.png`。
3. **场景 3：会话注销阻断与安全退出重定向**
   - 执行退出登录，前端清除会话并安全重定向至 `/login` 登录页；
   - 触发浏览器后退导航（`page.goBack()`），路由守卫拦截并阻断回跳，保持在 `/login`；
   - **截图证据**：`acceptance/stage3/evidence/SRS_NF001-V1.190-ui-logout-redirect.png`。

---

## 五、受控证据文件索引与校验

| 证据文件路径 | 文件说明与实测核心内容 |
|---|---|
| `acceptance/stage3/evidence/TC-086-sensitive.json` | 敏感凭据脱敏与存储核验历史对照受控证据（`userListExposesPasswordHash: false`，`defS3010Closed: true`，`ntS3009Closed: true`） |
| `acceptance/stage3/evidence/SRS_NF001-V1.190-protocol-summary.json` | 协议层、数据库存储、越权拦截、时序校验、会话联动失效与全量日志脱敏完整汇总证据 |
| `acceptance/stage3/evidence/SRS_NF001-V1.190-real-ui-results.json` | 真实 Edge 浏览器 UI 自动化实测结果 JSON（3/3 全部 PASSED） |
| `acceptance/stage3/evidence/SRS_NF001-V1.190-ui-admin-users.png` | 真实 Edge UI 管理员用户列表无敏感信息脱敏截图 |
| `acceptance/stage3/evidence/SRS_NF001-V1.190-ui-operator-restricted.png` | 真实 Edge UI 操作员菜单隔离与越权阻断截图 |
| `acceptance/stage3/evidence/SRS_NF001-V1.190-ui-logout-redirect.png` | 真实 Edge UI 登出安全重定向与后退阻断截图 |

---

## 六、整体验收裁决

- 业务规则：**SRS_NF001.R01 (P)**
- 测试用例：**TC-086.S1 (P)**、**TC-086.S2 (P)**
- 缺陷与缺口：**DEF-S3-010 (彻底关闭)**、**NT-S3-009 (彻底闭环)**
- 验收裁决：**REQUIREMENT_PASSED（全量实测满足预期，整项通过）**
- **后续协同**：
  1. 依据 V2.4 规范，`ai/gpt-test` 分支合入 `main` 并推送到远端；
  2. 交接文档 `docs/HANDOFF.md` 与路标 `docs/ROADMAP.md` 同步更新；
  3. 顺序推进下一项非功能需求：`SRS_NF002`（会话与数据完整性）。
