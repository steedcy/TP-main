-- 自定义候机楼矢量室内地图（2000 x 600）及 20 台仿真体设备布局

-- 1. 清理旧演示地图点位与区域，写入从布局图提取的矢量区域与设施点位
DELETE FROM terminal_pois;
DELETE FROM terminal_map_regions;

INSERT INTO terminal_map_regions (region_code, region_name, region_type, geometry_json, created_by)
VALUES
    ('REG_HOLDING_ZONE', '候机区（安检隔离区内）', 'ISOLATED_ZONE',
     '[{"x":40,"y":40},{"x":1960,"y":40},{"x":1960,"y":235},{"x":40,"y":235}]', 'system'),
    ('REG_CHECKIN_HALL', '值机区（安检隔离区外）', 'CHECKIN_HALL',
     '[{"x":40,"y":341},{"x":1960,"y":341},{"x":1960,"y":520},{"x":40,"y":520}]', 'system'),
    ('REG_SECURITY_PASS', '中央安检通道区域（可通行）', 'SECURITY_AREA',
     '[{"x":880,"y":235},{"x":1196,"y":235},{"x":1196,"y":341},{"x":880,"y":341}]', 'system'),
    ('REG_SHOP_BLOCK_W', '西侧商铺及设施区（不可通行）', 'SHOP_BLOCK',
     '[{"x":40,"y":235},{"x":880,"y":235},{"x":880,"y":341},{"x":40,"y":341}]', 'system'),
    ('REG_SHOP_BLOCK_E', '东侧商铺及设施区（不可通行）', 'SHOP_BLOCK',
     '[{"x":1196,"y":235},{"x":1960,"y":235},{"x":1960,"y":341},{"x":1196,"y":341}]', 'system'),
    ('CORR_HOLDING_MAIN', '候机区东西主通道', 'CORRIDOR',
     '[{"x":133,"y":115},{"x":239,"y":115},{"x":482,"y":115},{"x":719,"y":115},{"x":1028,"y":115},{"x":1257,"y":115},{"x":1493,"y":115},{"x":1877,"y":115}]', 'system'),
    ('CORR_HOLDING_CENTER', '候机区中轴通道', 'CORRIDOR',
     '[{"x":1028,"y":115},{"x":1028,"y":170},{"x":1038,"y":235}]', 'system'),
    ('CORR_SECURITY_MAIN', '安检通道贯通走廊', 'CORRIDOR',
     '[{"x":1038,"y":235},{"x":1038,"y":288},{"x":1038,"y":341}]', 'system'),
    ('CORR_CHECKIN_CENTER', '值机区中轴出入口通道', 'CORRIDOR',
     '[{"x":1038,"y":341},{"x":1038,"y":425},{"x":1036,"y":520}]', 'system'),
    ('CORR_CHECKIN_MAIN', '值机区东西主通道', 'CORRIDOR',
     '[{"x":133,"y":425},{"x":311,"y":425},{"x":520,"y":425},{"x":717,"y":425},{"x":1038,"y":425},{"x":1280,"y":425},{"x":1399,"y":425},{"x":1660,"y":425},{"x":1877,"y":425}]', 'system'),
    ('CORR_GATE_1_2', '1-2号登机口通道', 'CORRIDOR',
     '[{"x":133,"y":56},{"x":133,"y":115},{"x":239,"y":115},{"x":239,"y":56}]', 'system'),
    ('CORR_GATE_3', '3号登机口通道', 'CORRIDOR', '[{"x":482,"y":115},{"x":482,"y":57}]', 'system'),
    ('CORR_GATE_4', '4号登机口通道', 'CORRIDOR', '[{"x":719,"y":115},{"x":719,"y":56}]', 'system'),
    ('CORR_GATE_5', '5号登机口通道', 'CORRIDOR', '[{"x":1028,"y":115},{"x":1022,"y":57}]', 'system'),
    ('CORR_GATE_6', '6号登机口通道', 'CORRIDOR', '[{"x":1257,"y":115},{"x":1257,"y":56}]', 'system'),
    ('CORR_GATE_7', '7号登机口通道', 'CORRIDOR', '[{"x":1493,"y":115},{"x":1493,"y":57}]', 'system'),
    ('CORR_GATE_8', '8号登机口通道', 'CORRIDOR', '[{"x":1877,"y":115},{"x":1877,"y":56}]', 'system'),
    ('CORR_ENT_1', '1号出入口支线', 'CORRIDOR', '[{"x":311,"y":425},{"x":311,"y":520}]', 'system'),
    ('CORR_ENT_2', '2号出入口支线', 'CORRIDOR', '[{"x":717,"y":425},{"x":717,"y":520}]', 'system'),
    ('CORR_ENT_4', '4号出入口支线', 'CORRIDOR', '[{"x":1399,"y":425},{"x":1399,"y":520}]', 'system'),
    ('CORR_ENT_5', '5号出入口支线', 'CORRIDOR', '[{"x":1877,"y":425},{"x":1877,"y":520}]', 'system');

INSERT INTO terminal_pois (poi_code, poi_name, category, pos_x, pos_y, zone_name, linked_device_code, created_by)
VALUES
    ('GATE_01', '1号登机口', 'GATE', 133, 56, '候机区-西', NULL, 'system'),
    ('GATE_02', '2号登机口', 'GATE', 239, 56, '候机区-西', NULL, 'system'),
    ('GATE_03', '3号登机口', 'GATE', 482, 57, '候机区-西', NULL, 'system'),
    ('GATE_04', '4号登机口', 'GATE', 719, 56, '候机区-西', NULL, 'system'),
    ('GATE_05', '5号登机口', 'GATE', 1022, 57, '候机区-中', NULL, 'system'),
    ('GATE_06', '6号登机口', 'GATE', 1257, 56, '候机区-东', NULL, 'system'),
    ('GATE_07', '7号登机口', 'GATE', 1493, 57, '候机区-东', NULL, 'system'),
    ('GATE_08', '8号登机口', 'GATE', 1877, 56, '候机区-东', NULL, 'system'),
    ('SERVICE_DESK', '候机区服务台', 'SERVICE', 1028, 135, '候机区-中', 'SIM_DISPLAY_H2', 'system'),
    ('FAC_WATER_N1', '候机区饮用水(西)', 'FACILITY', 719, 138, '候机区-西', NULL, 'system'),
    ('FAC_WATER_N2', '候机区饮用水(东)', 'FACILITY', 1257, 149, '候机区-东', NULL, 'system'),
    ('FAC_ELEV_N1', '候机区电扶梯(西)', 'FACILITY', 515, 179, '候机区-西', NULL, 'system'),
    ('FAC_ELEV_N2', '候机区电扶梯(东)', 'FACILITY', 1543, 179, '候机区-东', NULL, 'system'),
    ('SECURITY_MAIN', '中央安检通道', 'SECURITY', 1037, 286, '中央安检区', NULL, 'system'),
    ('SHOP_FOOD_M1', '中央餐饮区(西)', 'SHOP', 380, 261, '西侧商铺区', NULL, 'system'),
    ('SHOP_M1', '中央商店(西1)', 'SHOP', 536, 261, '西侧商铺区', NULL, 'system'),
    ('FAC_FIRSTAID', '急救中心', 'FACILITY', 681, 254, '西侧商铺区', NULL, 'system'),
    ('SHOP_M2', '中央商店(西2)', 'SHOP', 745, 257, '西侧商铺区', NULL, 'system'),
    ('BAGGAGE_CLAIM_W', '行李查询/提取(西)', 'BAGGAGE', 850, 318, '西侧商铺区', NULL, 'system'),
    ('BAGGAGE_CLAIM_E', '行李查询/提取(东)', 'BAGGAGE', 1228, 317, '东侧商铺区', NULL, 'system'),
    ('SHOP_M3', '中央商店(东1)', 'SHOP', 1273, 257, '东侧商铺区', NULL, 'system'),
    ('SHOP_M4', '中央商店(东2)', 'SHOP', 1346, 259, '东侧商铺区', NULL, 'system'),
    ('SHOP_FOOD_M2', '中央餐饮区(东)', 'SHOP', 1668, 263, '东侧商铺区', NULL, 'system'),
    ('LOUNGE_VIP', '头等舱候机休息室', 'SERVICE', 1720, 264, '东侧商铺区', NULL, 'system'),
    ('SHOP_FOOD_S1', '值机区餐饮(西)', 'SHOP', 578, 407, '值机区-西', NULL, 'system'),
    ('SHOP_S2', '值机区商店(东)', 'SHOP', 1479, 403, '值机区-东', NULL, 'system'),
    ('CHECKIN_WEST', '值机办理区(西)', 'CHECKIN', 896, 435, '值机区-西', NULL, 'system'),
    ('CHECKIN_EAST', '值机办理区(东)', 'CHECKIN', 1164, 434, '值机区-东', NULL, 'system'),
    ('MEASURE_WEST', '智能行李测量点(左)', 'MEASURE', 520, 425, '值机区-西', 'SIM_SCANNER_W', 'system'),
    ('MEASURE_EAST', '智能行李测量点(右)', 'MEASURE', 1420, 425, '值机区-东', 'SIM_SCANNER_E', 'system'),
    ('ENTRANCE_01', '1号出入口', 'FACILITY', 311, 520, '值机区-南', NULL, 'system'),
    ('ENTRANCE_02', '2号出入口', 'FACILITY', 717, 520, '值机区-南', NULL, 'system'),
    ('ENTRANCE_03', '3号出入口(主入口)', 'FACILITY', 1036, 520, '值机区-南', NULL, 'system'),
    ('ENTRANCE_04', '4号出入口', 'FACILITY', 1399, 520, '值机区-南', NULL, 'system'),
    ('ENTRANCE_05', '5号出入口', 'FACILITY', 1877, 520, '值机区-南', NULL, 'system');

-- 2. 停用旧 F2 演示设备，写入新布局对应的 20 台仿真体设备
UPDATE device_agents
SET agent_status = 'DISABLED', online_status = 'OFFLINE', work_status = 'IDLE', updated_at = CURRENT_TIMESTAMP
WHERE device_id IN (SELECT id FROM devices WHERE device_code LIKE 'SIM_F2_%' OR device_code LIKE 'F2_%');

UPDATE devices
SET device_status = 'INACTIVE', updated_at = CURRENT_TIMESTAMP
WHERE device_code LIKE 'SIM_F2_%' OR device_code LIKE 'F2_%';

INSERT INTO devices (
    device_code, device_name, device_type_code, is_simulator, simulated_device_type,
    area_code, position_x, position_y, access_endpoint, access_credential_ref,
    status_report_interval, connection_test_status, device_status, onboarding_status, remark, created_by
)
VALUES
    -- 1. 智能行李测量设备（共2台，1左1右均在值机区）
    ('SIM_SCANNER_W', '智能行李测量设备-值机左', 'SIMULATOR', TRUE, 'BAGGAGE_SCANNER', 'CHECKIN_WEST', 520, 425, 'http://127.0.0.1:18101', 'local-sim/SIM_SCANNER_W', 5, 'PASSED', 'ACTIVE', 'MANUAL', '值机区左侧行李测量', 'system'),
    ('SIM_SCANNER_E', '智能行李测量设备-值机右', 'SIMULATOR', TRUE, 'BAGGAGE_SCANNER', 'CHECKIN_EAST', 1420, 425, 'http://127.0.0.1:18102', 'local-sim/SIM_SCANNER_E', 5, 'PASSED', 'ACTIVE', 'MANUAL', '值机区右侧行李测量', 'system'),
    -- 2. 智慧航显（共5台，值机区2台，候机区3台）
    ('SIM_DISPLAY_C1', '智慧航显-值机左', 'SIMULATOR', TRUE, 'SMART_DISPLAY', 'CHECKIN_WEST', 680, 445, 'http://127.0.0.1:18103', 'local-sim/SIM_DISPLAY_C1', 5, 'PASSED', 'ACTIVE', 'MANUAL', '值机区左侧智慧航显', 'system'),
    ('SIM_DISPLAY_C2', '智慧航显-值机右', 'SIMULATOR', TRUE, 'SMART_DISPLAY', 'CHECKIN_EAST', 1280, 445, 'http://127.0.0.1:18104', 'local-sim/SIM_DISPLAY_C2', 5, 'PASSED', 'ACTIVE', 'MANUAL', '值机区右侧智慧航显', 'system'),
    ('SIM_DISPLAY_H1', '智慧航显-候机西', 'SIMULATOR', TRUE, 'SMART_DISPLAY', 'HOLDING_WEST', 380, 145, 'http://127.0.0.1:18105', 'local-sim/SIM_DISPLAY_H1', 5, 'PASSED', 'ACTIVE', 'MANUAL', '候机区西侧智慧航显', 'system'),
    ('SIM_DISPLAY_H2', '智慧航显-候机中', 'SIMULATOR', TRUE, 'SMART_DISPLAY', 'HOLDING_CENTER', 1028, 165, 'http://127.0.0.1:18106', 'local-sim/SIM_DISPLAY_H2', 5, 'PASSED', 'ACTIVE', 'MANUAL', '候机区服务台旁智慧航显', 'system'),
    ('SIM_DISPLAY_H3', '智慧航显-候机东', 'SIMULATOR', TRUE, 'SMART_DISPLAY', 'HOLDING_EAST', 1620, 145, 'http://127.0.0.1:18107', 'local-sim/SIM_DISPLAY_H3', 5, 'PASSED', 'ACTIVE', 'MANUAL', '候机区东侧智慧航显', 'system'),
    -- 3. 航延屏（共6台，候机区3/4/5/6号登机口附近各1台，值机区左右各1台）
    ('SIM_DELAY_G3', '航延屏-3号登机口', 'SIMULATOR', TRUE, 'FLIGHT_DELAY_BOARD', 'HOLDING_WEST', 482, 85, 'http://127.0.0.1:18108', 'local-sim/SIM_DELAY_G3', 5, 'PASSED', 'ACTIVE', 'MANUAL', '3号登机口附近航延屏', 'system'),
    ('SIM_DELAY_G4', '航延屏-4号登机口', 'SIMULATOR', TRUE, 'FLIGHT_DELAY_BOARD', 'HOLDING_WEST', 719, 85, 'http://127.0.0.1:18109', 'local-sim/SIM_DELAY_G4', 5, 'PASSED', 'ACTIVE', 'MANUAL', '4号登机口附近航延屏', 'system'),
    ('SIM_DELAY_G5', '航延屏-5号登机口', 'SIMULATOR', TRUE, 'FLIGHT_DELAY_BOARD', 'HOLDING_CENTER', 1022, 85, 'http://127.0.0.1:18110', 'local-sim/SIM_DELAY_G5', 5, 'PASSED', 'ACTIVE', 'MANUAL', '5号登机口附近航延屏', 'system'),
    ('SIM_DELAY_G6', '航延屏-6号登机口', 'SIMULATOR', TRUE, 'FLIGHT_DELAY_BOARD', 'HOLDING_EAST', 1257, 85, 'http://127.0.0.1:18111', 'local-sim/SIM_DELAY_G6', 5, 'PASSED', 'ACTIVE', 'MANUAL', '6号登机口附近航延屏', 'system'),
    ('SIM_DELAY_C1', '航延屏-值机左', 'SIMULATOR', TRUE, 'FLIGHT_DELAY_BOARD', 'CHECKIN_WEST', 360, 465, 'http://127.0.0.1:18112', 'local-sim/SIM_DELAY_C1', 5, 'PASSED', 'ACTIVE', 'MANUAL', '值机区左侧航延屏', 'system'),
    ('SIM_DELAY_C2', '航延屏-值机右', 'SIMULATOR', TRUE, 'FLIGHT_DELAY_BOARD', 'CHECKIN_EAST', 1660, 465, 'http://127.0.0.1:18113', 'local-sim/SIM_DELAY_C2', 5, 'PASSED', 'ACTIVE', 'MANUAL', '值机区右侧航延屏', 'system'),
    -- 4. 移动服务机器人（共7台，值机区3台，候机区4台）
    ('SIM_ROBOT_C1', '移动服务机器人-值机西', 'SIMULATOR', TRUE, 'MOBILE_ROBOT', 'CHECKIN_WEST', 440, 405, 'http://127.0.0.1:18114', 'local-sim/SIM_ROBOT_C1', 5, 'PASSED', 'ACTIVE', 'MANUAL', '值机区西侧机器人', 'system'),
    ('SIM_ROBOT_C2', '移动服务机器人-值机中', 'SIMULATOR', TRUE, 'MOBILE_ROBOT', 'CHECKIN_CENTER', 1038, 415, 'http://127.0.0.1:18115', 'local-sim/SIM_ROBOT_C2', 5, 'PASSED', 'ACTIVE', 'MANUAL', '值机区中轴机器人', 'system'),
    ('SIM_ROBOT_C3', '移动服务机器人-值机东', 'SIMULATOR', TRUE, 'MOBILE_ROBOT', 'CHECKIN_EAST', 1520, 405, 'http://127.0.0.1:18116', 'local-sim/SIM_ROBOT_C3', 5, 'PASSED', 'ACTIVE', 'MANUAL', '值机区东侧机器人', 'system'),
    ('SIM_ROBOT_H1', '移动服务机器人-候机西', 'SIMULATOR', TRUE, 'MOBILE_ROBOT', 'HOLDING_WEST', 280, 120, 'http://127.0.0.1:18117', 'local-sim/SIM_ROBOT_H1', 5, 'PASSED', 'ACTIVE', 'MANUAL', '候机区西侧机器人', 'system'),
    ('SIM_ROBOT_H2', '移动服务机器人-候机中西', 'SIMULATOR', TRUE, 'MOBILE_ROBOT', 'HOLDING_CENTER', 780, 145, 'http://127.0.0.1:18118', 'local-sim/SIM_ROBOT_H2', 5, 'PASSED', 'ACTIVE', 'MANUAL', '候机区中偏西机器人', 'system'),
    ('SIM_ROBOT_H3', '移动服务机器人-候机中东', 'SIMULATOR', TRUE, 'MOBILE_ROBOT', 'HOLDING_CENTER', 1200, 145, 'http://127.0.0.1:18119', 'local-sim/SIM_ROBOT_H3', 5, 'PASSED', 'ACTIVE', 'MANUAL', '候机区中偏东机器人', 'system'),
    ('SIM_ROBOT_H4', '移动服务机器人-候机东', 'SIMULATOR', TRUE, 'MOBILE_ROBOT', 'HOLDING_EAST', 1750, 120, 'http://127.0.0.1:18120', 'local-sim/SIM_ROBOT_H4', 5, 'PASSED', 'ACTIVE', 'MANUAL', '候机区东侧机器人', 'system')
ON CONFLICT (device_code) DO UPDATE SET
    device_name = EXCLUDED.device_name,
    simulated_device_type = EXCLUDED.simulated_device_type,
    area_code = EXCLUDED.area_code,
    position_x = EXCLUDED.position_x,
    position_y = EXCLUDED.position_y,
    access_endpoint = EXCLUDED.access_endpoint,
    device_status = 'ACTIVE',
    connection_test_status = 'PASSED',
    updated_at = CURRENT_TIMESTAMP;

-- 为 20 台设备写入启用能力
INSERT INTO device_capabilities (device_id, capability_code, capability_name, capability_type, input_params, output_params, capability_status)
SELECT d.id, 'CAP_BAGGAGE_MEASURE', '行李尺寸重量测量', 'CAP_BAGGAGE_MEASURE',
       '[{"name":"baggageLocation","type":"String","required":true,"defaultValue":"值机区"}]'::json,
       '[{"name":"length","type":"Double","required":true},{"name":"width","type":"Double","required":true},{"name":"height","type":"Double","required":true},{"name":"weight","type":"Double","required":true},{"name":"isOversize","type":"Boolean","required":true}]'::json,
       'ENABLED'
FROM devices d WHERE d.simulated_device_type = 'BAGGAGE_SCANNER' AND d.device_status = 'ACTIVE'
  AND NOT EXISTS (SELECT 1 FROM device_capabilities c WHERE c.device_id = d.id AND c.capability_code = 'CAP_BAGGAGE_MEASURE');

INSERT INTO device_capabilities (device_id, capability_code, capability_name, capability_type, input_params, output_params, capability_status)
SELECT d.id, 'CAP_OVERSIZE_ALERT', '超规事件上报', 'CAP_OVERSIZE_ALERT',
       '[{"name":"location","type":"String","required":true,"defaultValue":"值机区"}]'::json,
       '[{"name":"alertStatus","type":"String","required":true}]'::json,
       'ENABLED'
FROM devices d WHERE d.simulated_device_type = 'BAGGAGE_SCANNER' AND d.device_status = 'ACTIVE'
  AND NOT EXISTS (SELECT 1 FROM device_capabilities c WHERE c.device_id = d.id AND c.capability_code = 'CAP_OVERSIZE_ALERT');

INSERT INTO device_capabilities (device_id, capability_code, capability_name, capability_type, input_params, output_params, capability_status)
SELECT d.id, 'CAP_INFO_DISPLAY', '综合信息展示', 'CAP_INFO_DISPLAY',
       '[{"name":"contentType","type":"String","required":true,"defaultValue":"TEXT"},{"name":"contentData","type":"String","required":true,"defaultValue":"请按照屏幕指引前往指定区域"},{"name":"displayDuration","type":"Integer","required":true,"defaultValue":"60"}]'::json,
       '[{"name":"displayStatus","type":"String","required":true}]'::json,
       'ENABLED'
FROM devices d WHERE d.simulated_device_type = 'SMART_DISPLAY' AND d.device_status = 'ACTIVE'
  AND NOT EXISTS (SELECT 1 FROM device_capabilities c WHERE c.device_id = d.id AND c.capability_code = 'CAP_INFO_DISPLAY');

INSERT INTO device_capabilities (device_id, capability_code, capability_name, capability_type, input_params, output_params, capability_status)
SELECT d.id, 'CAP_FLIGHT_UPDATE', '航班变更信息发布', 'CAP_FLIGHT_UPDATE',
       '[{"name":"flightNumber","type":"String","required":true,"defaultValue":"CA1001"},{"name":"updateType","type":"String","required":true,"defaultValue":"GATE_CHANGE"},{"name":"updateContent","type":"String","required":true,"defaultValue":"航班登机口变更提示"},{"name":"displayDuration","type":"Integer","required":true,"defaultValue":"60"}]'::json,
       '[{"name":"publishStatus","type":"String","required":true}]'::json,
       'ENABLED'
FROM devices d WHERE d.simulated_device_type = 'FLIGHT_DELAY_BOARD' AND d.device_status = 'ACTIVE'
  AND NOT EXISTS (SELECT 1 FROM device_capabilities c WHERE c.device_id = d.id AND c.capability_code = 'CAP_FLIGHT_UPDATE');

INSERT INTO device_capabilities (device_id, capability_code, capability_name, capability_type, input_params, output_params, capability_status)
SELECT d.id, 'CAP_NAVIGATION', '空间引导', 'CAP_NAVIGATION',
       '[{"name":"origin","type":"String","required":true,"defaultValue":"值机区"},{"name":"destination","type":"String","required":true,"defaultValue":"5号登机口"}]'::json,
       '[{"name":"navigationStatus","type":"String","required":true}]'::json,
       'ENABLED'
FROM devices d WHERE d.simulated_device_type = 'MOBILE_ROBOT' AND d.device_status = 'ACTIVE'
  AND NOT EXISTS (SELECT 1 FROM device_capabilities c WHERE c.device_id = d.id AND c.capability_code = 'CAP_NAVIGATION');

INSERT INTO device_capabilities (device_id, capability_code, capability_name, capability_type, input_params, output_params, capability_status)
SELECT d.id, 'CAP_ESCORT', '陪同服务', 'CAP_ESCORT',
       '[{"name":"origin","type":"String","required":true,"defaultValue":"值机区"},{"name":"destination","type":"String","required":true,"defaultValue":"5号登机口"}]'::json,
       '[{"name":"escortStatus","type":"String","required":true}]'::json,
       'ENABLED'
FROM devices d WHERE d.simulated_device_type = 'MOBILE_ROBOT' AND d.device_status = 'ACTIVE'
  AND NOT EXISTS (SELECT 1 FROM device_capabilities c WHERE c.device_id = d.id AND c.capability_code = 'CAP_ESCORT');

INSERT INTO device_capabilities (device_id, capability_code, capability_name, capability_type, input_params, output_params, capability_status)
SELECT d.id, 'CAP_NOTIFICATION', '现场通知', 'CAP_NOTIFICATION',
       '[{"name":"message","type":"String","required":true,"defaultValue":"请旅客前往指定区域"}]'::json,
       '[{"name":"notifyStatus","type":"String","required":true}]'::json,
       'ENABLED'
FROM devices d WHERE d.simulated_device_type = 'MOBILE_ROBOT' AND d.device_status = 'ACTIVE'
  AND NOT EXISTS (SELECT 1 FROM device_capabilities c WHERE c.device_id = d.id AND c.capability_code = 'CAP_NOTIFICATION');

-- 为 20 台设备创建启用状态的设备代理
INSERT INTO device_agents (agent_code, device_id, agent_status, online_status, work_status)
SELECT 'AGENT_' || d.device_code, d.id, 'ENABLED', 'OFFLINE', 'IDLE'
FROM devices d
WHERE d.device_code LIKE 'SIM_%' AND d.device_status = 'ACTIVE'
  AND NOT EXISTS (SELECT 1 FROM device_agents a WHERE a.device_id = d.id);
