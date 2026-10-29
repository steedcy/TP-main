# SRS_F002 运行总览：V1.111 独立复测与缺陷交接

- 复测时间：2026-10-29（Asia/Shanghai）。产品代码：`5d6d61b920a0f2b3ef762ca6f9ffb08921231ad4`，标签 `V1.111`；GPT 接收合并：`281601e62053c8aee127798c4c2b55dee8097301`。
- 基线：需求规格说明书 V1.0、测试计划/用例 V2；本轮未修改基线。测试工作区 `ai/gpt-test`，Claude 产品分支 `ai/claude-fix`。
- 独立环境：Windows 本机隔离 PostgreSQL schema `tip_gpt_f002_v111_20261029`（总览统计）与 `tip_gpt_f002flow_v111_20261029`（F2 任务流），后端 18105/18106/18107，前端 15174/15175，Redis DB 15/14/13；本机模型夹具 8099，任务流设备端点统一改指向未启用的 `127.0.0.1:18108`。未触碰共享 8080/5173/8091–8096 服务或 public schema。账号为本地合成角色，证据不含凭据/令牌。
- 构建：后端 `mvn -o -q -DskipTests package` 成功；前端 `npm run build` 成功（3263 模块，存在大包提示）。Claude 自报的 103 项后端单测是定向回归，不作为 GPT 独立验收结论。

## 当前裁决

| 项目 | V1.111 裁决 | 独立观察 |
| --- | --- | --- |
| TC-004.S1 | P | 九状态正式任务、试运行诱饵、五类异常与代理正样本；独立 SQL 与 API/Edge 指标一致：正式 COMPLETED=6、进行中=12、待人工=8、未处置异常=3、今日/近7日重规划均=2、代理总数=4、在线启用=2。 |
| TC-004.S2 | F | 九状态卡、已完成任务列表、五类最新异常及详情正常；但代理总数卡=4，点击后列表=5；在线卡=2，点击后列表=4。见 `DEF-S3-074`。真实模板试运行对正式统计的邻接复测尚需补做。 |
| TC-004.S3 | P | Edge 三角色默认今日、近7日切换、手动刷新与可见范围通过；配置管理员不显示任务指标。 |
| TC-004.S4 | P | 独立故障实例分别对 `agentOnline` 注入 FAIL、`statusCounts` 注入 DELAY；API 仅该指标为 null 且列入 `failedMetrics`，Edge 显示“--”及局部告警，其他区域仍正常。 |
| TC-005.S1 | F | 低风险计划和自动分配尝试有证据；高风险特殊旅客任务在基线启用时返回 500，不能完成自动降级。见 `DEF-S3-075`。设备端点故意不可达，低风险任务之后转人工不归因于监督流程。 |
| TC-005.S2 | F | 特殊旅客确定性高风险分支受同一 500 阻断；跨区域、资源临界及双信号边界尚未全测。 |
| TC-005.S3 | NT | 特殊旅客基线停用时，高风险任务确实转待人工，总览计数 3→4；监督无法判定、服务不可用、基线执行失败尚无完整独立证据。 |

规则：`R01/R02/R07/R08=P`，`R03=F`，`R04/R05/R06=NT`。其中 R02 的“九状态数量和状态卡跳转”本身通过；TC-004.S2 因代理卡跳转口径仍判 F。R05 的启停版本 API 子检查 7/7 通过，但同一候选计划启停成对判定未完成，不能裁定整条规则通过。旧版 F/NT 记录均保留在台账和原证据中。

## 缺陷与前置缺口

1. `DEF-S3-074`：总览卡片的代理总数排除 `ARCHIVED`，在线数仅统计 `ENABLED + ONLINE`；卡片点击后分别进入无状态筛选列表、只按 `onlineStatus=ONLINE` 的列表。隔离样本包含 2 启用在线、1 启用离线、1 停用在线、1 归档在线，API 和 Edge 都复现 4→5、2→4。请统一卡片与跳转列表的业务口径，并复测筛选/分页。证据：`evidence/SRS_F002-V1.111-api-20261029.json`、`evidence/SRS_F002-V1.111-browser-20261029.json`。
2. `DEF-S3-075`：F2 特殊旅客基线模板启用、相关代理/能力准备完成、模型夹具成功时，任务提交返回 HTTP 500/API 1000；后端本地日志的根因是 `task_step_assignments.step_seq` 非空约束失败。F2 特殊旅客和大件行李模板步骤均无 `stepSeq`，`TaskPlanningOrchestrator.normalizeTemplateSteps` 未补序号，而 `TaskExecutionOrchestrator.startExecution` 按该字段写分配表。对特殊旅客分别用含/不含显式 `assistanceType` 的输入复现。请在产品逻辑中为模板步骤生成稳定序号并验证高风险降级，勿改正式用例来掩盖失败。已脱敏记录：`evidence/SRS_F002-V1.111-baseline-stepseq-20261029.json`、`evidence/SRS_F002-V1.111-flow-20261029.json`。本地完整后端日志不上传公开仓库。
3. `NT-S3-028`：TC-005.S3 仅无可用基线分支实测通过；监督无法判定、监督服务不可用、基线执行失败需隔离故障夹具。`NT-S3-029`：TC-005.S2 的低置信度、候选差异、上下文时间单信号/双信号及 0.8/60 秒边界尚未全测。修复 `DEF-S3-075` 后继续。

`DEF-S3-002` 的总览及任务/异常列表排除试运行口径，在人工 SQL 诱饵上通过，但 `TC-028.S2` 的真实模板试运行仍需邻接复测，故缺陷不在本轮完全关闭。`DEF-S3-043` 的规则启停版本递增 API 已复测，`NT-S3-027` 同候选成对判定仍未完成。`NT-S3-002/003` 的夹具已实跑。Claude 提供的 `nt-s3-002-seed-overview.py` 初次运行在数据写入后因 psql `SET` 输出导致 `expected()` 解析错误；GPT 只给 psql 增加 `-q`，随后独立 SQL 输出与 API 一致。最初代理正样本因心跳超时转离线的诊断结果亦保留，随后在本轮专用后端将心跳阈值设为 3600 秒并重新准备样本；该诊断不作为产品失败。

## 原始证据索引

- 独立 SQL 和正向 API：`evidence/SRS_F002-V1.111-sql-expected-20261029.json`、`evidence/SRS_F002-V1.111-api-20261029.json`。
- Edge 功能和链接：`evidence/SRS_F002-V1.111-browser-20261029.json`。
- 单指标故障/超时与 Edge：`evidence/SRS_F002-V1.111-fault-fail-20261029.json`、`evidence/SRS_F002-V1.111-fault-delay-20261029.json`、`evidence/SRS_F002-V1.111-fault-browser-20261029.json`。
- 风险规则版本、低风险计划、无基线分支及高风险故障：`evidence/SRS_F002-V1.111-risk-version-20261029.json`、`evidence/SRS_F002-V1.111-low-risk-plan-20261029.json`、`evidence/SRS_F002-V1.111-no-baseline-20261029.json`、`evidence/SRS_F002-V1.111-flow-20261029.json`、`evidence/SRS_F002-V1.111-baseline-stepseq-20261029.json`。
- 前置诊断：`evidence/SRS_F002-V1.111-diagnostic-heartbeat-20261029.json`。

下一轮仍处理 SRS_F002；不得前进至 F003 或把任一 NT 计为通过。修复后须在下一版本独立重测上述 F 和 NT，已通过的步骤/规则按代码影响范围做邻接回归。
