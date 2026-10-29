# SRS_F002 运行总览：V1.112 独立复测与验收裁决

- 代码：`e1b06ee0c2b07b3f545a9a35c4be3c91b2b3c970`，标签 `V1.112`，Claude 修复分支 `ai/claude-fix`；GPT 在 `ai/gpt-test` 合并接收 `616ed60` 后独立复测。
- 结果：TC-004.S1～S4、TC-005.S1～S3 共 **7 步 P**；`SRS_F002.R01`～`R08` 共 **8 条 P**。旧 V1.111 的 F/NT 原始记录保留。此结论只针对 SRS_F002 的本轮范围，不代表 95 项全量通过。
- 环境：Windows 本机、独立 PostgreSQL schema `tip_gpt_f002_v111_20261029`（总览正样本；schema 名沿用，运行代码为 V1.112）与 `tip_gpt_f002flow_v112_20261029`（F2 流程），独立后端 18105/18106/18107、模型夹具 8099、仿真设备 18108、Edge 前端 15174/15175/15176；未使用共享 8080/5173/8091～8096。所有数据为虚构样本。

## 分项证据

| 项目 | 独立观察 | 原始证据 |
| --- | --- | --- |
| TC-004.S1/S2、R01/R02/R07 | 正式九状态统计与 SQL 一致；完成数 6；总览代理总数 4→默认列表 4，在线数 2→启用在线列表 2；五类异常、详情和跳转正常。 | `evidence/SRS_F002-V1.112-api-18105-20261029.json`、`evidence/SRS_F002-V1.112-ui-20261029.json` |
| TC-004.S3、R08 | 三角色可见范围、今日/近7日与刷新在 Edge 复测。 | 同上 |
| TC-004.S4 | 单指标 FAIL 和 DELAY 均只影响指定位置，Edge 显示 `--` 与局部告警，其余指标可用。 | `evidence/SRS_F002-V1.112-fault-fail-20261029.json`、`evidence/SRS_F002-V1.112-fault-delay-20261029.json`、`evidence/SRS_F002-V1.112-fault-ui-20261029.json` |
| TC-005.S1、R03 | 高风险状态流转 `PLANNING→SUPERVISING→DOWNGRADING`；同一候选在资源临界规则停用后为低风险，流转 `PLANNING→SUPERVISING→PENDING_ASSIGNMENT`。后续不可达设备造成的转人工单独记录。F2 特殊旅客和大件行李基线步骤序号已补齐，任务提交不再 500。 | `evidence/SRS_F002-V1.112-status-transitions-20261029.json`、`evidence/SRS_F002-V1.112-risk-pair-20261029.json`、`evidence/SRS_F002-V1.112-flow-20261029.json` |
| TC-005.S2、R05/R06 | 陪同、跨区、资源临界三类规则命中；同目标同场景参数在规则启用/停用时由 HIGH 改 LOW，规则集 V1.6→V1.7；单信号 LOW、0.79+候选差异 HIGH、0.80 边界 LOW、候选差异+62.5 秒模型延迟 HIGH。跨区样本在隔离能力 schema 声明可选 `targetZone`，三类计划校验均 PASS。 | `evidence/SRS_F002-V1.112-flow-20261029.json`、`evidence/SRS_F002-V1.112-risk-pair-20261029.json`、`evidence/SRS_F002-V1.112-risk-signals-20261029.json`、`evidence/SRS_F002-V1.112-cross-zone-20261029.json` |
| TC-005.S3、R04 | 无基线、监督无法判定、监督不可用及真实仿真设备反馈失败后基线重试/恢复失败，均进入待人工；总览计数同步增加、卡片高亮、任务和异常详情可打开。 | `evidence/SRS_F002-V1.112-no-baseline-20261029.json`、`evidence/SRS_F002-V1.112-risk-fault-undetermined-20261029.json`、`evidence/SRS_F002-V1.112-risk-fault-unavailable-20261029.json`、`evidence/SRS_F002-V1.112-baseline-failure-20261029.json`、`evidence/SRS_F002-V1.112-flow-ui-20261029.json` |
| 邻接 TC-028.S2 统计子项 | 真正的模板试运行完成，任务 `is_dry_run=true`、计划来源 `BASELINE_TEMPLATE`、事件含下发和反馈；正式总览完成数 0→0。仅关闭试运行计数偏差，TC-028.S2 其他审计要求仍待 SRS_F009 复测。 | `evidence/SRS_F002-V1.112-dryrun-20261029.json` |

## 诊断与边界

- 初次通过数据库回写 `context_snapshots.generated_at` 试图模拟过期，未影响当前请求内存中的快照，所得 LOW 为**夹具无效**，不计产品 F；原始诊断保留在 `evidence/SRS_F002-V1.112-risk-signals-diagnostic-db-backdate-20261029.json`。改用模型延迟 62.5 秒且隔离实例超时阈值 75 秒后实测 HIGH。默认产品模型超时仍为 60 秒；该覆盖验证风险函数在可达前置条件下的行为，非默认超时性能验收。
- F2 风险流程设备端点故意隔离不可达，因此部分任务在经过 LOW/PENDING_ASSIGNMENT 或 HIGH/DOWNGRADING 后又因设备能力分配转人工；状态触发的证明来自隔离 schema 的追加式状态变更触发器和任务事件，不以最终状态代替中间状态。
- 跨区测试为能力输入声明了可选 `targetZone`，结束后恢复原配置；正式 F2 标准夹具未声明该字段。后续 SRS_F014 还需检验实际业务配置及规则可维护性。
- `DEF-S3-074`、`DEF-S3-075` 在本需求范围关闭；`DEF-S3-002` 的总览统计子项和 `DEF-S3-043` 的版本/成对判定子项通过。TC-028/TC-043 的其他要求及既有缺陷不在本次整项裁决中自动转 P。

下一需求按顺序为 `SRS_F003`。Claude 须从已推送的最新 `main` 接收本轮证据，继续修复；GPT 待下一 `READY_FOR_GPT` 已推送提交后才独立复测。
