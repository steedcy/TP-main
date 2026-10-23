-- 对应《数据库设计说明书》V2.0 第7.1节数据初始化脚本
-- 默认系统管理员账号，密码为占位符哈希，部署时必须替换为实际加盐摘要值
INSERT INTO users (username, password_hash, real_name, role, contact, status) VALUES
('admin', '$2a$10$PLACEHOLDER_HASH_REPLACE_ON_DEPLOY', '系统管理员', 'SYSTEM_ADMIN', '13800000000', 'ACTIVE');

-- 五类设备类型能力边界（对应8.4.3）
INSERT INTO device_type_capability (device_type_code, device_type_name, supported_capability_types, type_description) VALUES
('SMART_DISPLAY', '智慧航显', '["CAP_INFO_DISPLAY", "CAP_FLIGHT_UPDATE", "CAP_NAVIGATION"]', '固定部署的综合信息展示设备'),
('BAGGAGE_SCANNER', '智能行李测量设备', '["CAP_BAGGAGE_MEASURE", "CAP_OVERSIZE_ALERT"]', '自动测量行李尺寸和重量的设备'),
('FLIGHT_DELAY_BOARD', '航延屏', '["CAP_INFO_DISPLAY", "CAP_FLIGHT_UPDATE"]', '专用于航班信息发布的显示屏'),
('MOBILE_ROBOT', '移动服务机器人', '["CAP_NAVIGATION", "CAP_ESCORT", "CAP_NOTIFICATION", "CAP_INFO_DISPLAY"]', '可移动的服务机器人'),
('SIMULATOR', '仿真体', '["CAP_SIM_STATUS"]', '模拟设备行为的仿真体，创建时需指定所模拟的真实设备类型');

-- 确定性高风险规则（对应TBD-03拍板结论三类规则，附录B 4.4节）
INSERT INTO risk_rules (rule_code, rule_content, rule_version, enabled) VALUES
('RULE_ESCORT_SPECIAL_PASSENGER', '移动机器人会合或陪同服务对象为特殊旅客时判定为高风险；普通空间引导场景不命中', 'V1.0', TRUE),
('RULE_CROSS_ZONE', '仅移动服务机器人适用；同一任务链条中跨越预定义区域边界1次及以上命中', 'V1.0', TRUE),
('RULE_RESOURCE_CRITICAL', '任务申请资源时可用备用候选设备数量低于配置阈值（默认1）命中', 'V1.0', TRUE);

-- 预置任务族基线模板框架（具体步骤在配置阶段补充）
INSERT INTO baseline_templates (template_name, task_family, is_preset, input_params, steps, template_status) VALUES
('超规行李处置标准模板', 'OVERSIZE_BAGGAGE_HANDLING', TRUE, '[{"name":"baggageLocation","type":"String","required":true}]', '[]', 'DRAFT'),
('特殊旅客服务标准模板', 'SPECIAL_PASSENGER_SERVICE', TRUE, '[{"name":"assistanceType","type":"String","required":true}]', '[]', 'DRAFT'),
('航班变更应对标准模板', 'FLIGHT_CHANGE_RESPONSE', TRUE, '[{"name":"flightNumber","type":"String","required":true}]', '[]', 'DRAFT');
