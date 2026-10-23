-- 对应5.4.1开放式任务目标提交与理解 + 5.4.2规划上下文构建。
-- 数据库设计说明书V2.0未设计"待补充问题"和"降级原因"的落库字段，此处在tasks表补充。
ALTER TABLE tasks ADD COLUMN missing_info_questions JSON;
ALTER TABLE tasks ADD COLUMN downgrade_reason TEXT;

-- 规划上下文快照：5.4.2业务规则1/4要求以快照形式持久化参与规划的代理清单、能力、
-- 在线状态、位置、负载、可用时间及生成时间，供过程追溯与5.4.5监督判定（上下文接近过期信号）使用。
-- plan_versions.snapshot_id此前只是一个字符串标识，未关联真实快照内容，此处新增真实存储表。
CREATE TABLE context_snapshots (
    id BIGSERIAL PRIMARY KEY,
    snapshot_code VARCHAR(32) NOT NULL UNIQUE,
    task_id BIGINT NOT NULL,
    agents JSON NOT NULL,
    capability_coverage JSON,
    failed_agent_codes JSON,
    generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_context_snapshot_task FOREIGN KEY (task_id) REFERENCES tasks(id)
);
CREATE INDEX idx_context_snapshot_task_id ON context_snapshots(task_id);
