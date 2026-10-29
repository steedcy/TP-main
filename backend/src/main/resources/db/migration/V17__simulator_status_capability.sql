-- DEF-S3-020 / SRS_F003.R04: simulators must carry the simulation-status generation capability.
-- Back-fill existing simulators that lack it. Status is UNTESTED: it must pass a capability test before enabling.
INSERT INTO device_capabilities (device_id, capability_code, capability_name, capability_type,
                                 input_params, output_params, capability_status, capability_description)
SELECT d.id, 'CAP_SIM_STATUS', '仿真状态生成', 'CAP_SIM_STATUS', '[]'::json, '[]'::json, 'UNTESTED',
       '仿真体生成并上报模拟设备状态'
FROM devices d
WHERE d.is_simulator = TRUE
  AND d.device_status <> 'DELETED'
  AND NOT EXISTS (SELECT 1 FROM device_capabilities c
                  WHERE c.device_id = d.id AND c.capability_code = 'CAP_SIM_STATUS');
