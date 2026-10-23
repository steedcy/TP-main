-- 对应5.5.3异常识别与恢复、5.5.5任务监控业务规则9/10。数据库设计说明书未设计独立的异常状态
-- 管理表，task_events是仅追加日志，无法承载"待处置->处置中->已处置/已忽略"的状态流转，此处补充。
CREATE TABLE task_exceptions (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL,
    step_seq INT,
    exception_type VARCHAR(32) NOT NULL,
    occurred_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    recovery_action TEXT,
    recovery_result VARCHAR(16),
    impact_conclusion TEXT,
    reason_code VARCHAR(64),
    exception_status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(64),
    CONSTRAINT fk_task_exception_task FOREIGN KEY (task_id) REFERENCES tasks(id),
    CONSTRAINT chk_exception_type CHECK (exception_type IN
        ('AGENT_OFFLINE', 'CAPABILITY_GAP', 'EXECUTION_TIMEOUT', 'STEP_FAILED', 'REPLAN_FAILED')),
    CONSTRAINT chk_exception_recovery_result CHECK (recovery_result IS NULL OR recovery_result IN ('SUCCESS', 'FAILED')),
    CONSTRAINT chk_exception_status CHECK (exception_status IN ('PENDING', 'PROCESSING', 'RESOLVED', 'IGNORED'))
);
CREATE INDEX idx_task_exception_task_id ON task_exceptions(task_id);
CREATE INDEX idx_task_exception_status ON task_exceptions(exception_status);
CREATE INDEX idx_task_exception_type ON task_exceptions(exception_type);
