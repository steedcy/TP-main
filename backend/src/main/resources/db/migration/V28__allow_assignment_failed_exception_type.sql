-- DEF-S3-099: 支持 ASSIGNMENT_FAILED 异常类型进入 task_exceptions 检查约束
ALTER TABLE task_exceptions DROP CONSTRAINT IF EXISTS chk_exception_type;
ALTER TABLE task_exceptions ADD CONSTRAINT chk_exception_type CHECK (
    exception_type IN ('AGENT_OFFLINE', 'CAPABILITY_GAP', 'EXECUTION_TIMEOUT', 'STEP_FAILED', 'REPLAN_FAILED', 'ASSIGNMENT_FAILED')
);
