-- SRS_NF016.R01: 完善审计日志与事件长字段落库机制，扩宽受限 VARCHAR 列至 TEXT/宽字符类型，
-- 杜绝因长操作对象、长错误原因码或脱敏展开字符串引发的 SQL 截断或写库失败。
ALTER TABLE operation_logs ALTER COLUMN username TYPE VARCHAR(256);
ALTER TABLE operation_logs ALTER COLUMN role TYPE VARCHAR(64);
ALTER TABLE operation_logs ALTER COLUMN operation_type TYPE VARCHAR(64);
ALTER TABLE operation_logs ALTER COLUMN operation_target TYPE TEXT;
ALTER TABLE operation_logs ALTER COLUMN source_ip TYPE VARCHAR(128);

ALTER TABLE task_events ALTER COLUMN event_type TYPE VARCHAR(128);
ALTER TABLE task_events ALTER COLUMN reason_code TYPE VARCHAR(256);

ALTER TABLE device_events ALTER COLUMN event_type TYPE VARCHAR(128);
ALTER TABLE device_events ALTER COLUMN reason_code TYPE VARCHAR(256);
ALTER TABLE device_events ALTER COLUMN command_id TYPE VARCHAR(64);
ALTER TABLE device_events ALTER COLUMN result TYPE VARCHAR(64);
