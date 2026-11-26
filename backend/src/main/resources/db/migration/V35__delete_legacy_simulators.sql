-- 彻底删除旧的 20 台 F2 仿真体设备及相关外键引用，仅保留本轮新建的 20 台仿真体

UPDATE task_step_assignments
SET device_agent_id = NULL
WHERE device_agent_id IN (
    SELECT a.id FROM device_agents a
    JOIN devices d ON a.device_id = d.id
    WHERE d.device_code LIKE 'SIM_F2_%' OR d.device_code LIKE 'F2_%'
);

DELETE FROM device_command_reports
WHERE agent_code IN (
    SELECT a.agent_code FROM device_agents a
    JOIN devices d ON a.device_id = d.id
    WHERE d.device_code LIKE 'SIM_F2_%' OR d.device_code LIKE 'F2_%'
);

DELETE FROM device_commands
WHERE agent_code IN (
    SELECT a.agent_code FROM device_agents a
    JOIN devices d ON a.device_id = d.id
    WHERE d.device_code LIKE 'SIM_F2_%' OR d.device_code LIKE 'F2_%'
);

DELETE FROM device_events
WHERE device_agent_id IN (
    SELECT a.id FROM device_agents a
    JOIN devices d ON a.device_id = d.id
    WHERE d.device_code LIKE 'SIM_F2_%' OR d.device_code LIKE 'F2_%'
);

DELETE FROM dry_run_device_selections
WHERE device_agent_id IN (
    SELECT a.id FROM device_agents a
    JOIN devices d ON a.device_id = d.id
    WHERE d.device_code LIKE 'SIM_F2_%' OR d.device_code LIKE 'F2_%'
);

DELETE FROM device_agents
WHERE device_id IN (
    SELECT id FROM devices WHERE device_code LIKE 'SIM_F2_%' OR device_code LIKE 'F2_%'
);

DELETE FROM device_capabilities
WHERE device_id IN (
    SELECT id FROM devices WHERE device_code LIKE 'SIM_F2_%' OR device_code LIKE 'F2_%'
);

DELETE FROM devices
WHERE device_code LIKE 'SIM_F2_%' OR device_code LIKE 'F2_%';
