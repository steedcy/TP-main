-- 对应5.3.2试运行与启用业务规则3/5：试运行结果与自主规划使用相同任务和事件结构，
-- 但必须标记为试运行实例，且不计入运行总览的正式任务统计。
-- 数据库设计说明书V2.0的tasks表未设计该标记字段，此处补充。
ALTER TABLE tasks ADD COLUMN is_dry_run BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX idx_task_is_dry_run ON tasks(is_dry_run);

-- 试运行发起时选择的模拟设备（每个步骤一个agent_id），随试运行结果一并保存供追溯，
-- 数据库设计说明书未设计对应表，新增dry_run_devices仅追加记录本次试运行的设备选择。
CREATE TABLE dry_run_device_selections (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL,
    step_seq INT NOT NULL,
    device_agent_id BIGINT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_dry_run_selection_task FOREIGN KEY (task_id) REFERENCES tasks(id),
    CONSTRAINT fk_dry_run_selection_agent FOREIGN KEY (device_agent_id) REFERENCES device_agents(id)
);
CREATE INDEX idx_dry_run_selection_task_id ON dry_run_device_selections(task_id);
