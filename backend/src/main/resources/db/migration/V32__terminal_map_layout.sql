CREATE TABLE IF NOT EXISTS terminal_pois (
    id BIGSERIAL PRIMARY KEY,
    poi_code VARCHAR(64) NOT NULL UNIQUE,
    poi_name VARCHAR(128) NOT NULL,
    category VARCHAR(32) NOT NULL,
    pos_x NUMERIC(10, 2) NOT NULL,
    pos_y NUMERIC(10, 2) NOT NULL,
    zone_name VARCHAR(128),
    linked_device_code VARCHAR(64),
    created_by VARCHAR(64),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS terminal_map_regions (
    id BIGSERIAL PRIMARY KEY,
    region_code VARCHAR(64) NOT NULL UNIQUE,
    region_name VARCHAR(128) NOT NULL,
    region_type VARCHAR(32) NOT NULL,
    geometry_json TEXT NOT NULL,
    created_by VARCHAR(64),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO terminal_pois (poi_code, poi_name, category, pos_x, pos_y, zone_name, linked_device_code, created_by)
VALUES
    ('T2值机岛A01', 'T2值机岛 A01', 'CHECKIN', 400, 3100, 'T2值机区-北', NULL, 'system'),
    ('T2值机岛A03', 'T2值机岛 A03', 'CHECKIN', 805, 4050, 'T2值机区-南', NULL, 'system'),
    ('T2值机区', 'T2值机区（会合点）', 'CHECKIN', 805, 4050, 'T2值机区-南', NULL, 'system'),
    ('行李托运柜台A01', '行李托运柜台 A01', 'BAGGAGE', 430, 3180, '行李托运区', NULL, 'system'),
    ('超规行李专柜B01', '超规行李专柜 B01', 'BAGGAGE', 810, 4200, '超规行李专柜区', NULL, 'system'),
    ('安检通道01', '安检通道 01', 'SECURITY', 630, 3750, '中央安检区', NULL, 'system'),
    ('VIP安检通道', 'VIP 特殊旅客安检通道', 'SECURITY', 840, 3750, '中央安检区', NULL, 'system'),
    ('智能行李测量点A', '智能行李测量点（主）', 'MEASURE', 400, 3106, 'T2值机区-北', 'SIM_F2_BAGGAGE', 'system'),
    ('智能行李测量点B', '智能行李测量点（备）', 'MEASURE', 465, 3447, 'T2值机区-中', 'SIM_F2_BAGGAGE_B', 'system'),
    ('旅客服务中心', '旅客综合服务柜台', 'SERVICE', 630, 4150, 'F2中庭南区', NULL, 'system'),
    ('GATE_A01', '登机口 A01', 'GATE', 500, 4600, 'A指廊', NULL, 'system'),
    ('GATE_A05', '登机口 A05', 'GATE', 815, 4600, 'A指廊', NULL, 'system'),
    ('GATE_B01', '登机口 B01', 'GATE', 420, 5200, 'B指廊', NULL, 'system')
ON CONFLICT (poi_code) DO NOTHING;
