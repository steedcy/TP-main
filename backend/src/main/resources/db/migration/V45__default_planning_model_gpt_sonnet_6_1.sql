-- 将规划模型运行配置统一更新为默认仅使用第二模型 gpt-sonnet-6.1 (SECONDARY_ONLY)
-- 保留已保存的 API Key 与 Base URL 不变
INSERT INTO system_settings (setting_key, setting_value, updated_by, updated_at)
VALUES
    ('planning.active.mode', 'SECONDARY_ONLY', 'system', CURRENT_TIMESTAMP),
    ('planning.fallback.enabled', 'false', 'system', CURRENT_TIMESTAMP),
    ('planning.claude.model', 'gpt-sonnet-6.1', 'system', CURRENT_TIMESTAMP)
ON CONFLICT (setting_key) DO UPDATE SET
    setting_value = EXCLUDED.setting_value,
    updated_by = EXCLUDED.updated_by,
    updated_at = CURRENT_TIMESTAMP;
