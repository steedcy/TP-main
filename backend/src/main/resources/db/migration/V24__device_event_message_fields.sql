-- DEF-S3-082 / SRS_F007.R07: unified-message device events carry a structured command id and result,
-- so the agent timeline can show them directly instead of only inside the summary text.
-- Other event types leave both columns NULL.
ALTER TABLE device_events ADD COLUMN command_id VARCHAR(32);
ALTER TABLE device_events ADD COLUMN result VARCHAR(24);
CREATE INDEX idx_device_event_command ON device_events(command_id);
