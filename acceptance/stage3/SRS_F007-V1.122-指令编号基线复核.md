# F007 V1.122 指令编号基线复核

产品 `b1c3959b74d4db3a9e7326a350bcc8107e6760d7` / `V1.122`，Claude交接 `76bd7c46c58648bea7abc33aaed4567537f902f3`，执行基线 V2.3。

DEF-S3-049 的历史真实运行证据 `evidence/TC-023-command-identity-20261026T120620Z.json` 显示同一步骤的接受、执行和取消跨消息类型复用指令号。V1.122 交接明确说明该行为未修改；`git diff --name-only V1.121 V1.122 -- backend/src/main/java/com/airport/ai/task/TaskExecutionOrchestrator.java backend/src/main/resources/mapper/DeviceCommandMapper.xml` 无输出。该项沿用历史 F 和源码影响复核，**不宣称 V1.122 已独立运行复现**。

BL-003 的方案 A 会将已记录失败的“每条下发类消息唯一指令号”改为跨消息复用，涉及幂等与事件关联等核心协议规则，不予追溯放宽。请按方案 B 修复：不同逻辑消息分配各自唯一指令号，同一逻辑消息重试保留相同编号；同步反馈、取消、设备适配器、任务关联与必要迁移。实施中如发现更安全兼容的设计，可在保持该规则的前提下记录设计取舍。

本版其他修改尚未独立实跑，保持 NT；不继承 Claude 单测结果为独立 P。收到新版本后复测 TC-023/024 的指令编号、重试、六类消息、安全字段、反馈、时间线和受影响邻接。旧 F/NT 和证据保留，F007 未验收，不推进 F008。
