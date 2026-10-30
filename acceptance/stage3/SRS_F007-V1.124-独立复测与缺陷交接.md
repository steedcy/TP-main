# F007 V1.124 独立复测与缺陷交接

结论：**READY_FOR_CLAUDE（V2.3）**。产品 `6062a7e57f733cb529ec55daeb3e1ac4d0e32597` / V1.124，Claude 交接 `b76cfe5`，GPT 接收 `73a081b`。本组未通过，main仍 `f1a61e8`，不推进F008。

独立构建后端成功（离线 package、跳过单测），GPT 自有 schema `tip_gpt_f006_v118_20261030` 真实 V23→V24 迁移成功。V1.123 仿真器源码相对 V1.124 无变更，独立构建并运行。原始记录位于 `evidence/SRS_F007-V1.124-*.json` 和页面截图。

- **DEF-S3-082 查询字段已通过复测**：能力和状态查询实际返回200；迁移后新增事件的结构化指令号和 SUCCESS 均正确，真实 Edge 代理详情页面相应列可见。原失败证据保留。
- 实际设备代理及仿真器联动：同一步骤的承接、执行、取消编号两两不同；取消后设备空闲，取消确认 `CONFIRMED_IDLE`；真实失败及超时反馈分别触发重试，执行编号不变、尝试序号0→1。承接编号用于执行反馈时返回404/code4116，正确拒绝。设备 report 入口的 `UNRECOGNIZED` 反馈实际归一为 FAILED、原因码 `ERR_FEEDBACK_UNRECOGNIZED`，进入重试。测试夹具为自有库构造进行中任务和步骤，不声称从创建任务开始的完整 E2E。
- 速度、加速度、姿态、路径点、避障、急停、限速、失联停靠及下划线/连字符变体共11种在平台统一消息入口和仿真器 HTTP 两侧均返回400；正常展示意图在实际消息链路中接受。以上观察与原始记录中的探针中断不混计。

## DEF-S3-083：统一消息入口未归一未知反馈

在隔离库创建已有有效执行编号的活动步骤，通过 `/internal/v1/device-agent/messages` 发送 `EXECUTION_FEEDBACK`、`executionResult=UNRECOGNIZED`，返回 HTTP 400/code3001“executionResult取值非法”，未进入统一的失败归一与异常恢复。原始请求/响应和任务 ID 在 `evidence/SRS_F007-V1.124-unified-feedback.json`。同版本同条件下设备 `/device-api/v1/agents/{agent}/report` 路径已实测归一、记录 `ERR_FEEDBACK_UNRECOGNIZED` 并重试，见 `...-feedback-r2.json`。涉及 TC-024.S1、SRS_F007.R06；请 Claude 统一两个入口的非空未知结果处理，同时保留空值拒绝及合理的身份、步骤和幂等校验，定向回归后推送递增标签和交接。

探针诊断完整保留并与产品 F 区分：承接编号反馈正确返回404，首次探针错误要求400；一次终止缺 `confirmed` 合理400；一次超时测试遇到自有活动夹具占用409；两次UI定位/分页超时。分别纠正后补足缺失观察，详见 `...-build-and-diagnostics.json`。旧 F/NT 不删除。

其余六类消息中的拒绝、全角色时间线和失败/超时原因码展示、有效/异常边界、旧迁移回退与 F004/F005/F006 邻接仍 NT；DEF-S3-049 历史 F 不以部分观察直接关闭。发现明确产品 F 后及时交回，本版未完成整项验收。

GPT 自有后端18129/Redis10、schema V24，PID 4432，V1.124 运行元数据 `.local-test/gpt-f007-v124-runtime.json`；仿真器18130 PID10636、Vite15179 PID2404，操作前须再次核对。不要碰对方资源或重建/覆盖历史库。
