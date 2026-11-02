-- DEF-S3-087 / SRS_F009.R08: operation_logs.chk_op_log_result allowed only ('SUCCESS', 'FAILED').
-- When a baseline template dry-run is manually cancelled, the operation result is recorded as CANCELLED
-- (DEF-S3-086), causing PostgreSQL check constraint violation and HTTP 500 transaction rollback.
-- Expand the check constraint to allow ('SUCCESS', 'FAILED', 'CANCELLED').
ALTER TABLE operation_logs DROP CONSTRAINT IF EXISTS chk_op_log_result;
ALTER TABLE operation_logs ADD CONSTRAINT chk_op_log_result CHECK (operation_result IN ('SUCCESS', 'FAILED', 'CANCELLED'));
