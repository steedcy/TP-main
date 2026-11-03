-- DEF-S3-089 / SRS_F013.R07: operation_logs.chk_op_log_result allowed only ('SUCCESS', 'FAILED', 'CANCELLED').
-- When an unauthorized force bypass of a validation-failed plan is attempted and hard-intercepted,
-- the audit operation result is recorded as INTERCEPTED.
-- Expand check constraint to allow ('SUCCESS', 'FAILED', 'CANCELLED', 'INTERCEPTED').
ALTER TABLE operation_logs DROP CONSTRAINT IF EXISTS chk_op_log_result;
ALTER TABLE operation_logs ADD CONSTRAINT chk_op_log_result CHECK (operation_result IN ('SUCCESS', 'FAILED', 'CANCELLED', 'INTERCEPTED'));
