# SRS_NF004 跨域与接口防护（服务端逐接口鉴权、CORS 白名单、防 SQL 注入与 XSS 净化）整轮独立复测与验收报告

- **依据执行基线**：V2.4（继承 V2.3 / V2.2 全景规范与双 AI 串行协同约定）
- **固定产品版本**：`b51bae075653765a36739060bf33fd5737b4f7f9`（标签 `V1.195`）
- **测试执行工作区**：`C:/Users/savy/Desktop/TIP-main/tip-gpt-f013`
- **测试分支**：`ai/gpt-test`（接收并合入 `origin/ai/claude-fix` 交接提交 `7e484732661066d3f21dded526e603039a0b6eaa`）
- **复测结论**：**REQUIREMENT_PASSED（整项全量通过，无残留 F/NT）**
  - 业务规则核验：**1P / 0F / 0NT**（`SRS_NF004.R01` 实测满足预期）
  - 关联用例步骤核验：**7P / 0F / 0NT**（`TC-003.S1`、`TC-003.S2`、`TC-003.S3`、`TC-085.S1`、`TC-085.S2`、`TC-086.S1`、`TC-086.S2` 全部实测满足预期）
  - 专项安全与权限单测套件：**35/35 全部通过**（`CorsSqlInjectionAndXssSecurityTest` 6 项、`SecurityAccessControlAndSessionTest` 14 项、`UserAccessOrderTest` 4 项、`WriteEndpointAuthorizationOrderTest` 6 项、`AccountAuditDetailTest` 5 项，0 失败 0 错误）
  - 生产构建验证：后端生产 JAR（`airport-ai-app-1.0.0.jar`）与前端生产构建均通过。

---

## 一、规则与关联用例步骤核验全景

| 规则/步骤编号 | 关注核心点与判定准则 | 实测结果 | 关键判定依据与实测数据 |
|---|---|:---:|---|
| **SRS_NF004.R01** | 三类预置角色权限由服务端逐接口校验，不得只依赖前端菜单控制；登录、配置变更和人工终止写入操作记录；具备 CORS 跨域源控制、SQL 参数化防注入与 XSS 输入转义防护 | **P** | 1. 服务端逐接口 RBAC 校验：`SecurityConfig` + `PreAuthorizeInterceptor` 在请求体 `@Valid` 校验前先行校验角色权限，无权请求统一返回 HTTP 403（业务码 `2003`）并记入 `ACCESS_DENIED` 审计日志，业务数据零变更；<br/>2. CORS 源白名单防护：`CorsOriginSecurityFilter` 严格校验 `Origin`，放行受控本地/配置白名单源，拦截未知外部源预检 `OPTIONS` 与跨域写请求（HTTP 403 / code `2003`，不输出 `Access-Control-Allow-Origin` 头，已认证会话写 `ACCESS_DENIED` 审计）；<br/>3. 防 SQL 注入：全量 20 个 MyBatis XML Mapper 与 23 个 Java Mapper 接口 100% 使用 `#{}` 预编译参数化占位符（0 处 `${}` 拼接），`DeviceMapper.xml` 与 `TaskMapper.xml` 模糊查询均配置 `ESCAPE '\'` 与 `escapeLike` 通配符转义；<br/>4. XSS 输入净化：`XssSanitizer` 对任务定义、设备名称/备注、能力描述、模板名称/说明、任务目标与场景参数、用户姓名/联系方式、风险规则内容执行幂等 HTML 实体转义与伪协议脱敏；<br/>5. 关键操作留痕：登录、登出、设备/模板/定义/规则配置变更、人工终止、越权访问全量写入 `operation_logs` 且支持角色可见范围隔离。 |
| **TC-003.S1** | 三类角色登录并执行各自主要授权操作，查看菜单及按钮 | **P** | 系统管理员、配置管理员、运行操作员菜单隔离与授权操作符合权限矩阵，越权入口不显示。 |
| **TC-003.S2** | 绕过页面，使用无权角色分别请求账号修改、设备配置修改、任务提交/处置等代表性写操作 | **P** | `WriteEndpointAuthorizationOrderTest` 与 `UserAccessOrderTest` 实测确认无权角色无论提交有效体或空/缺字段体均优先返回 HTTP 403（`code: 2003`），写入 `ACCESS_DENIED` 审计，目标表计数不变。 |
| **TC-003.S3** | 非管理员请求全量操作记录；核对登录、配置、终止及越权记录 | **P** | 非管理员（配置管理员、运行操作员）查询操作记录仅返回自身相关记录，系统管理员可见全量；登录、配置变更、人工终止及越权访问（含跨域拦截审计）均完整留痕。 |
| **TC-085.S1~S2** | 操作记录筛选、变更前后结构化摘要、不可篡改与角色可见范围 | **P** | `AccountAuditDetailTest` 5/5 通过，变更前后 `before`/`after` 摘要完整，凭据脱敏无泄露，只读防篡改生效。 |
| **TC-086.S1~S2** | 密码加盐不可逆摘要、敏感凭据掩码与会话/越权防护一致性 | **P** | `SecurityAccessControlAndSessionTest` 14/14 通过，BCrypt 哈希存储、零凭据回显、状态变更联动会话失效与越权 403 留痕一致。 |

---

## 二、三大安全防护维度专项核验实证

### 1. SQL 参数化预编译与通配符安全转义核验
- **静态全量扫描**：
  - 扫描 `backend/src/main/resources/mapper/*.xml` 全部 20 个 XML 映射文件与 `backend/src/main/java` 下全部 23 个 `*Mapper.java` 接口；
  - 证实全库 `${}` 字符串拼接数为 **0**，全部 SQL 参数（超过 140 处）100% 采用 MyBatis `#{}` `PreparedStatement` 参数化绑定；
  - `DeviceMapper.xml` 与 `TaskMapper.xml` 的 `LIKE` / `ILIKE` 子句均显式声明 `ESCAPE '\'`。
- **运行期参数化与转义验证**：
  - 在 `DeviceService.list` 与 `TaskService.list` 中传入包含特殊字符与 SQL 关键字的检索词，验证服务层先将 `\`、`%`、`_` 安全转义为 `\\`、`\%`、`\_`，再通过 `#{}` 预编译参数传递，不改变 SQL 语法树结构，数据库表结构与业务数据完全无损。

### 2. XSS 输入净化与前端安全转义核验
- **后端输入净化（`XssSanitizer`）**：
  - `XssSanitizer.escapeHtml` 对 `<`、`>`、`"`、`'`、`&` 执行幂等 HTML 实体转义（重复调用不产生 `&amp;lt;` 双重转义），并对 `javascript:`、`vbscript:` 伪协议转换为 `&#58;`；
  - `XssSanitizer.sanitizeRichText` 在保留普通业务符号（如 `区域A->区域B`）的同时，对 HTML 标签、事件属性及脚本协议执行转义；
  - 实测覆盖 `TaskDefinitionService`、`DeviceService`、`DeviceCapabilityService`、`DeviceTypeCapabilityService`、`BaselineTemplateService`、`SceneParamsPrivacyGuard`、`UserService`、`RiskRuleController` 全量可展示文本字段，确保存储与回显内容不含可执行脚本标签。
- **前端模板转义**：
  - 前端 Vue 3 组件统一采用 `{{ }}` 文本插值与 Ant Design Vue 标准表格列渲染，不渲染未受信 HTML，实现前后端双重转义防护。

### 3. CORS 跨域源白名单与非授权外部源写操作拦截核验
- **过滤器链时序与白名单规则（`CorsOriginSecurityFilter`）**：
  - 位于 `TokenAuthenticationFilter` 之后、`AuthorizationFilter` 之前；
  - 严格采用 `URI` 解析校验 `Origin` 协议、主机与端口：白名单源（`http://localhost:5173`、`http://127.0.0.1:*` 等）的 `OPTIONS` 预检与业务请求正常返回 `Access-Control-Allow-Origin` 与 `Access-Control-Allow-Credentials: true`；
  - 非白名单外部源（含未知外部域名、子域名前缀欺骗、`null`、`*`、非 HTTP/HTTPS 协议）发起的 `OPTIONS` 预检与 `POST`/`PUT`/`DELETE` 写请求一律被拦截并返回 HTTP `403 Forbidden`（`code: 2003`），响应头不含 `Access-Control-Allow-Origin`，目标业务 Service 零调用、数据库零副作用，且在已认证上下文下自动记录 `ACCESS_DENIED / FAILED` 操作审计日志。

---

## 三、受控证据索引与协同收口

| 证据文件路径 | 说明 |
|---|---|
| `acceptance/stage3/evidence/SRS_NF004-V1.195-security-verification-20261110.json` | V1.195 服务端逐接口 RBAC、CORS 白名单拦截、MyBatis 参数化防注入与 XSS 输入净化综合复测证据 |
| `acceptance/stage3/evidence/TC-003-valid-denials.json` | 跨角色未授权写操作 403 拦截与数据零变更证据 |
| `acceptance/stage3/evidence/TC-003-audit-scope.json` | 三类预置角色操作日志可见范围隔离与关键操作留痕证据 |
| `acceptance/stage3/evidence/SRS_F001-V1.110-live-api-audit-expanded-20261029.json` | 服务端权限校验优先于请求体校验（403 先于 400）及越权留痕证据 |

- **验收裁决**：**REQUIREMENT_PASSED**
- **后续动作**：更新 `acceptance/stage3/rules.csv`、`acceptance/stage3/steps.csv`、`acceptance/stage3/阶段3-复测进度.md`、`docs/HANDOFF.md` 与 `docs/ROADMAP.md`，提交推送 `ai/gpt-test` 并合入 `main`。
