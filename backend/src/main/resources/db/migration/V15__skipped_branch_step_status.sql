ALTER TABLE task_step_assignments DROP CONSTRAINT chk_step_status;
ALTER TABLE task_step_assignments ADD CONSTRAINT chk_step_status CHECK (step_status IN
    ('PENDING_ASSIGNMENT', 'EXECUTING', 'COMPLETED', 'FAILED', 'FROZEN', 'SKIPPED'));
