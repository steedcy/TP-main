# SRS_NF003 旅客个人身份隐私保护 整轮独立复测与验收报告

- **依据执行基线**：V2.4（继承 V2.3 / V2.2 全景规范与双 AI 串行协同约定）
- **固定产品版本**：`443ccbd1b28de9971affe6253f3b80652f8fd132`（标签 `V1.191`）
- **测试执行工作区**：`C:/Users/savy/Desktop/TIP-main/tip-gpt-f013`
- **测试分支**：`ai/gpt-test`（合并 `READY_FOR_GPT` 交接分支 `origin/ai/claude-fix` 提交 `aa5a29a`）
- **独立复测环境**：
  - PostgreSQL 独立 Schema：`tip_gpt_f006_v118_20261030`（严格与生产及默认数据库隔离）
  - Redis 独立 DB：`11`
  - 后端服务端口：`18129`
  - 前端代理端口：`15179`
  - 受控规划模型端口：`18117`
  - 生产打包可执行文件：`backend/target/airport-ai-app-1.0.0.jar`
- **复测结论**：**REQUIREMENT_PASSED（整项全量通过，无残留 F/NT）**
  - 业务规则核验：**1P / 0F / 0NT**（`SRS_NF003.R01` 实测满足预期）
  - 测试用例核验：**6P / 0F / 0NT**（`TC-031.S2`、`TC-077.S1`、`TC-077.S2`、`TC-077.S3`、`TC-086.S1`、`TC-086.S2` 全部实测满足预期）
  - 缺陷彻底闭环：**DEF-S3-032 彻底关闭（CLOSED）**
  - 敏感泄露扫描：**外部大模型交互日志 0 处泄露，全库 7 张表 0 处真实个人敏感信息落库**；
  - 业务代码放行：**航班号（CA1234 等）、行李编号（BAG-123456 等）、区域代号等合法业务标识 100% 安全放行，零误拒**；
  - 真实 Edge 浏览器 UI 实测：**3/3 全部通过**（敏感参数拦截与前端 Ant Design Toast 提示、任务详情页掩码脱敏渲染、操作员任务管理主页）。

---

## 一、复测执行全景与核心指标

| 规则/步骤编号 | 关注核心点与判定准则 | 实测结果 | 关键判定依据与实测数据 |
|---|---|:---:|---|
| **SRS_NF003.R01** | 不保存旅客真实身份信息，演示使用虚构或脱敏数据；提交给规划模型的内容须脱敏 | **P** | 1. 场景参数守卫（`SceneParamsPrivacyGuard.reject`）对顶层及任意多层嵌套的敏感字段（姓名、18位身份证号、护照号、手机号、邮箱等）严格执行 HTTP 400 拦截；<br/>2. 自然语言任务目标自动执行递归脱敏（转换为 `[PROTECTED_IDENTITY]`、`[PROTECTED_ID]`、`[PROTECTED_PHONE]` 等）；<br/>3. 大模型交互请求 Prompt 统一经脱敏处理，11 次外部交互 0 处泄露；<br/>4. 全库 7 张表深度扫描：累计 0 处敏感个人信息落库；<br/>5. **彻底关闭历史高危缺陷 DEF-S3-032**。 |
| **TC-031.S2** | 查看解析和原始目标，完整后进入上下文构建；只保存必要协助信息，不保存真实身份 | **P** | 实测超规行李及特殊旅客目标提交中，额外注入顶层与嵌套旅客姓名、证件号均被拦截为 HTTP 400，任务创建数增加 0；自然语言目标中的敏感信息在 `Task`、`TaskEvent`、`OperationLog` 及 `TaskView` 中均受掩码保护。 |
| **TC-077.S1~S3** | 特殊旅客补充、会合及陪同闭环；只存必要协助信息，不存真实身份；追问与执行闭环 | **P** | 1. `TC-077.S1`：缺少起点时生成待补充问题，特殊旅客流程禁止向旅客索取身份信息；<br/>2. `TC-077.S2`：澄清接口对注入身份键名返回 400 拦截，自由文本补充答案自动脱敏存储；<br/>3. `TC-077.S3`：任务生命周期全过程（提交、澄清、取消、事件详情）不泄露任何明文旅客身份。 |
| **TC-086.S1~S2** | 密码和敏感凭据与个人身份信息保护；核对数据库、日志与视图出参一致性 | **P** | 跨模块核验认证日志、任务事件、操作审计及数据库持久化：密码 100% 加盐哈希，个人身份信息 0 处泄露，所有出参接口严格脱敏。 |

---

## 二、DEF-S3-032 彻底关闭验证实证

### 1. 历史缺陷现象（DEF-S3-032）
- 历史版本（V1.135 之前）中，向任务 `sceneParams` 提交 `passengerName`、`identityDocumentNumber` 等纯虚构哨兵字段时，后端未做校验直接建任务并原样持久化到数据库；
- V1.135 仅校验了 `sceneParams` 顶层键名，当哨兵放置于嵌套结构（如 `sceneParams.metadata.passengerName`）或 JSON 文本内时，仍然成功创建任务并落库、发送至大模型；
- 澄清补充接口（`/clarify`）、行李测量事件（`/measurement-event`）同样存在穿透漏洞。

### 2. V1.191 核心加固手段
- **全深度递归拦截**：在 `SceneParamsPrivacyGuard.reject` 中采用 `ObjectMapper.valueToTree` 将场景参数转换为 JSON AST 树，递归扫描顶层及任意深度嵌套的 Map、List、JSON 文本对象；一旦发现命中身份键名或值内包含中英文姓名/身份证号/手机号/护照号，立即抛出 `BusinessException(ErrorCode.PARAM_FORMAT_ERROR)`（HTTP 400），快速失败拒绝建任务；
- **全链路出入库脱敏**：
  - 任务目标入口、出参视图（`TaskView`）、任务事件（`TaskEvent`）、审计日志（`OperationLog`）、任务生命周期处置原因（取消/终止/失败/降级原因）全方位接入脱敏；
  - 外部大模型请求（`MoonshotChatClient`）发送前统一执行脱敏防线；
- **业务标识白名单保护**：精确界定业务临时编号（`BAG-*`、`P-R08-OVERSIZE`、`TEMP-*`）和航班号（`CA1234`、`MU5182` 等），杜绝贪婪误杀与误拒。

### 3. 本轮独立复测实测数据
1. **参数注入与强拦截实测（Check 1，19/19 全部 400 拦截）**：
   - 顶层字段：`passengerName`、`identityDocumentNumber`、`phone`、`idCard`、`passport`、`email`、`旅客姓名`、`身份证号`、`手机号` 均返回 HTTP 400（错误码 3001）；
   - 嵌套 Map：`{"metadata": {"passengerName": "李四"}}`、`{"level1": {"level2": {"level3": {"idCardNumber": "..."}}}}` 均返回 HTTP 400；
   - 嵌套 List：`{"passengers": [{"passengerName": "王五"}]}`、`{"contacts": [{"phone": "..."}]}` 均返回 HTTP 400；
   - 嵌套 JSON 串：`{"extraJson": "{\"mobile\":\"13800138000\"}"}` 均返回 HTTP 400；
   - 字段值含身份文本：`{"remark": "旅客姓名: 张三"}`、`{"idInfo": "身份证: ..."}` 均返回 HTTP 400；
   - **拦截前后任务数核验**：初始任务数 1349，19 项拦截测试后任务数依然为 1349，违规建任务数严格为 **0**。
2. **行李测量事件接口实测（Check 2，3/3 全部 400 拦截）**：
   - `extraParams` 包含 `passengerName`、嵌套 `contactPhone` 及 `handlingInstructions` 包含身份文本均返回 HTTP 400。
3. **任务澄清接口实测（Check 3，全部拦截或脱敏）**：
   - 回答键名为敏感身份字段返回 HTTP 400；
   - 自由文本补充包含身份敏感信息时，接口接受并自动脱敏，数据库中 `scene_params` 仅保存脱敏后内容。

---

## 三、大模型交互日志与数据库全库深度审计（Check 6）

### 1. 外部大模型交互日志审计
- 通过独立受控模型 Mock 服务（端口 18117）对发送到大模型端点（`/v1/goal/understand`、`/v1/planning/generate`）的请求报文进行逐包落地与审查（文件 `.local-test/model-requests-nf003.jsonl`）；
- 复测期间共捕获 **11 次** 大模型交互请求；
- 对捕获的所有请求报文全文检索虚构哨兵（姓名、身份证号、手机号、护照号、邮箱）：
  - **敏感个人信息外发泄露数：0**；
  - 任务目标均以 `[PROTECTED_IDENTITY]`、`[PROTECTED_ID]` 等形式脱敏上送。

### 2. 数据库全库全表深度扫描（0 处敏感信息落库）
- 扫描隔离 Schema `tip_gpt_f006_v118_20261030` 下全部核心数据表的所有文本/字符/JSON 字段：
  - `tasks`（11 个字段）
  - `task_events`（7 个字段）
  - `operation_logs`（7 个字段）
  - `plan_versions`（11 个字段）
  - `context_snapshots`（4 个字段）
  - `task_exceptions`（7 个字段）
  - `users`（8 个字段）
- 逐字段扫描所有注入的旅客姓名、18位身份证号、手机号、护照号、邮箱：
  - **全库累计落库泄漏数：0 处**；
  - 严格证明系统各持久化链路均不保存真实旅客个人身份信息。

---

## 四、合法业务编号安全放行验证（Check 5，零误拒）

复测覆盖了 6 类常见合法业务输入，全部成功创建任务（HTTP 200，新增任务 ID 1362～1367）：
1. 航班号 `CA1234`：`{"flightNumber": "CA1234", "targetLocation": "F2_TEST_GATE"}` -> 成功；
2. 航班号 `MU5182`：`{"flightNumber": "MU5182", "gate": "F2_ZONE_A"}` -> 成功；
3. 超规行李临时编号 `BAG-123456` -> 成功；
4. 超规行李规格编号 `P-R08-OVERSIZE` -> 成功；
5. 预置区域代号 `F2_TEST_GATE`、`F2_ZONE_B` 与临时代码 `TEMP-2026-001` -> 成功；
6. 轮椅协助业务目标与类型 `WHEELCHAIR` -> 成功。
证明隐私防护规则未对正常业务代号产生误拦截或误脱敏。

---

## 五、真实 Edge 浏览器 UI 实测

使用 Playwright 驱动真实 Microsoft Edge 浏览器（无头模式）访问前端代理（端口 15179），执行 3 项全流程测试：

1. **UI-1: 操作员登录与任务管理主页**
   - 操作员 `oprator` 成功登录，跳转 `/tasks` 页面，任务表格与操作按钮正常渲染；
   - 截图存证：`acceptance/stage3/evidence/SRS_NF003-V1.191-ui-operator-tasks.png`。
2. **UI-2: 敏感参数注入拦截与前端错误提示弹窗（DEF-S3-032 闭环核验）**
   - 提交包含 `passengerName`、`idCard` 的任务请求，接口强拦截返回 400，前端弹出 Ant Design 错误提示：`"场景参数不得包含旅客身份信息字段: idCard、passengerName"`；
   - 截图存证：`acceptance/stage3/evidence/SRS_NF003-V1.191-ui-submit-interception.png`。
3. **UI-3: 任务目标自然语言脱敏与详情页安全渲染**
   - 输入包含姓名、18位身份证、手机号的自然语言目标，任务成功创建（Task ID 1368）；
   - 前端自动跳转任务详情页 `/tasks/1368`，页面 DOM 文本审查：
     - `leaksName`: false
     - `leaksId`: false
     - `leaksPhone`: false
     - `hasProtectedMask`: true（正常渲染 `[PROTECTED_IDENTITY]`）
   - 证明前端视图展示层严格保护旅客隐私，无明文泄露；
   - 截图存证：`acceptance/stage3/evidence/SRS_NF003-V1.191-ui-task-detail-masked.png`。

---

## 六、台账与版本控制归档

- **规则台账更新 (`acceptance/stage3/rules.csv`)**：
  - `SRS_NF003.R01` 由 `F` 更新为 `P`，验证用例关联至 `TC-031.S2;TC-077.S1;TC-077.S2;TC-077.S3;TC-086.S1;TC-086.S2`，缺陷关联清空；
- **缺陷台账更新 (`acceptance/stage3/issues.csv`)**：
  - `DEF-S3-032` 状态正式更新为 `CLOSED V1.191`，关闭依据记录完备；
- **步骤台账更新 (`acceptance/stage3/steps.csv`)**：
  - 更新 `TC-031.S2` 登记 V1.191 复测结论与闭环记录；
- **受控测试证据归档**：
  - 协议与数据库复测报告：`acceptance/stage3/evidence/SRS_NF003-V1.191-protocol-summary.json`
  - 真实 Edge UI 自动化结果：`acceptance/stage3/evidence/SRS_NF003-V1.191-real-ui-results.json`
  - 真实 Edge 浏览器实测截图：
    - `acceptance/stage3/evidence/SRS_NF003-V1.191-ui-operator-tasks.png`
    - `acceptance/stage3/evidence/SRS_NF003-V1.191-ui-submit-interception.png`
    - `acceptance/stage3/evidence/SRS_NF003-V1.191-ui-task-detail-masked.png`
- **后续协同**：SRS_NF003 验收全部通过，将 `ai/gpt-test` 分支合并至 `main` 并推送到 origin；更新交接文件至 `REQUIREMENT_PASSED`。
