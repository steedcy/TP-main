# SRS_F007 V1.125 独立复测进行中

- 执行基线 V2.3；产品 `80234681218bc10613cd9b1400a6a08fc4e065c8`，标签 V1.125，Claude 交接 `21861ddd48da44287e334be94f62be6695a0ce4d`，main `f1a61e8`。当前 GPT_TESTING，需求尚未裁决。
- 独立后端构建成功，运行自有 schema `tip_gpt_f006_v118_20261030`（V24）、端口 18129、Redis 10；运行元数据 `.local-test/gpt-f007-v125-runtime.json`。仿真器 18130 沿用源码未变的 V1.124 构建；操作前核对进程归属。
- V1.125 活动步骤真实统一入口空结果返回 400；UNRECOGNIZED 返回 200，事件 FAILED/ERR_FEEDBACK_UNRECOGNIZED，重试使用相同执行编号、序号 0→1：`evidence/SRS_F007-V1.125-unified-feedback-r2.json`。首轮因 Windows 子进程输出编码导致探针读取失败，不是产品失败；保留 `...-unified-feedback.json` 与从原任务恢复的 `...-unified-recovery.json`。
- 尚须验证原始值、设备 report 对照、缺失/空白、身份/步骤/序号/重复回执及合法反馈等受影响路径，六类消息、角色时间线、迁移回退和邻接剩余 NT；按 V2.3 核对历史 P 的源码/依赖影响，来源保留原 SHA。旧 F/NT 保留；未合 main、不推进 F008。
