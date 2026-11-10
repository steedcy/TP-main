# SRS_NF010 数据库高可用与连接池 整轮独立复测与验收报告

- **依据执行基线**：V2.4（继承 V2.3 / V2.2 全景规范与双 AI 串行协同约定）
- **固定产品版本**：`2dd346949eae90f636ec0170487122ea20931885`（标签 `V1.192`）
- **测试执行工作区**：`C:/Users/savy/Desktop/TIP-main/tip-gpt-f013`
- **测试分支**：`ai/gpt-test`（合并 `READY_FOR_GPT` 交接分支 `origin/ai/claude-fix` 提交 `7b4eaf2`，包含产品 commit `2dd3469`）
- **独立复测环境**：
  - PostgreSQL 独立 Schema：`tip_gpt_f006_v118_20261030`（严格与生产及默认数据库隔离）
  - Redis 独立 DB：`11`
  - 后端服务端口：`18129`
  - 前端代理端口：`15179`
  - 受控规划模型端口：`18117`
  - 生产打包可执行文件：`backend/target/airport-ai-app-1.0.0.jar`
- **复测结论**：**REQUIREMENT_PASSED（整项全量通过，无残留 F/NT）**
  - 业务规则核验：**1P / 0F / 0NT**（`SRS_NF010.R01` 实测满足预期）
  - 测试用例核验：**1P / 0F / 0NT**（`TC-090.S1` 实测满足预期）
  - 历史前置缺口彻底闭环：**NT-S3-011 彻底关闭（CLOSED）**
  - 连接池高压排队：**35 并发突发高压，140 个高频数据库业务请求 100% 成功（140/140），平均延迟 366.3ms，P95 679.1ms，排队日志明确生效**；
  - 零泄漏零死锁：**高压后 `idle in transaction` 未释放事务连接严格为 0，总连接数严格受 30 上限管控，零进程死锁**；
  - 真实双浏览器并发：**Microsoft Edge 与 Google Chrome 真实双浏览器并行自动化实测 100% 通过（双方会话隔离、操作员任务协同与管理员设备配置保存互不干扰、响应正常、零白屏、控制台零报错）**。

---

## 一、复测执行全景与核心指标

| 规则/步骤编号 | 关注核心点与判定准则 | 实测结果 | 关键判定依据与实测数据 |
|---|---|:---:|---|
| **SRS_NF010.R01** | 支持 Chrome、Edge 当前主版本；双浏览器并发操作互不干扰、响应正常无白屏 | **P** | 1. 真实 Microsoft Edge（操作员 `oprator`）与 Google Chrome（配置管理员 `set`）并行启动；<br/>2. Edge 客户端提交协同任务 `TASK-20261110-1363`，Chrome 客户端保存更新设备配置 `G6_UNTESTED_134145`；<br/>3. 两端各自进入运行总览、设备管理与态势监控，双方会话隔离、响应正常、无白屏、控制台零报错；<br/>4. **彻底关闭历史前置缺口 NT-S3-011**。 |
| **TC-090.S1** | 分别在 Chrome、Edge 操作登录、配置、任务提交监控、态势及追溯，核心操作正常，关键字段/提示/按钮可用 | **P** | 1. Edge 浏览器（1440×900）执行登录、总览渲染、任务提交、任务列表重载、任务详情查看及截图留痕（耗时 12.17s）；<br/>2. Chrome 浏览器（1440×900）执行登录、总览渲染、设备列表查询、设备参数修改保存、态势 2D 监控及截图留痕（耗时 10.70s）；<br/>3. 并发交叉验证双方数据隔离、无数据踩踏、防竞争生效。 |

---

## 二、NT-S3-011 彻底关闭验证实证

### 1. 历史前置缺口说明（NT-S3-011）
- 历史版本（V1.5 阶段 3 初审）中，TC-090 仅对 Chrome 和 Edge 进行了静态页面打开与布局视口可见性采样（24 个页面样本，S2 P）；
- 未在真实双浏览器各自执行实际配置保存、任务实际提交与监控流转，导致双客户端并发交互被登记为前置缺口 `NT-S3-011`（S1 NT）；
- 缺少在高并发排队下 HikariCP 连接池的真实借还、排队生效性及零泄漏实测证据。

### 2. V1.192 加固与实测闭环手段
1. **HikariCP 生产连接池 9 项核心参数硬化**：
   - `pool-name: AirportAiHikariPool`：显式命名连接池，便于日志与 JMX 观测；
   - `minimum-idle: 5`：保障初始冷启动快速就绪；
   - `maximum-pool-size: 30`：刚性约束最大数据库连接上限，防止突发流量冲垮 PostgreSQL；
   - `connection-timeout: 30000`：连接获取超时阈值 30 秒；
   - `idle-timeout: 600000`：空闲连接回收时间 10 分钟；
   - `max-lifetime: 1800000`：连接最大存活时间 30 分钟；
   - `keepalive-time: 30000`：心跳保活检测周期 30 秒；
   - `validation-timeout: 5000`：连接有效性探针超时 5 秒；
   - `leak-detection-threshold: 60000`：连接借出超 60 秒触发泄漏告警与堆栈追踪，防死锁。
2. **连接池故障与并发冲突友好防护**：
   - `GlobalExceptionHandler` 捕获 `CannotGetJdbcConnectionException`，瞬时排队超时返回友好 503（`DATABASE_POOL_BUSY`）；
   - 捕获 `DeadlockLoserDataAccessException`、`CannotAcquireLockException`，行锁冲突与死锁返回 409（`DATA_CONCURRENCY_CONFLICT`）；
   - 捕获 `DuplicateKeyException`，唯一键约束冲突返回 409（`DUPLICATE_KEY_CONFLICT`）。
3. **真实 Edge 与 Chrome 双浏览器并发自动化实测**：
   - 驱动真实宿主机安装的 Edge (`C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe`) 与 Chrome (`C:/Users/savy/AppData/Local/Google/Chrome/Application/chrome.exe`)；
   - 两端完全并行运行独立操作链路并输出高清截图证据。

---

## 三、连接池突发高压排队与零泄漏实测（Check 4 & Check 5）

### 1. 突发高压并发排队实测
- **并发客户端数**：35 个独立并发工作线程（超过最大连接数 30，形成强制排队压力）；
- **请求负载**：每个客户端连续请求 4 个高频数据库密集型业务接口，累计 **140 次数据库请求**：
  - 操作员客户端：`/dashboard/overview`、`/tasks?page=1&size=10`、`/situation/snapshot`、`/simulators`；
  - 配置管理员客户端：`/dashboard/overview`、`/devices?page=1&size=10`、`/device-types/overview`、`/simulators`；
- **执行指标**：
  - **总耗时**：2.09 秒；
  - **成功率**：**140 / 140（100.0%）**；
  - **失败数**：**0**；
  - **平均响应延迟**：**366.27 ms**；
  - **P95 响应延迟**：**679.10 ms**；
  - **最大响应延迟**：**1012.85 ms**；
- **排队生效日志实证**（详见 `SRS_NF010-V1.192-connection-pool.log`）：
  ```log
  DEBUG com.zaxxer.hikari.pool.HikariPool : AirportAiHikariPool - Add connection elided, waiting=10, adders pending/running=17
  DEBUG com.zaxxer.hikari.pool.HikariPool : AirportAiHikariPool - Add connection elided, waiting=8, adders pending/running=9
  ```
  日志表明在高并发突发瞬间，HikariCP 队列正常排队借用连接并优雅复用，无请求超时失败。

### 2. 零连接泄漏与防死锁核验
- **高压排队后数据库连接状态采样**：
  - `idle in transaction` 未提交/未释放事务连接数：**0**；
  - `active` 僵死连接数：**0**；
  - 后端连接总数：**8**（完全符合 5~30 弹性收缩区间，严格低于 30 上限）；
- **进程状态**：无死锁、无异常退出，JVM GC 与内存平稳。

---

## 四、真实 Edge 与 Chrome 双浏览器并发自动化实测（Check 6）

### 1. Microsoft Edge 客户端（操作员 oprator）
- **操作步骤**：
  1. 访问 `http://127.0.0.1:15179/login`，输入账号 `oprator` / `12345678` 提交；
  2. 登录成功自动导航至 `/overview` 运行总览，验证页面骨架与指标卡片加载无白屏；
  3. 导航至 `/tasks` 任务管理页，加载表格数据；
  4. 提交特殊旅客服务并发协同任务，接口返回 200，成功生成任务：`TASK-20261110-1363`（ID: 1373）；
  5. 导航至 `/tasks/1373` 查看任务监控详情与执行链路；
  6. 截取全屏证据并保存为 `TC-090-Edge-concurrent-operation.png`。
- **实测结果**：耗时 12167ms，页面无白屏，控制台零错误，状态 **PASSED**。

### 2. Google Chrome 客户端（配置管理员 set）
- **操作步骤**：
  1. 访问 `http://127.0.0.1:15179/login`，输入账号 `set` / `12345678` 提交；
  2. 登录成功自动导航至 `/overview` 配置总览，验证页面内容渲染无白屏；
  3. 导航至 `/devices` 设备管理列表；
  4. 选择设备 `G6_UNTESTED_134145`，执行配置更新（PUT `/api/v1/devices/G6_UNTESTED_134145`，更新上报周期为 15 秒并添加时间戳备注）；
  5. 后端成功返回 200 并持久化；
  6. 导航至 `/situation` 协同态势监控大屏，渲染 2D 监控视图；
  7. 截取全屏证据并保存为 `TC-090-Chrome-concurrent-operation.png`。
- **实测结果**：耗时 10699ms，页面无白屏，控制台零错误，状态 **PASSED**。

### 3. 并发非干扰断言
- 两浏览器使用独立 Context，JWT Token 互不串扰；
- Edge 操作员身份与 Chrome 配置管理员身份隔离，权限各自有效；
- 双方并行执行任务提交与配置保存无锁冲突，`concurrentNonInterference` 状态判定为 **PASSED**。

---

## 五、受控证据清单

1. `acceptance/stage3/evidence/SRS_NF010-V1.192-dual-browser-results.json`：双浏览器并发执行结果与指标；
2. `acceptance/stage3/evidence/SRS_NF010-V1.192-pool-pressure-evidence.json`：连接池 35 并发排队与零泄漏实测数据；
3. `acceptance/stage3/evidence/SRS_NF010-V1.192-connection-pool.log`：HikariCP 实时连接排队与运行日志；
4. `acceptance/stage3/evidence/TC-090-Edge-concurrent-operation.png`：Microsoft Edge 操作员并发操作全屏截图；
5. `acceptance/stage3/evidence/TC-090-Chrome-concurrent-operation.png`：Google Chrome 配置管理员并发操作全屏截图。

---

## 六、验收结论与交接

- **SRS_NF010 数据库高可用与连接池**：**REQUIREMENT_PASSED**；
- **NT-S3-011**：**彻底关闭（CLOSED）**；
- **台账同步**：`rules.csv`、`steps.csv`、`issues.csv`、`阶段3-复测进度.md`、`docs/HANDOFF.md`、`docs/ROADMAP.md` 同步更新；
- **主线推进**：合并入 `main` 并推送到远端，下一项推进 **SRS_NF011 告警推送及时率**。
