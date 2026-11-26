-- 依据《45条标准用例集》补充当前 2000x600 室内地图缺失的功能设施点位（值机区/隔离区外 8 个，候机区/隔离区内 3 个）
INSERT INTO terminal_pois (poi_code, poi_name, category, pos_x, pos_y, zone_name, linked_device_code, created_by)
VALUES
    -- 值机区（隔离区外）
    ('PET_CHANNEL', '宠物托运专用通道', 'SERVICE', 420, 465, '值机区-西', NULL, 'system'),
    ('OVERSIZE_PACKING', '超规行李打包处', 'BAGGAGE', 600, 425, '值机区-西', NULL, 'system'),
    ('OVERSIZE_CHECKIN', '超规行李托运处', 'BAGGAGE', 760, 425, '值机区-西', NULL, 'system'),
    ('REBOOK_COUNTER', '改签退票柜台', 'SERVICE', 960, 435, '值机区-中', NULL, 'system'),
    ('SPECIAL_SERVICE_DESK', '特殊旅客服务台', 'SERVICE', 990, 435, '值机区-中', NULL, 'system'),
    ('TRANSFER_COUNTER', '中转柜台', 'SERVICE', 1280, 425, '值机区-东', NULL, 'system'),
    ('OVERSIZE_STORAGE', '超规行李寄存处', 'BAGGAGE', 1340, 425, '值机区-东', NULL, 'system'),
    ('BAGGAGE_CAROUSEL', '行李提取与分拣区', 'BAGGAGE', 1580, 425, '值机区-东', NULL, 'system'),

    -- 候机区（隔离区内）
    ('DUTY_MANAGER_DESK', '值班经理接待点', 'SERVICE', 960, 145, '候机区-中', NULL, 'system'),
    ('MEAL_VOUCHER_POINT', '餐食发放登记处', 'SERVICE', 1100, 145, '候机区-中', NULL, 'system'),
    ('SHUTTLE_GATE', '远机位摆渡点', 'FACILITY', 1820, 115, '候机区-东', NULL, 'system')
ON CONFLICT (poi_code) DO UPDATE SET
    poi_name = EXCLUDED.poi_name,
    category = EXCLUDED.category,
    pos_x = EXCLUDED.pos_x,
    pos_y = EXCLUDED.pos_y,
    zone_name = EXCLUDED.zone_name,
    updated_at = CURRENT_TIMESTAMP;
