-- 4. 基线模板与风险规则模块
CREATE TABLE baseline_templates (
    id BIGSERIAL PRIMARY KEY,
    template_name VARCHAR(64) NOT NULL UNIQUE,
    task_family VARCHAR(32) NOT NULL,
    is_preset BOOLEAN NOT NULL DEFAULT FALSE,
    input_params JSON NOT NULL,
    steps JSON NOT NULL,
    template_version VARCHAR(16) NOT NULL DEFAULT 'V1.0',
    template_status VARCHAR(16) NOT NULL DEFAULT 'DRAFT',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(64),
    CONSTRAINT chk_template_status CHECK (template_status IN ('DRAFT', 'DRY_RUN_PASSED', 'ENABLED', 'DISABLED')),
    CONSTRAINT chk_template_task_family CHECK (task_family IN
        ('OVERSIZE_BAGGAGE_HANDLING', 'SPECIAL_PASSENGER_SERVICE', 'FLIGHT_CHANGE_RESPONSE', 'EXTENDED'))
);
CREATE INDEX idx_template_task_family ON baseline_templates(task_family);
CREATE INDEX idx_template_status ON baseline_templates(template_status);

CREATE TABLE risk_rules (
    id BIGSERIAL PRIMARY KEY,
    rule_code VARCHAR(64) NOT NULL UNIQUE,
    rule_content TEXT NOT NULL,
    rule_version VARCHAR(16) NOT NULL DEFAULT 'V1.0',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(64)
);

-- 5. 任务规划与执行模块
CREATE TABLE tasks (
    id BIGSERIAL PRIMARY KEY,
    task_code VARCHAR(32) NOT NULL UNIQUE,
    task_goal VARCHAR(500) NOT NULL,
    task_family VARCHAR(32),
    scene_params JSON,
    goal_parsing_result JSON,
    status VARCHAR(32) NOT NULL DEFAULT 'PLANNING',
    current_plan_version_id BIGINT,
    replan_used BOOLEAN NOT NULL DEFAULT FALSE,
    replanning_reason TEXT,
    manual_terminate_reason VARCHAR(200),
    failure_reason TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(64) NOT NULL,
    CONSTRAINT chk_task_status CHECK (status IN
        ('PLANNING', 'SUPERVISING', 'PENDING_ASSIGNMENT', 'DOWNGRADING', 'EXECUTING',
         'COMPLETED', 'FAILED', 'PENDING_MANUAL', 'MANUAL_TERMINATED'))
);
CREATE INDEX idx_task_status ON tasks(status);
CREATE INDEX idx_task_family ON tasks(task_family);
CREATE INDEX idx_task_created_at ON tasks(created_at);

CREATE TABLE plan_versions (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL,
    version_no INT NOT NULL,
    source VARCHAR(32) NOT NULL,
    baseline_template_id BIGINT,
    snapshot_id VARCHAR(32) NOT NULL,
    plan_steps JSON NOT NULL,
    structure_check_result VARCHAR(16),
    capability_check_result VARCHAR(16),
    constraint_check_result VARCHAR(16),
    risk_level VARCHAR(16),
    risk_reason_code VARCHAR(64),
    judgment_basis TEXT,
    confidence DECIMAL(4,3),
    rule_set_version VARCHAR(16),
    frozen_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_plan_version_task FOREIGN KEY (task_id) REFERENCES tasks(id),
    CONSTRAINT fk_plan_version_template FOREIGN KEY (baseline_template_id) REFERENCES baseline_templates(id),
    CONSTRAINT chk_plan_source CHECK (source IN ('AUTONOMOUS', 'BASELINE_TEMPLATE')),
    CONSTRAINT chk_plan_risk_level CHECK (risk_level IN ('LOW', 'HIGH', 'UNDETERMINED'))
);
CREATE UNIQUE INDEX uk_plan_version_no ON plan_versions(task_id, version_no);
CREATE INDEX idx_plan_version_task_id ON plan_versions(task_id);

CREATE TABLE task_step_assignments (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL,
    plan_version_id BIGINT NOT NULL,
    step_seq INT NOT NULL,
    device_agent_id BIGINT,
    command_id VARCHAR(32),
    step_status VARCHAR(16) NOT NULL DEFAULT 'PENDING_ASSIGNMENT',
    retry_count INT NOT NULL DEFAULT 0,
    execution_result VARCHAR(16),
    reason_code VARCHAR(64),
    output_params JSON,
    dispatched_at TIMESTAMP,
    feedback_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_step_assign_task FOREIGN KEY (task_id) REFERENCES tasks(id),
    CONSTRAINT fk_step_assign_plan_version FOREIGN KEY (plan_version_id) REFERENCES plan_versions(id),
    CONSTRAINT fk_step_assign_agent FOREIGN KEY (device_agent_id) REFERENCES device_agents(id),
    CONSTRAINT chk_step_status CHECK (step_status IN
        ('PENDING_ASSIGNMENT', 'EXECUTING', 'COMPLETED', 'FAILED', 'FROZEN')),
    CONSTRAINT chk_step_retry_count CHECK (retry_count <= 1)
);
CREATE UNIQUE INDEX uk_step_assign_seq ON task_step_assignments(plan_version_id, step_seq);
CREATE INDEX idx_step_assign_task_id ON task_step_assignments(task_id);
CREATE INDEX idx_step_assign_agent_id ON task_step_assignments(device_agent_id);
CREATE INDEX idx_step_assign_status ON task_step_assignments(step_status);

-- 6. 过程追溯与操作记录模块
CREATE TABLE task_events (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    occurred_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    trigger VARCHAR(16) NOT NULL DEFAULT 'SYSTEM',
    reason_code VARCHAR(64),
    detail_summary TEXT,
    CONSTRAINT fk_task_event_task FOREIGN KEY (task_id) REFERENCES tasks(id),
    CONSTRAINT chk_event_trigger CHECK (trigger IN ('SYSTEM', 'OPERATOR'))
);
CREATE INDEX idx_task_event_task_id ON task_events(task_id);
CREATE INDEX idx_task_event_occurred_at ON task_events(occurred_at);

CREATE TABLE operation_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    username VARCHAR(32) NOT NULL,
    role VARCHAR(32),
    operation_type VARCHAR(32) NOT NULL,
    operation_target VARCHAR(128),
    operation_result VARCHAR(16) NOT NULL,
    source_ip VARCHAR(64),
    detail JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_op_log_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT chk_op_log_result CHECK (operation_result IN ('SUCCESS', 'FAILED'))
);
CREATE INDEX idx_op_log_user_id ON operation_logs(user_id);
CREATE INDEX idx_op_log_type ON operation_logs(operation_type);
CREATE INDEX idx_op_log_created_at ON operation_logs(created_at);

-- task_events 仅追加约束：应用账号撤销 UPDATE/DELETE 权限
-- 部署时需将 app_user 替换为实际的应用数据库账号名
-- REVOKE UPDATE, DELETE ON task_events FROM app_user;
-- GRANT INSERT, SELECT ON task_events TO app_user;
