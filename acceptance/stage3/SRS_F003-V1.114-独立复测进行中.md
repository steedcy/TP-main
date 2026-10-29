# SRS_F003 V1.114 独立复测进行中

- Claude 产品代码：`8746e2832865d2a5b29581fe6560c94e46f7364c`，标签 `V1.114`；GPT 已快进合入 `ai/claude-fix` 交接提交 `6c5ffb83e9b057ea1759f2e10735aaf724898c7f`。
- 环境：Windows 本机 GPT 独立 schema `tip_gpt_f002_v111_20261029`、后端 `127.0.0.1:18105`、Edge/Vite `127.0.0.1:15174`、仿真器 `18110`。没有使用 Claude 运行资源。
- 构建：`mvn -o -DskipTests package` 成功；这只是运行前置，不等于验收。
- 当前结论：**复测尚未完成，SRS_F003 未通过，也未推进 F004**。本文件只记录已执行的子检查；步骤和规则最终 P/F/NT 待补齐后登记。

## 已执行的原始检查

- 新建边界、四种仿真体、唯一性、列表字段共 21 个 API 子检查均满足脚本断言；四种新建仿真体能力数分别为 4/3/3/5，均包含 `CAP_SIM_STATUS` 且为 `UNTESTED`。V18 已在隔离库执行；旧 V1.113 仿真体能力集也已补齐。对一台新仿真体删除一项能力后，重载首次补 1 项、再次补 0 项。证据：`evidence/SRS_F003-V1.114-phase1.json`、`evidence/SRS_F003-V1.114-diagnostic-correction.json`。
- Edge 页面 4 个子检查通过：列表列、在线筛选入口、新建表单默认项、编码检索。证据：`evidence/SRS_F003-V1.114-ui.json`。
- 连接与启用 8 个原始子检查中 7 个脚本断言通过。读取超时项的原始 `pass=false` 源于脚本复用前一项的相同 URL，连接状态按设计保留 `FAILED`，实际超时原因已正确保存；原始证据保留，后续以更正口径复核。证据：`evidence/SRS_F003-V1.114-connection.json`。
- 删除三种进行中任务均返回 409 且任务/设备状态不变。停用待分配占用设备后 HTTP 200、代理 `DISABLED/OFFLINE`、释放事件 0→1、任务转 `PENDING_MANUAL` 并产生 `AGENT_OFFLINE` 异常；步骤行仍为 `PENDING_ASSIGNMENT`。原始脚本把行状态不变判为失败；前两次诊断夹具缺少计划版本/步骤，现已更正。需按规格确认人工接管状态下步骤行保留是否合理，不能仅凭脚本更正宣称整项通过。证据：`evidence/SRS_F003-V1.114-r06.json`、`evidence/SRS_F003-V1.114-diagnostic-correction.json`。

## 待继续

TC-008.S1 完整边界与编辑、S2 类型/在线组合和分页、TC-009.S1/S3 浏览器结果/凭据编辑、TC-010.S2 另两种占用状态与空闲设备、S3 确认/归档/审计、R07/R08、能力测试启用及 TC-017.S3/TC-093.S1 邻接回归。旧版 P 不沿用。基线文档与公司版用例未修改。
