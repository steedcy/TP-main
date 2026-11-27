-- V46: 为所有设施点位增加互不重叠的矩形区域(bounds_json)，停用 RULE_ESCORT_SPECIAL_PASSENGER，并绑定特殊旅客模板第2~4步使用同一台机器人

ALTER TABLE terminal_pois ADD COLUMN IF NOT EXISTS bounds_json TEXT;

UPDATE terminal_pois SET bounds_json = '{"x1": 221.0, "y1": 42.0, "x2": 257.0, "y2": 70.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'GATE_01';
UPDATE terminal_pois SET bounds_json = '{"x1": 464.0, "y1": 43.0, "x2": 500.0, "y2": 71.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'GATE_02';
UPDATE terminal_pois SET bounds_json = '{"x1": 701.0, "y1": 42.0, "x2": 737.0, "y2": 70.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'GATE_03';
UPDATE terminal_pois SET bounds_json = '{"x1": 1004.0, "y1": 43.0, "x2": 1040.0, "y2": 71.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'GATE_04';
UPDATE terminal_pois SET bounds_json = '{"x1": 1239.0, "y1": 42.0, "x2": 1275.0, "y2": 70.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'GATE_05';
UPDATE terminal_pois SET bounds_json = '{"x1": 1667.0, "y1": 42.0, "x2": 1703.0, "y2": 70.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'GATE_06';
UPDATE terminal_pois SET bounds_json = '{"x1": 1010.0, "y1": 121.0, "x2": 1046.0, "y2": 149.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'SERVICE_DESK';
UPDATE terminal_pois SET bounds_json = '{"x1": 701.0, "y1": 124.0, "x2": 737.0, "y2": 152.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_WATER_N1';
UPDATE terminal_pois SET bounds_json = '{"x1": 1239.0, "y1": 135.0, "x2": 1275.0, "y2": 163.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_WATER_N2';
UPDATE terminal_pois SET bounds_json = '{"x1": 459.0, "y1": 165.0, "x2": 495.0, "y2": 193.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_ELEV_N1';
UPDATE terminal_pois SET bounds_json = '{"x1": 497.0, "y1": 165.0, "x2": 533.0, "y2": 193.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_ESC_DN_N1';
UPDATE terminal_pois SET bounds_json = '{"x1": 538.0, "y1": 164.0, "x2": 574.0, "y2": 192.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_ESC_UP_N1';
UPDATE terminal_pois SET bounds_json = '{"x1": 1484.0, "y1": 165.0, "x2": 1520.0, "y2": 193.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_ELEV_N2';
UPDATE terminal_pois SET bounds_json = '{"x1": 1525.0, "y1": 165.0, "x2": 1561.0, "y2": 193.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_ESC_UP_N2';
UPDATE terminal_pois SET bounds_json = '{"x1": 1563.0, "y1": 165.0, "x2": 1599.0, "y2": 193.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_ESC_DN_N2';
UPDATE terminal_pois SET bounds_json = '{"x1": 880.0, "y1": 235.0, "x2": 1196.0, "y2": 341.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'SECURITY_MAIN';
UPDATE terminal_pois SET bounds_json = '{"x1": 109, "y1": 235.0, "x2": 171.0, "y2": 286.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_WC_MW1';
UPDATE terminal_pois SET bounds_json = '{"x1": 173.0, "y1": 235.0, "x2": 225.5, "y2": 286.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_WATER_MW1';
UPDATE terminal_pois SET bounds_json = '{"x1": 338, "y1": 235.0, "x2": 398.0, "y2": 286.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'SHOP_FOOD_MW1';
UPDATE terminal_pois SET bounds_json = '{"x1": 400.0, "y1": 235.0, "x2": 460, "y2": 286.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_NURSERY_MW';
UPDATE terminal_pois SET bounds_json = '{"x1": 494, "y1": 235.0, "x2": 556.0, "y2": 286.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'SHOP_MW1';
UPDATE terminal_pois SET bounds_json = '{"x1": 558.0, "y1": 235.0, "x2": 600.5, "y2": 286.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_WC_MW2';
UPDATE terminal_pois SET bounds_json = '{"x1": 602.5, "y1": 235.0, "x2": 652.0, "y2": 286.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_WATER_MW2';
UPDATE terminal_pois SET bounds_json = '{"x1": 654.0, "y1": 235.0, "x2": 712.0, "y2": 286.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_FIRSTAID';
UPDATE terminal_pois SET bounds_json = '{"x1": 714.0, "y1": 235.0, "x2": 787, "y2": 286.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'SHOP_MW2';
UPDATE terminal_pois SET bounds_json = '{"x1": 554, "y1": 290.0, "x2": 613.5, "y2": 341.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_WC_MW3';
UPDATE terminal_pois SET bounds_json = '{"x1": 615.5, "y1": 290.0, "x2": 675, "y2": 341.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_WATER_MW3';
UPDATE terminal_pois SET bounds_json = '{"x1": 698, "y1": 290.0, "x2": 782, "y2": 341.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_LOUNGE_MW';
UPDATE terminal_pois SET bounds_json = '{"x1": 808, "y1": 290.0, "x2": 880, "y2": 341.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'BAGGAGE_CLAIM_W';
UPDATE terminal_pois SET bounds_json = '{"x1": 1231, "y1": 235.0, "x2": 1308.5, "y2": 286.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'SHOP_ME1';
UPDATE terminal_pois SET bounds_json = '{"x1": 1310.5, "y1": 235.0, "x2": 1383.5, "y2": 286.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'SHOP_ME2';
UPDATE terminal_pois SET bounds_json = '{"x1": 1385.5, "y1": 235.0, "x2": 1445.5, "y2": 286.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_WC_ME1';
UPDATE terminal_pois SET bounds_json = '{"x1": 1447.5, "y1": 235.0, "x2": 1501.5, "y2": 286.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_WATER_ME1';
UPDATE terminal_pois SET bounds_json = '{"x1": 1503.5, "y1": 235.0, "x2": 1577, "y2": 286.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_NURSERY_ME';
UPDATE terminal_pois SET bounds_json = '{"x1": 1626, "y1": 235.0, "x2": 1693.0, "y2": 286.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'SHOP_FOOD_ME1';
UPDATE terminal_pois SET bounds_json = '{"x1": 1695.0, "y1": 235.0, "x2": 1762, "y2": 286.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'LOUNGE_VIP';
UPDATE terminal_pois SET bounds_json = '{"x1": 1196, "y1": 290.0, "x2": 1263.5, "y2": 341.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'BAGGAGE_CLAIM_E';
UPDATE terminal_pois SET bounds_json = '{"x1": 1265.5, "y1": 290.0, "x2": 1339.0, "y2": 341.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_LOUNGE_ME';
UPDATE terminal_pois SET bounds_json = '{"x1": 1341.0, "y1": 290.0, "x2": 1404.0, "y2": 341.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_GUARD_ME';
UPDATE terminal_pois SET bounds_json = '{"x1": 1406.0, "y1": 290.0, "x2": 1449.5, "y2": 341.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_WC_ME2';
UPDATE terminal_pois SET bounds_json = '{"x1": 1451.5, "y1": 290.0, "x2": 1512, "y2": 341.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_WATER_ME2';
UPDATE terminal_pois SET bounds_json = '{"x1": 560.0, "y1": 393.0, "x2": 596.0, "y2": 421.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'SHOP_FOOD_S1';
UPDATE terminal_pois SET bounds_json = '{"x1": 1461.0, "y1": 389.0, "x2": 1497.0, "y2": 417.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'SHOP_S2';
UPDATE terminal_pois SET bounds_json = '{"x1": 803.0, "y1": 420.0, "x2": 839.0, "y2": 448.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_ELEV_S1';
UPDATE terminal_pois SET bounds_json = '{"x1": 840.0, "y1": 420.0, "x2": 876.0, "y2": 448.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_WC_S1';
UPDATE terminal_pois SET bounds_json = '{"x1": 878.0, "y1": 421.0, "x2": 914.0, "y2": 449.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'CHECKIN_WEST';
UPDATE terminal_pois SET bounds_json = '{"x1": 878.0, "y1": 458.0, "x2": 914.0, "y2": 486.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_ESC_UP_S1';
UPDATE terminal_pois SET bounds_json = '{"x1": 916.0, "y1": 456.0, "x2": 952.0, "y2": 484.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_STAIRS_S1';
UPDATE terminal_pois SET bounds_json = '{"x1": 1105.0, "y1": 421.0, "x2": 1141.0, "y2": 449.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'CHECKIN_EAST';
UPDATE terminal_pois SET bounds_json = '{"x1": 1146.0, "y1": 420.0, "x2": 1182.0, "y2": 448.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_ELEV_S2';
UPDATE terminal_pois SET bounds_json = '{"x1": 1184.0, "y1": 420.0, "x2": 1220.0, "y2": 448.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_WC_S2';
UPDATE terminal_pois SET bounds_json = '{"x1": 1105.0, "y1": 458.0, "x2": 1141.0, "y2": 486.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_ESC_UP_S2';
UPDATE terminal_pois SET bounds_json = '{"x1": 1146.0, "y1": 456.0, "x2": 1182.0, "y2": 484.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'FAC_STAIRS_S2';
UPDATE terminal_pois SET bounds_json = '{"x1": 502.0, "y1": 411.0, "x2": 538.0, "y2": 439.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'MEASURE_WEST';
UPDATE terminal_pois SET bounds_json = '{"x1": 1402.0, "y1": 411.0, "x2": 1438.0, "y2": 439.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'MEASURE_EAST';
UPDATE terminal_pois SET bounds_json = '{"x1": 293.0, "y1": 506.0, "x2": 329.0, "y2": 534.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'ENTRANCE_01';
UPDATE terminal_pois SET bounds_json = '{"x1": 1018.0, "y1": 506.0, "x2": 1054.0, "y2": 534.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'ENTRANCE_02';
UPDATE terminal_pois SET bounds_json = '{"x1": 1859.0, "y1": 506.0, "x2": 1895.0, "y2": 534.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'ENTRANCE_03';
UPDATE terminal_pois SET bounds_json = '{"x1": 227.5, "y1": 235.0, "x2": 302, "y2": 286.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'PET_CHANNEL';
UPDATE terminal_pois SET bounds_json = '{"x1": 138, "y1": 290.0, "x2": 222, "y2": 341.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'OVERSIZE_PACKING';
UPDATE terminal_pois SET bounds_json = '{"x1": 268, "y1": 290.0, "x2": 352, "y2": 341.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'OVERSIZE_CHECKIN';
UPDATE terminal_pois SET bounds_json = '{"x1": 1678, "y1": 290.0, "x2": 1762, "y2": 341.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'REBOOK_COUNTER';
UPDATE terminal_pois SET bounds_json = '{"x1": 1558, "y1": 290.0, "x2": 1642, "y2": 341.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'SPECIAL_SERVICE_DESK';
UPDATE terminal_pois SET bounds_json = '{"x1": 1788, "y1": 290.0, "x2": 1872, "y2": 341.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'TRANSFER_COUNTER';
UPDATE terminal_pois SET bounds_json = '{"x1": 408, "y1": 290.0, "x2": 492, "y2": 341.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'OVERSIZE_STORAGE';
UPDATE terminal_pois SET bounds_json = '{"x1": 1768, "y1": 235.0, "x2": 1852, "y2": 286.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'DUTY_MANAGER_DESK';
UPDATE terminal_pois SET bounds_json = '{"x1": 1863, "y1": 235.0, "x2": 1947, "y2": 286.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'MEAL_VOUCHER_POINT';
UPDATE terminal_pois SET bounds_json = '{"x1": 1802.0, "y1": 101.0, "x2": 1838.0, "y2": 129.0}', updated_at = CURRENT_TIMESTAMP WHERE poi_code = 'SHUTTLE_GATE';

-- 停用特殊旅客机器人会合/陪同确定性高风险规则，避免自主规划结果被100%固定降级丢弃
UPDATE risk_rules SET enabled = FALSE, updated_at = CURRENT_TIMESTAMP WHERE rule_code = 'RULE_ESCORT_SPECIAL_PASSENGER';

-- 更新特殊旅客标准基线模板，要求第2步 CAP_NOTIFICATION 与第3步 CAP_NAVIGATION、第4步 CAP_ESCORT 使用同一台移动服务机器人
UPDATE baseline_templates SET steps = $j$[{"stepSeq": 1, "capabilityType": "CAP_INFO_DISPLAY", "paramMapping": [{"target": "contentType", "source": "TEMPLATE_INPUT.contentType"}, {"target": "contentData", "source": "TEMPLATE_INPUT.meetingNotice"}, {"target": "displayDuration", "source": "TEMPLATE_INPUT.displayDuration"}], "stepTimeout": 60, "completionCondition": "displayStatus=SUCCESS"}, {"stepSeq": 2, "capabilityType": "CAP_NOTIFICATION", "paramMapping": [{"target": "notificationContent", "source": "TEMPLATE_INPUT.meetingNotice"}, {"target": "notificationType", "source": "TEMPLATE_INPUT.notificationType"}, {"target": "repeatCount", "source": "TEMPLATE_INPUT.repeatCount"}], "stepTimeout": 60, "completionCondition": "notificationStatus=SUCCESS", "bindSameAgentGroup": "SPECIAL_ESCORT_ROBOT"}, {"stepSeq": 3, "capabilityType": "CAP_NAVIGATION", "paramMapping": [{"target": "targetLocation", "source": "TEMPLATE_INPUT.origin"}, {"target": "routePreference", "source": "TEMPLATE_INPUT.routePreference"}], "stepTimeout": 60, "completionCondition": "routeGenerated=true", "bindSameAgentGroup": "SPECIAL_ESCORT_ROBOT"}, {"stepSeq": 4, "capabilityType": "CAP_ESCORT", "paramMapping": [{"target": "targetLocation", "source": "TEMPLATE_INPUT.targetLocation"}, {"target": "escortMode", "source": "TEMPLATE_INPUT.escortMode"}, {"target": "maxDuration", "source": "TEMPLATE_INPUT.maxDuration"}], "stepTimeout": 60, "completionCondition": "arrivalStatus=ARRIVED", "bindSameAgentGroup": "SPECIAL_ESCORT_ROBOT"}]$j$::json, updated_at = CURRENT_TIMESTAMP WHERE is_preset = TRUE AND task_family = 'SPECIAL_PASSENGER_SERVICE';
