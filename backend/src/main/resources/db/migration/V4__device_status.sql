-- 对应5.2.1设备档案与连接测试业务规则6"停用/启用"设备档案。
-- 数据库设计说明书V2.0 4.3.1节的devices表遗漏了设备档案自身的启用/停用状态字段
-- （device_agents.agent_status是代理侧状态，两者语义不同：停用设备时联动停用代理，
-- 但设备本身也需要独立状态用于列表筛选、防止对已停用设备发起连接测试/创建代理）。
-- DELETED为逻辑删除标记：device_agents.device_id对devices.id有外键约束，且5.2.2业务规则
-- 要求代理归档后"仅保留历史记录"不可恢复，故设备删除不做物理DELETE，只做状态标记（见DeviceService.delete）。
-- device_code唯一约束（devices_device_code_key，V1建表时已建）对DELETED状态记录同样生效，
-- 即设备编码为永久标识，删除后不可复用——避免历史操作记录/事件时间线中的编码指向发生混淆。
ALTER TABLE devices ADD COLUMN device_status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE';
ALTER TABLE devices ADD CONSTRAINT chk_device_status CHECK (device_status IN ('ACTIVE', 'INACTIVE', 'DELETED'));
CREATE INDEX idx_device_status ON devices(device_status);

-- V1.4正文5.2.2/5.2.3多处提到"设备事件"（代理创建/停用/启用/归档、离线、恢复上报等），
-- 但数据库设计说明书V2.0未设计对应表；task_events.task_id为NOT NULL外键，
-- 无法承载与任务无关的纯设备事件（如未占用任何任务时的离线/恢复）。
-- 新增device_events表，仅追加语义与task_events一致。
CREATE TABLE device_events (
    id BIGSERIAL PRIMARY KEY,
    device_agent_id BIGINT NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    occurred_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    trigger VARCHAR(16) NOT NULL DEFAULT 'SYSTEM',
    reason_code VARCHAR(64),
    detail_summary TEXT,
    CONSTRAINT fk_device_event_agent FOREIGN KEY (device_agent_id) REFERENCES device_agents(id),
    CONSTRAINT chk_device_event_trigger CHECK (trigger IN ('SYSTEM', 'OPERATOR'))
);
CREATE INDEX idx_device_event_agent_id ON device_events(device_agent_id);
CREATE INDEX idx_device_event_occurred_at ON device_events(occurred_at);
