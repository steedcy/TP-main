-- V2建表时step_status varchar(16)容不下'PENDING_ASSIGNMENT'(18字符)本身，此前从未有代码
-- 真正写入过这个默认值以外的场景（本次5.5实现是首次实际执行INSERT/UPDATE），暴露该缺陷。
ALTER TABLE task_step_assignments ALTER COLUMN step_status TYPE VARCHAR(32);
