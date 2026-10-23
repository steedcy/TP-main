-- 对应5.4.4计划三类校验"错误清单"界面元素。数据库设计说明书V2.0的plan_versions表
-- 只设计了三个校验结果字段（PASS/FAIL级别），未设计详细错误清单存储，此处补充。
ALTER TABLE plan_versions ADD COLUMN validation_errors JSON;
