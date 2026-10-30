-- SRS_F005 / DEF-S3-015: runtime-adjustable settings (first use: heartbeat timeout, 10~120s, default 30s).
-- An absent row means "use the configured default".
CREATE TABLE system_settings (
    setting_key VARCHAR(64) PRIMARY KEY,
    setting_value VARCHAR(256) NOT NULL,
    updated_by VARCHAR(64),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
