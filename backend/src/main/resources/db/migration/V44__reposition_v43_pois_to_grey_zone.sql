-- V44: 将 V43 新增的 9 个服务点位调整至中间灰色商业/设施带（中间西区 / 中间东区），并删除重复的 BAGGAGE_CAROUSEL

DELETE FROM terminal_pois
WHERE poi_code = 'BAGGAGE_CAROUSEL';

UPDATE terminal_pois SET pos_x = 260,  pos_y = 260, zone_name = '中间西区', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'PET_CHANNEL';
UPDATE terminal_pois SET pos_x = 180,  pos_y = 318, zone_name = '中间西区', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'OVERSIZE_PACKING';
UPDATE terminal_pois SET pos_x = 310,  pos_y = 318, zone_name = '中间西区', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'OVERSIZE_CHECKIN';
UPDATE terminal_pois SET pos_x = 450,  pos_y = 318, zone_name = '中间西区', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'OVERSIZE_STORAGE';
UPDATE terminal_pois SET pos_x = 1600, pos_y = 318, zone_name = '中间东区', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'SPECIAL_SERVICE_DESK';
UPDATE terminal_pois SET pos_x = 1720, pos_y = 318, zone_name = '中间东区', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'REBOOK_COUNTER';
UPDATE terminal_pois SET pos_x = 1830, pos_y = 318, zone_name = '中间东区', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'TRANSFER_COUNTER';
UPDATE terminal_pois SET pos_x = 1810, pos_y = 260, zone_name = '中间东区', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'DUTY_MANAGER_DESK';
UPDATE terminal_pois SET pos_x = 1905, pos_y = 260, zone_name = '中间东区', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'MEAL_VOUCHER_POINT';
