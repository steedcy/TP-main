-- 对应5.6.1任务族可扩展化改造：baseline_templates.task_family此前受限于硬编码4值枚举
-- CHECK约束（V2迁移遗留），配置管理员新增扩展任务定义后其definitionCode（如EXT_xxxxxxxx）
-- 无法通过该约束，导致扩展任务族永远配不出对应的降级基线模板。task_family合法性校验
-- 已迁移至应用层BaselineTemplateService.create()查询task_definitions表，数据库层不再
-- 需要重复此约束。
ALTER TABLE baseline_templates DROP CONSTRAINT IF EXISTS chk_template_task_family;
