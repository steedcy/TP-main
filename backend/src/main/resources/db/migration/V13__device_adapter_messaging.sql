-- Device-side credentials are stored as a one-way lookup hash plus encrypted material
-- needed by the platform when it calls the simulator. Plain tokens are never persisted.
ALTER TABLE devices
    ADD COLUMN device_token_hash VARCHAR(64),
    ADD COLUMN device_token_ciphertext TEXT,
    ADD COLUMN device_token_issued_at TIMESTAMP;

ALTER TABLE device_agents ADD COLUMN business_status JSONB;

CREATE TABLE device_commands (
    id BIGSERIAL PRIMARY KEY,
    command_id VARCHAR(32) NOT NULL,
    agent_code VARCHAR(32) NOT NULL,
    command_type VARCHAR(32) NOT NULL,
    attempt_no SMALLINT NOT NULL DEFAULT 0,
    task_id BIGINT,
    step_seq INT,
    capability_type VARCHAR(32),
    command_payload TEXT NOT NULL,
    command_status VARCHAR(24) NOT NULL DEFAULT 'PENDING',
    response_payload TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_device_command_agent FOREIGN KEY (agent_code) REFERENCES device_agents(agent_code),
    CONSTRAINT chk_device_command_attempt CHECK (attempt_no BETWEEN 0 AND 1),
    CONSTRAINT chk_device_command_status CHECK (command_status IN
        ('PENDING', 'DELIVERY_FAILED', 'SENT', 'ACCEPTED', 'REJECTED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'TIMED_OUT', 'CANCELLED')),
    CONSTRAINT uk_device_command_attempt UNIQUE (agent_code, command_id, command_type, attempt_no)
);
CREATE INDEX idx_device_command_task ON device_commands(task_id, step_seq);
CREATE INDEX idx_device_command_status ON device_commands(command_status, updated_at);

-- Duplicate device reports are acknowledged but never advance the task state twice.
CREATE TABLE device_command_reports (
    id BIGSERIAL PRIMARY KEY,
    agent_code VARCHAR(32) NOT NULL,
    command_id VARCHAR(32) NOT NULL,
    report_type VARCHAR(24) NOT NULL,
    attempt_no SMALLINT NOT NULL DEFAULT 0,
    payload_hash VARCHAR(64) NOT NULL,
    received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_device_report_agent FOREIGN KEY (agent_code) REFERENCES device_agents(agent_code),
    CONSTRAINT chk_device_report_attempt CHECK (attempt_no BETWEEN 0 AND 1),
    CONSTRAINT uk_device_command_report UNIQUE (agent_code, command_id, report_type, attempt_no)
);
CREATE INDEX idx_device_report_command ON device_command_reports(command_id);
