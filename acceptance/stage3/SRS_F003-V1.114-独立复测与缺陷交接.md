# SRS_F003 V1.114 独立复测与缺陷交接

- 产品代码：`8746e2832865d2a5b29581fe6560c94e46f7364c`（标签 `V1.114`）；Claude 交接提交 `6c5ffb83e9b057ea1759f2e10735aaf724898c7f`；GPT 复测分支 `ai/gpt-test`。未合并 `main`，未推进 `SRS_F004`。
- 环境：Windows 本机 GPT 独立 schema `tip_gpt_f002_v111_20261029`；后端 `127.0.0.1:18105`；Edge/Vite `127.0.0.1:15174`；仿真器 `127.0.0.1:18110`，代理状态报告定向至 GPT 后端。未使用 Claude 工作目录、schema 或端口。
- **结论：SRS_F003 未通过。** TC-008～010 的 9 步为 **P7/F2/NT0**；F 为 TC-008.S1 和 TC-009.S3，均由 DEF-S3-078 导致。R01～R08 按本项规则文本为 **P8/F0/NT0**；R04 的“按类型加载画像”已满足，但画像内 `CAP_SIM_STATUS` 的调用测试另有 DEF-S3-079，阻断关联能力用例，不能据 R04 的 P 宣称关联用例通过。构建成功和单项规则 P 不代替整项验收。

## 本轮结果

| 步骤/规则 | 判定 | 独立观察 |
| --- | --- | --- |
| TC-008.S1 | F | Edge 新建默认值、合法最小/最大边界、非法边界、唯一性等子检查通过；编辑设备时前端 PUT 返回 500，弹窗保持打开。 |
| TC-008.S2 | P | Edge 必需列、编码检索、类型与离线组合筛选；API 名称检索、组合筛选与两页无重叠分页准确。无代理设备在 API 中 `onlineStatus=null`，页面按离线显示，原脚本要求字面 `OFFLINE` 的 false 已有更正证据。 |
| TC-008.S3 / R05 | P | 19→20 的新增正常；20 个活动对象时再新增合法对象返回 409、提示上限 20、总数不变。两次原始观察均保留。 |
| TC-009.S1/S2 | P/P | 真仿真器连接成功、服务端及 Edge 均显示耗时，代理可创建；不可达、非法响应、读取超时原因不同且保存 FAILED，均拒绝创建代理。读超时脚本复用 URL 时状态保留 FAILED，原 false 与更正说明均保留。 |
| TC-009.S3 | F | API 使用定义内字段修改接入参数成功，结果重置与掩码行为可验证；Edge 编辑提交带有 `deviceCode` 等不属于 `UpdateDeviceRequest` 的字段，HTTP 500，无法从页面完成编辑。 |
| TC-010.S1 | P | 待分配、降级执行中、执行中三类正式任务关联设备均不能删除；HTTP 409，任务与设备不变。 |
| TC-010.S2 / R06 | P | 待分配、降级执行中、执行中占用设备停用后代理停用离线并清空占用，写释放事件和异常，任务转人工；空闲代理停用不产生释放事件。连接未通过时再启用被拒，重测通过后可启用。待分配步骤行仍保存历史 `PENDING_ASSIGNMENT`，但任务已转 `PENDING_MANUAL`，代理占用释放；原脚本要求行状态变化的 false 保留在原始证据中。 |
| TC-010.S3 / R07 | P | Edge 删除先取消则设备仍在，确认后设备软删除、代理归档并保留历史；新增、修改、停用/启用、删除均有操作日志，日志未含测试用虚构凭据原值。 |
| R01～R04、R08 | P | 唯一性、连接前置、连接结果、五类边界和四类仿真画像、凭据掩码均按规则文本验证；V18 在隔离库执行，旧实例补齐，新实例继承能力数 4/3/3/5，重载首次补缺 1 项、再次补 0 项。 |

## 待 Claude 修复

1. **DEF-S3-078，编辑设备失败（TC-008.S1、TC-009.S3）**：Edge 编辑 `G3MAX155148XXXXXXXXXXXXXXXXXXXXX` 时 PUT `/api/v1/devices/{code}` 返回 500；请求体有 `deviceCode`、`deviceTypeCode`、`isSimulator`、`simulatedDeviceType`、`accessCredentialRefMasked` 等非 `UpdateDeviceRequest` 字段。后端日志为 `HttpMessageNotReadableException: Unrecognized field "deviceCode"`。前端 `DeviceListView.vue` 把整个表单对象传给 `updateDevice`。请只发送更新 DTO 允许的字段；保留“凭据输入留空不修改”和掩码；用 Edge 实测编辑、接入参数变更重置、重测及操作日志。定义内字段的 API PUT 已通过。原始证据：`evidence/SRS_F003-V1.114-boundaries.json`、`evidence/SRS_F003-V1.114-edit-ui.json`、`evidence/SRS_F003-V1.114-edit-diagnostic.json`。
2. **DEF-S3-079，仿真状态能力不可测试（关联 TC-017.S3、TC-093.S1）**：`CAP_SIM_STATUS` 已作为 `UNTESTED` 画像加载；在代理 `ENABLED/ONLINE` 且同设备三项业务能力均 `TESTED_PASSED` 的前置下，对 `CAP_SIM_STATUS` 调用测试得到 `TESTED_FAILED`，启用返回 400“能力未通过模拟调用测试”。仿真器执行器没有该能力的成功处理路径。请使仿真状态能力通过统一代理测试并可启用，再验证新同类设备从连接、能力测试到启用的完整链。原始证据：`evidence/SRS_F003-V1.114-final-api.json`。TC-017.S3 的矩阵导出旧偏差与 TC-093.S1 全流程尚需在各自需求轮次完整复测，本轮未宣称通过。

## 证据与口径

所有本轮 JSON 原始证据位于 `acceptance/stage3/evidence/SRS_F003-V1.114-*.json`；`steps.csv`、`rules.csv`、`issues.csv` 已登记本轮状态。V1.113 的失败及 V1.114 原始脚本 false 均保留，诊断更正见 `SRS_F003-V1.114-diagnostic-correction.json`、`SRS_F003-V1.114-edit-diagnostic.json`、`SRS_F003-V1.114-final-api.json` 与上限 19→20 / 20→20 两次证据。需求基线、95 项用例和公司版用例均未修改。
