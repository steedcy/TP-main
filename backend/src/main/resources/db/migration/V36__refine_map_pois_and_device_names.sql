-- 细化候机楼设施点位、调整登机口(6个)/出入口(3个)、统一20台仿真体命名

-- 1. 更新区域名称与走廊（6个登机口、3个出入口）
DELETE FROM terminal_pois;
DELETE FROM terminal_map_regions;

INSERT INTO terminal_map_regions (region_code, region_name, region_type, geometry_json, created_by)
VALUES
    ('REG_HOLDING_ZONE', '候机区', 'ISOLATED_ZONE',
     '[{"x":40,"y":40},{"x":1960,"y":40},{"x":1960,"y":235},{"x":40,"y":235}]', 'system'),
    ('REG_CHECKIN_HALL', '值机区', 'CHECKIN_HALL',
     '[{"x":40,"y":341},{"x":1960,"y":341},{"x":1960,"y":520},{"x":40,"y":520}]', 'system'),
    ('REG_SECURITY_PASS', '安全检查', 'SECURITY_AREA',
     '[{"x":880,"y":235},{"x":1196,"y":235},{"x":1196,"y":341},{"x":880,"y":341}]', 'system'),
    ('REG_SHOP_BLOCK_W', '西侧商铺及设施区', 'SHOP_BLOCK',
     '[{"x":40,"y":235},{"x":880,"y":235},{"x":880,"y":341},{"x":40,"y":341}]', 'system'),
    ('REG_SHOP_BLOCK_E', '东侧商铺及设施区', 'SHOP_BLOCK',
     '[{"x":1196,"y":235},{"x":1960,"y":235},{"x":1960,"y":341},{"x":1196,"y":341}]', 'system'),
    ('CORR_HOLDING_MAIN', '候机区东西主通道', 'CORRIDOR',
     '[{"x":239,"y":115},{"x":482,"y":115},{"x":719,"y":115},{"x":1028,"y":115},{"x":1257,"y":115},{"x":1685,"y":115}]', 'system'),
    ('CORR_HOLDING_CENTER', '候机区中轴通道', 'CORRIDOR',
     '[{"x":1028,"y":115},{"x":1028,"y":170},{"x":1038,"y":235}]', 'system'),
    ('CORR_SECURITY_MAIN', '安检通道贯通走廊', 'CORRIDOR',
     '[{"x":1038,"y":235},{"x":1038,"y":288},{"x":1038,"y":341}]', 'system'),
    ('CORR_CHECKIN_CENTER', '值机区中轴出入口通道', 'CORRIDOR',
     '[{"x":1038,"y":341},{"x":1038,"y":425},{"x":1036,"y":520}]', 'system'),
    ('CORR_CHECKIN_MAIN', '值机区东西主通道', 'CORRIDOR',
     '[{"x":311,"y":425},{"x":520,"y":425},{"x":858,"y":425},{"x":1038,"y":425},{"x":1164,"y":425},{"x":1420,"y":425},{"x":1660,"y":425},{"x":1877,"y":425}]', 'system'),
    ('CORR_GATE_1', '1号登机口通道', 'CORRIDOR', '[{"x":239,"y":115},{"x":239,"y":56}]', 'system'),
    ('CORR_GATE_2', '2号登机口通道', 'CORRIDOR', '[{"x":482,"y":115},{"x":482,"y":57}]', 'system'),
    ('CORR_GATE_3', '3号登机口通道', 'CORRIDOR', '[{"x":719,"y":115},{"x":719,"y":56}]', 'system'),
    ('CORR_GATE_4', '4号登机口通道', 'CORRIDOR', '[{"x":1028,"y":115},{"x":1022,"y":57}]', 'system'),
    ('CORR_GATE_5', '5号登机口通道', 'CORRIDOR', '[{"x":1257,"y":115},{"x":1257,"y":56}]', 'system'),
    ('CORR_GATE_6', '6号登机口通道', 'CORRIDOR', '[{"x":1685,"y":115},{"x":1685,"y":56}]', 'system'),
    ('CORR_ENT_1', '1号门支线', 'CORRIDOR', '[{"x":311,"y":425},{"x":311,"y":520}]', 'system'),
    ('CORR_ENT_3', '3号门支线', 'CORRIDOR', '[{"x":1877,"y":425},{"x":1877,"y":520}]', 'system');

-- 2. 完整提取并标定图中所有设施与 POI
INSERT INTO terminal_pois (poi_code, poi_name, category, pos_x, pos_y, zone_name, linked_device_code, created_by)
VALUES
    -- 6 个登机口
    ('GATE_01', '1号登机口', 'GATE', 239, 56, '候机区-西', NULL, 'system'),
    ('GATE_02', '2号登机口', 'GATE', 482, 57, '候机区-西', NULL, 'system'),
    ('GATE_03', '3号登机口', 'GATE', 719, 56, '候机区-西', NULL, 'system'),
    ('GATE_04', '4号登机口', 'GATE', 1022, 57, '候机区-中', NULL, 'system'),
    ('GATE_05', '5号登机口', 'GATE', 1257, 56, '候机区-东', NULL, 'system'),
    ('GATE_06', '6号登机口', 'GATE', 1685, 56, '候机区-东', NULL, 'system'),

    -- 候机区设施
    ('SERVICE_DESK', '服务台', 'SERVICE', 1028, 135, '候机区-中', 'SIM_DISPLAY_H2', 'system'),
    ('FAC_WATER_N1', '饮用水', 'FACILITY', 719, 138, '候机区-西', NULL, 'system'),
    ('FAC_WATER_N2', '饮用水', 'FACILITY', 1257, 149, '候机区-东', NULL, 'system'),
    ('FAC_ELEV_N1', '电梯', 'FACILITY', 477, 179, '候机区-西', NULL, 'system'),
    ('FAC_ESC_DN_N1', '向下自动扶梯', 'FACILITY', 515, 179, '候机区-西', NULL, 'system'),
    ('FAC_ESC_UP_N1', '向上自动扶梯', 'FACILITY', 556, 178, '候机区-西', NULL, 'system'),
    ('FAC_ELEV_N2', '电梯', 'FACILITY', 1502, 179, '候机区-东', NULL, 'system'),
    ('FAC_ESC_UP_N2', '向上自动扶梯', 'FACILITY', 1543, 179, '候机区-东', NULL, 'system'),
    ('FAC_ESC_DN_N2', '向下自动扶梯', 'FACILITY', 1581, 179, '候机区-东', NULL, 'system'),

    -- 中央安全检查
    ('SECURITY_MAIN', '安全检查', 'SECURITY', 1037, 286, '中央安检区', NULL, 'system'),

    -- 中间左侧商铺及设施（上排）
    ('FAC_WC_MW1', '洗手间', 'FACILITY', 151, 258, '中间西区', NULL, 'system'),
    ('FAC_WATER_MW1', '饮用水', 'FACILITY', 193, 261, '中间西区', NULL, 'system'),
    ('SHOP_FOOD_MW1', '餐饮', 'SHOP', 380, 261, '中间西区', NULL, 'system'),
    ('FAC_NURSERY_MW', '母婴候机室', 'FACILITY', 418, 259, '中间西区', NULL, 'system'),
    ('SHOP_MW1', '商店', 'SHOP', 536, 261, '中间西区', NULL, 'system'),
    ('FAC_WC_MW2', '洗手间', 'FACILITY', 578, 260, '中间西区', NULL, 'system'),
    ('FAC_WATER_MW2', '饮用水', 'FACILITY', 625, 260, '中间西区', NULL, 'system'),
    ('FAC_FIRSTAID', '急救中心', 'FACILITY', 681, 254, '中间西区', NULL, 'system'),
    ('SHOP_MW2', '商店', 'SHOP', 745, 257, '中间西区', NULL, 'system'),

    -- 中间左侧设施（下排）
    ('FAC_WC_MW3', '洗手间', 'FACILITY', 596, 318, '中间西区', NULL, 'system'),
    ('FAC_WATER_MW3', '饮用水', 'FACILITY', 633, 319, '中间西区', NULL, 'system'),
    ('FAC_LOUNGE_MW', '候机厅', 'SERVICE', 740, 318, '中间西区', NULL, 'system'),
    ('BAGGAGE_CLAIM_W', '行李开包间', 'BAGGAGE', 850, 318, '中间西区', NULL, 'system'),

    -- 中间右侧商铺及设施（上排）
    ('SHOP_ME1', '商店', 'SHOP', 1273, 257, '中间东区', NULL, 'system'),
    ('SHOP_ME2', '商店', 'SHOP', 1346, 259, '中间东区', NULL, 'system'),
    ('FAC_WC_ME1', '洗手间', 'FACILITY', 1423, 260, '中间东区', NULL, 'system'),
    ('FAC_WATER_ME1', '饮用水', 'FACILITY', 1470, 260, '中间东区', NULL, 'system'),
    ('FAC_NURSERY_ME', '母婴候机室', 'FACILITY', 1535, 263, '中间东区', NULL, 'system'),
    ('SHOP_FOOD_ME1', '餐饮', 'SHOP', 1668, 263, '中间东区', NULL, 'system'),
    ('LOUNGE_VIP', '头等舱候机厅', 'SERVICE', 1720, 264, '中间东区', NULL, 'system'),

    -- 中间右侧设施（下排）
    ('BAGGAGE_CLAIM_E', '行李开包间', 'BAGGAGE', 1228, 317, '中间东区', NULL, 'system'),
    ('FAC_LOUNGE_ME', '候机厅', 'SERVICE', 1301, 318, '中间东区', NULL, 'system'),
    ('FAC_GUARD_ME', '安全保卫', 'SECURITY', 1379, 318, '中间东区', NULL, 'system'),
    ('FAC_WC_ME2', '洗手间', 'FACILITY', 1431, 319, '中间东区', NULL, 'system'),
    ('FAC_WATER_ME2', '饮用水', 'FACILITY', 1470, 319, '中间东区', NULL, 'system'),

    -- 值机区设施
    ('SHOP_FOOD_S1', '餐饮', 'SHOP', 578, 407, '值机区-西', NULL, 'system'),
    ('SHOP_S2', '商店', 'SHOP', 1479, 403, '值机区-东', NULL, 'system'),
    ('FAC_ELEV_S1', '电梯', 'FACILITY', 821, 434, '值机区-西', NULL, 'system'),
    ('FAC_WC_S1', '洗手间', 'FACILITY', 858, 434, '值机区-西', NULL, 'system'),
    ('CHECKIN_WEST', '售票', 'SERVICE', 896, 435, '值机区-西', NULL, 'system'),
    ('FAC_ESC_UP_S1', '向上自动扶梯', 'FACILITY', 896, 472, '值机区-西', NULL, 'system'),
    ('FAC_STAIRS_S1', '楼梯', 'FACILITY', 934, 470, '值机区-西', NULL, 'system'),
    ('CHECKIN_EAST', '问询', 'SERVICE', 1123, 435, '值机区-东', NULL, 'system'),
    ('FAC_ELEV_S2', '电梯', 'FACILITY', 1164, 434, '值机区-东', NULL, 'system'),
    ('FAC_WC_S2', '洗手间', 'FACILITY', 1202, 434, '值机区-东', NULL, 'system'),
    ('FAC_ESC_UP_S2', '向上自动扶梯', 'FACILITY', 1123, 472, '值机区-东', NULL, 'system'),
    ('FAC_STAIRS_S2', '楼梯', 'FACILITY', 1164, 470, '值机区-东', NULL, 'system'),
    ('MEASURE_WEST', '智能行李测量点01', 'MEASURE', 520, 425, '值机区-西', 'SIM_SCANNER_W', 'system'),
    ('MEASURE_EAST', '智能行李测量点02', 'MEASURE', 1420, 425, '值机区-东', 'SIM_SCANNER_E', 'system'),

    -- 3 个出入口
    ('ENTRANCE_01', '1号门', 'FACILITY', 311, 520, '值机区-南', NULL, 'system'),
    ('ENTRANCE_02', '2号门', 'FACILITY', 1036, 520, '值机区-南', NULL, 'system'),
    ('ENTRANCE_03', '3号门', 'FACILITY', 1877, 520, '值机区-南', NULL, 'system');

-- 3. 统一 20 台仿真体命名：设备类型中文名 + 两位数字编号
UPDATE devices SET device_name = '智能行李测量设备01' WHERE device_code = 'SIM_SCANNER_W';
UPDATE devices SET device_name = '智能行李测量设备02' WHERE device_code = 'SIM_SCANNER_E';

UPDATE devices SET device_name = '智慧航显01' WHERE device_code = 'SIM_DISPLAY_C1';
UPDATE devices SET device_name = '智慧航显02' WHERE device_code = 'SIM_DISPLAY_C2';
UPDATE devices SET device_name = '智慧航显03' WHERE device_code = 'SIM_DISPLAY_H1';
UPDATE devices SET device_name = '智慧航显04' WHERE device_code = 'SIM_DISPLAY_H2';
UPDATE devices SET device_name = '智慧航显05' WHERE device_code = 'SIM_DISPLAY_H3';

UPDATE devices SET device_name = '航延屏01' WHERE device_code = 'SIM_DELAY_G3';
UPDATE devices SET device_name = '航延屏02' WHERE device_code = 'SIM_DELAY_G4';
UPDATE devices SET device_name = '航延屏03' WHERE device_code = 'SIM_DELAY_G5';
UPDATE devices SET device_name = '航延屏04' WHERE device_code = 'SIM_DELAY_G6';
UPDATE devices SET device_name = '航延屏05' WHERE device_code = 'SIM_DELAY_C1';
UPDATE devices SET device_name = '航延屏06' WHERE device_code = 'SIM_DELAY_C2';

UPDATE devices SET device_name = '移动服务机器人01' WHERE device_code = 'SIM_ROBOT_C1';
UPDATE devices SET device_name = '移动服务机器人02' WHERE device_code = 'SIM_ROBOT_C2';
UPDATE devices SET device_name = '移动服务机器人03' WHERE device_code = 'SIM_ROBOT_C3';
UPDATE devices SET device_name = '移动服务机器人04' WHERE device_code = 'SIM_ROBOT_H1';
UPDATE devices SET device_name = '移动服务机器人05' WHERE device_code = 'SIM_ROBOT_H2';
UPDATE devices SET device_name = '移动服务机器人06' WHERE device_code = 'SIM_ROBOT_H3';
UPDATE devices SET device_name = '移动服务机器人07' WHERE device_code = 'SIM_ROBOT_H4';
