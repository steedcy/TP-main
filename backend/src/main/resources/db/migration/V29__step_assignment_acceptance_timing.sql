-- DEF-S3-102: 支持记录步骤承接请求与响应耗时
ALTER TABLE task_step_assignments ADD COLUMN IF NOT EXISTS acceptance_requested_at TIMESTAMP;
ALTER TABLE task_step_assignments ADD COLUMN IF NOT EXISTS accepted_at TIMESTAMP;
ALTER TABLE task_step_assignments ADD COLUMN IF NOT EXISTS acceptance_duration_ms BIGINT;
