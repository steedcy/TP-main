-- 对应5.5.1候选轮询："全部候选拒绝或无候选->生成异常"。task_step_assignments每个步骤只有一行
-- （唯一索引plan_version_id+step_seq），候选轮询发生在多次异步的设备响应请求之间（不是同一次
-- 方法调用内的循环），需要持久化"已尝试过哪些候选"才能在下一次响应到达时正确选出下一个候选，
-- 且不能重复询问已拒绝过的设备。故补充该字段，而非依赖task_events做文本解析。
ALTER TABLE task_step_assignments ADD COLUMN rejected_agent_ids JSON NOT NULL DEFAULT '[]';
