# SRS_F004 V1.116 独立复测与验收裁决

- 产品提交 `6d7a028bcad79dcd0137d241b127b6e84183dca7`，标签V1.116，Claude交接d1d1433。GPT在Windows本机隔离schema `tip_gpt_f002_v111_20261029` 独立实测；后端18105、辅助后端18106/Redis12、Edge/Vite15174、GPT仿真器18114/18116，本地受控模型18117。前后端构建成功不作为验收结论。
- **SRS_F004通过：TC-011～013共8步骤P8/F0/NT0；R01～R08共8规则P8/F0/NT0。** 本结论只覆盖F004，不是95项或项目整体验收。

| 步骤 | 本版独立证据与结论 |
| --- | --- |
| TC-011.S1 | 实际连接PASSED后自动创建唯一启用空闲代理；重复连接/显式创建不增行；未测试设备创建400；带已启用能力的代理进入实际规划候选。`intake`、`fault-retry`、`candidate-retry`。 |
| TC-011.S2 | Edge列表/详情字段齐全含能力编码名称；配置管理员当前任务为文本，运行操作员链接GET200；双承接请求实测同一代理最多1个执行步骤，两任务均完成。`agent-ui`、`messages`。 |
| TC-011.S3 | 系统管理员使用任意唯一指令号调用六类统一消息：能力查询、状态查询、承接、拒绝、执行反馈、取消均走统一入口；实际承接/拒绝后任务完成，反馈正确业务结果后完成，取消写传输账本。运动安全字段400且设备指令行数0；非法消息类型400。`messages`、`feedback-correction`。完整消息时间线界面仍留F007，不在本项宣称通过。 |
| TC-012.S1 | Edge取消停用保持BUSY/任务不变；确认停用后恢复切换另一代理并实际完成，原占用清空。待分配关联且current_task_id为空同样恢复成功；confirmed=false400且状态不变。`agent-ui`、`occupied-recovery`、`pending-archive`。 |
| TC-012.S2 | 设备停用/启用同步代理并重新ONLINE；删除后ARCHIVED/OFFLINE且历史保留，重建409不可恢复。停用/归档均不在实际规划快照候选。`intake`、`pending-archive`、`candidate-retry`、`neighbor`。 |
| TC-012.S3 | 创建/停用/启用/归档四类专属操作记录与设备事件齐全，含占用释放。`pending-archive`、`occupied-recovery`。 |
| TC-013.S1 | 仅对GPT单个设备ID注入唯一编号冲突、持久化异常：连接PASSED保留、自动创建false、显式创建500并提示稍后重试，始终0条代理，无半成品；触发器finally移除并复查0。`fault-retry`。 |
| TC-013.S2 | 故障解除后重试生成1条唯一在线代理，能力实际测试并启用；实际规划上下文含新代理，停用后新快照不含。`fault-retry`、`candidate-retry`。 |

表中缩写均为 `acceptance/stage3/evidence/SRS_F004-V1.116-{名称}.json`。步骤与规则登记见steps.csv、rules.csv。

## 邻接与诊断

- 自动创建修改后的连接结果、设备启停同步已以实际仿真器验证；统一消息传输覆盖TC023相关路径，总览代理总数/在线数与SQL一致（`neighbor-correction`）。不重复宣称F003全量或TC023事件时间线全项验收。
- 原`messages`反馈探针使用displayed=true，非CAP_INFO_DISPLAY的完成标记displayStatus=SUCCESS，因此即时任务仍EXECUTING；原false保留，任务随后通过运行时完成。使用正确业务标记的独立新任务即时COMPLETED，见`feedback-correction`，不是放宽完成标准。
- 原`neighbor`在响应根级取指标而不是metrics，原false保留；按正式响应结构读取后与SQL一致，见`neighbor-correction`。
- 18105未配置模型地址导致初次候选探针503；使用独立18106/18117可控夹具，仅验证实际上下文候选，不冒充模型质量测试。
- 六类消息测试的任务/计划/分配为GPT专用schema内的有效合成夹具；双承接由运行时实际处理，采样最大同时执行数1。取消账本验证传输路径，不代替后续取消用例的完整业务验收。
- 需求/95项用例未修改，公司版资料未处理。旧F/NT证据保留；V1.116标签不移动到证据提交。下一项SRS_F005设备状态上报与离线判断。
