-- 对应《数据库设计说明书》V2.0 第4节数据表设计
-- 1. 用户认证模块
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(32) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    real_name VARCHAR(32) NOT NULL,
    role VARCHAR(32) NOT NULL,
    contact VARCHAR(128) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
    failed_login_attempts INT NOT NULL DEFAULT 0,
    locked_at TIMESTAMP,
    locked_reason VARCHAR(255),
    last_login_at TIMESTAMP,
    last_failed_login_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(64),
    CONSTRAINT chk_users_status CHECK (status IN ('ACTIVE', 'INACTIVE', 'LOCKED')),
    CONSTRAINT chk_users_role CHECK (role IN ('SYSTEM_ADMIN', 'OPERATOR', 'CONFIG_ADMIN'))
);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_role ON users(role);

-- 2. 设备类型能力边界与能力画像模块
CREATE TABLE device_type_capability (
    id BIGSERIAL PRIMARY KEY,
    device_type_code VARCHAR(32) NOT NULL UNIQUE,
    device_type_name VARCHAR(64) NOT NULL,
    supported_capability_types JSON NOT NULL,
    type_description TEXT,
    constraint_rules TEXT,
    typical_scenarios TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(64)
);

CREATE TABLE capability_template (
    id BIGSERIAL PRIMARY KEY,
    device_type_code VARCHAR(32) NOT NULL,
    template_code VARCHAR(32) NOT NULL,
    template_name VARCHAR(64) NOT NULL,
    capability_type VARCHAR(32) NOT NULL,
    input_params JSON NOT NULL,
    output_params JSON NOT NULL,
    template_version VARCHAR(16) NOT NULL DEFAULT 'V1.0',
    template_status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
    template_description TEXT,
    usage_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_cap_template_device_type FOREIGN KEY (device_type_code)
        REFERENCES device_type_capability(device_type_code),
    CONSTRAINT chk_cap_template_status CHECK (template_status IN ('ACTIVE', 'INACTIVE'))
);
CREATE UNIQUE INDEX uk_cap_template_code ON capability_template(device_type_code, template_code);
CREATE INDEX idx_cap_template_type ON capability_template(device_type_code);
CREATE INDEX idx_cap_template_cap_type ON capability_template(capability_type);

-- 3. 设备接入与代理管理模块
CREATE TABLE devices (
    id BIGSERIAL PRIMARY KEY,
    device_code VARCHAR(32) NOT NULL UNIQUE,
    device_name VARCHAR(64) NOT NULL,
    device_type_code VARCHAR(32) NOT NULL,
    is_simulator BOOLEAN NOT NULL DEFAULT FALSE,
    simulated_device_type VARCHAR(32),
    area_code VARCHAR(32) NOT NULL,
    position_x DECIMAL(10,2) NOT NULL,
    position_y DECIMAL(10,2) NOT NULL,
    access_endpoint VARCHAR(255) NOT NULL,
    access_credential_ref VARCHAR(128) NOT NULL,
    status_report_interval INT NOT NULL DEFAULT 15,
    connection_test_status VARCHAR(16) NOT NULL DEFAULT 'UNTESTED',
    connection_test_result TEXT,
    remark VARCHAR(200),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    CONSTRAINT fk_device_type FOREIGN KEY (device_type_code)
        REFERENCES device_type_capability(device_type_code),
    CONSTRAINT chk_device_conn_test_status CHECK (connection_test_status IN ('UNTESTED', 'PASSED', 'FAILED')),
    CONSTRAINT chk_device_report_interval CHECK (status_report_interval BETWEEN 5 AND 60)
);
CREATE INDEX idx_device_type ON devices(device_type_code);
CREATE INDEX idx_device_area ON devices(area_code);

CREATE TABLE device_agents (
    id BIGSERIAL PRIMARY KEY,
    agent_code VARCHAR(32) NOT NULL UNIQUE,
    device_id BIGINT NOT NULL,
    agent_status VARCHAR(16) NOT NULL DEFAULT 'ENABLED',
    online_status VARCHAR(16) NOT NULL DEFAULT 'OFFLINE',
    work_status VARCHAR(16) NOT NULL DEFAULT 'IDLE',
    current_task_id BIGINT,
    current_step_seq INT,
    last_reported_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_device_agent_device FOREIGN KEY (device_id) REFERENCES devices(id),
    CONSTRAINT uk_device_agent_device UNIQUE (device_id),
    CONSTRAINT chk_agent_status CHECK (agent_status IN ('ENABLED', 'DISABLED', 'ARCHIVED')),
    CONSTRAINT chk_online_status CHECK (online_status IN ('ONLINE', 'OFFLINE')),
    CONSTRAINT chk_work_status CHECK (work_status IN ('IDLE', 'BUSY'))
);
CREATE INDEX idx_agent_online_status ON device_agents(online_status);
CREATE INDEX idx_agent_work_status ON device_agents(work_status);

CREATE TABLE device_capabilities (
    id BIGSERIAL PRIMARY KEY,
    device_id BIGINT NOT NULL,
    template_id BIGINT,
    capability_code VARCHAR(32) NOT NULL,
    capability_name VARCHAR(64) NOT NULL,
    capability_type VARCHAR(32) NOT NULL,
    input_params JSON NOT NULL,
    output_params JSON NOT NULL,
    applicable_conditions VARCHAR(200),
    capability_status VARCHAR(16) NOT NULL DEFAULT 'UNTESTED',
    test_result TEXT,
    last_test_at TIMESTAMP,
    capability_description VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_device_cap_device FOREIGN KEY (device_id) REFERENCES devices(id),
    CONSTRAINT fk_device_cap_template FOREIGN KEY (template_id) REFERENCES capability_template(id),
    CONSTRAINT chk_cap_status CHECK (capability_status IN ('UNTESTED', 'TESTED_PASSED', 'TESTED_FAILED', 'ENABLED', 'DISABLED'))
);
CREATE UNIQUE INDEX uk_device_cap_code ON device_capabilities(device_id, capability_code);
CREATE INDEX idx_device_cap_device_id ON device_capabilities(device_id);
CREATE INDEX idx_device_cap_type ON device_capabilities(capability_type);
CREATE INDEX idx_device_cap_status ON device_capabilities(capability_status);
