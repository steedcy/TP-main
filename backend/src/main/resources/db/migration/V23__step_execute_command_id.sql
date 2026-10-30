-- DEF-S3-049 / SRS_F007.R02 (BL-003 option B): every downstream logical message gets its own command id.
-- command_id stays the TASK_ACCEPT id; the EXECUTE_CAPABILITY message gets execute_command_id (kept across its own
-- retry, attempt_no tells attempts apart); TASK_CANCEL ids are generated per cancel request and never stored here.
-- Rows created before this migration keep NULL and are still correlated by command_id.
ALTER TABLE task_step_assignments ADD COLUMN execute_command_id VARCHAR(32);
CREATE INDEX idx_step_assignment_execute_command ON task_step_assignments(execute_command_id);
