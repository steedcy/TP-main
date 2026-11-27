-- 将第二模型标识修正为 gpt-6.1-sol（保持默认仅使用第二模型 SECONDARY_ONLY 不变，且保留既有 API Key 与 Base URL）
INSERT INTO system_settings (setting_key, setting_value, updated_by, updated_at)
VALUES
    ('planning.claude.model', 'gpt-6.1-sol', 'system', CURRENT_TIMESTAMP)
ON CONFLICT (setting_key) DO UPDATE SET
    setting_value = EXCLUDED.setting_value,
    updated_by = EXCLUDED.updated_by,
    updated_at = CURRENT_TIMESTAMP;
