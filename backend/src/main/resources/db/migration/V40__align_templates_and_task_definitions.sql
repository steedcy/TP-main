-- 依据最新 2000x600 室内地图、20 台仿真体点位与《附录F》能力契约，统一更新任务定义、标准基线模板及能力模板默认点位

-- 1. 更新三类预设任务定义的场景参数与可执行禁行区约束
UPDATE task_definitions
SET scene_params = $j$[
  {"name":"baggageLocation","type":"String","required":true,"defaultValue":null,"range":"行李当前所在位置编码（如 MEASURE_WEST、MEASURE_EAST、CHECKIN_WEST）"},
  {"name":"targetCounter","type":"String","required":false,"defaultValue":"CHECKIN_WEST","range":"超规行李目标办理点位编码（如 CHECKIN_WEST、CHECKIN_EAST）"}
]$j$::json,
    constraint_description = '禁止进入西侧商铺及设施区(REG_SHOP_BLOCK_W)和东侧商铺及设施区(REG_SHOP_BLOCK_E)；测量结果超标须触发超规事件上报',
    updated_at = CURRENT_TIMESTAMP
WHERE definition_code = 'OVERSIZE_BAGGAGE_HANDLING';

UPDATE task_definitions
SET scene_params = $j$[
  {"name":"assistanceType","type":"String","required":true,"defaultValue":null,"range":"协助类型，如轮椅/视障/听障陪同"},
  {"name":"origin","type":"String","required":false,"defaultValue":"SERVICE_DESK","range":"会合起点位置编码（如 ENTRANCE_02、SERVICE_DESK）"},
  {"name":"targetLocation","type":"String","required":false,"defaultValue":"GATE_04","range":"目标地点位置编码（如 GATE_01~GATE_06）"}
]$j$::json,
    constraint_description = '禁止进入西侧商铺及设施区(REG_SHOP_BLOCK_W)和东侧商铺及设施区(REG_SHOP_BLOCK_E)；陪同对象为特殊旅客时优先安排陪同服务并保持现场通知联动',
    updated_at = CURRENT_TIMESTAMP
WHERE definition_code = 'SPECIAL_PASSENGER_SERVICE';

UPDATE task_definitions
SET scene_params = $j$[
  {"name":"flightNumber","type":"String","required":true,"defaultValue":null,"range":"航班号"},
  {"name":"targetLocation","type":"String","required":false,"defaultValue":"GATE_04","range":"变更后目标登机口编码（如 GATE_01~GATE_06）"}
]$j$::json,
    constraint_description = '禁止进入西侧商铺及设施区(REG_SHOP_BLOCK_W)和东侧商铺及设施区(REG_SHOP_BLOCK_E)；涉及登机口变更时须同步发布航班变更信息并提供空间引导',
    updated_at = CURRENT_TIMESTAMP
WHERE definition_code = 'FLIGHT_CHANGE_RESPONSE';

-- 2. 更新 3 个已启用的标准基线模板：替换旧 F2 测试点位为新地图真实 POI，并修正特殊旅客模板第 3 步 CAP_NAVIGATION 完成条件为 routeGenerated=true
UPDATE baseline_templates
SET input_params = $j$[
  {"name":"targetCounter","type":"String","required":true,"defaultValue":"CHECKIN_WEST","range":null},
  {"name":"routePreference","type":"String","required":true,"defaultValue":"BARRIER_FREE","range":null},
  {"name":"measureMode","type":"String","required":true,"defaultValue":"AUTO","range":null},
  {"name":"timeout","type":"Integer","required":true,"defaultValue":"30","range":"10~60"},
  {"name":"alertLevel","type":"String","required":true,"defaultValue":"WARNING","range":null},
  {"name":"contentType","type":"String","required":true,"defaultValue":"TEXT","range":null},
  {"name":"contentData","type":"String","required":true,"defaultValue":"超规行李请前往值机区西侧柜台(CHECKIN_WEST)办理托运","range":null},
  {"name":"displayDuration","type":"Integer","required":true,"defaultValue":"60","range":null}
]$j$::json,
    updated_at = CURRENT_TIMESTAMP
WHERE is_preset = TRUE AND task_family = 'OVERSIZE_BAGGAGE_HANDLING';

UPDATE baseline_templates
SET input_params = $j$[
  {"name":"notificationType","type":"String","required":true,"defaultValue":"BOTH","range":null},
  {"name":"repeatCount","type":"Integer","required":true,"defaultValue":"1","range":"1~5"},
  {"name":"targetLocation","type":"String","required":true,"defaultValue":"GATE_04","range":null},
  {"name":"escortMode","type":"String","required":true,"defaultValue":"LEAD","range":null},
  {"name":"maxDuration","type":"Integer","required":true,"defaultValue":"600","range":"60~1800"},
  {"name":"contentType","type":"String","required":true,"defaultValue":"TEXT","range":null},
  {"name":"displayDuration","type":"Integer","required":true,"defaultValue":"60","range":null},
  {"name":"origin","type":"String","required":true,"defaultValue":"SERVICE_DESK","range":null},
  {"name":"meetingNotice","type":"String","required":true,"defaultValue":"请在服务台(SERVICE_DESK)会合，由服务机器人陪同前往4号登机口(GATE_04)。","range":null},
  {"name":"routePreference","type":"String","required":true,"defaultValue":"BARRIER_FREE","range":null}
]$j$::json,
    steps = $j$[
  {
    "stepSeq": 1,
    "capabilityType": "CAP_INFO_DISPLAY",
    "paramMapping": [
      {"target": "contentType", "source": "TEMPLATE_INPUT.contentType"},
      {"target": "contentData", "source": "TEMPLATE_INPUT.meetingNotice"},
      {"target": "displayDuration", "source": "TEMPLATE_INPUT.displayDuration"}
    ],
    "stepTimeout": 60,
    "completionCondition": "displayStatus=SUCCESS"
  },
  {
    "stepSeq": 2,
    "capabilityType": "CAP_NOTIFICATION",
    "paramMapping": [
      {"target": "notificationContent", "source": "TEMPLATE_INPUT.meetingNotice"},
      {"target": "notificationType", "source": "TEMPLATE_INPUT.notificationType"},
      {"target": "repeatCount", "source": "TEMPLATE_INPUT.repeatCount"}
    ],
    "stepTimeout": 60,
    "completionCondition": "notificationStatus=SUCCESS"
  },
  {
    "stepSeq": 3,
    "capabilityType": "CAP_NAVIGATION",
    "paramMapping": [
      {"target": "targetLocation", "source": "TEMPLATE_INPUT.origin"},
      {"target": "routePreference", "source": "TEMPLATE_INPUT.routePreference"}
    ],
    "stepTimeout": 60,
    "completionCondition": "routeGenerated=true"
  },
  {
    "stepSeq": 4,
    "capabilityType": "CAP_ESCORT",
    "paramMapping": [
      {"target": "targetLocation", "source": "TEMPLATE_INPUT.targetLocation"},
      {"target": "escortMode", "source": "TEMPLATE_INPUT.escortMode"},
      {"target": "maxDuration", "source": "TEMPLATE_INPUT.maxDuration"}
    ],
    "stepTimeout": 60,
    "completionCondition": "arrivalStatus=ARRIVED"
  }
]$j$::json,
    updated_at = CURRENT_TIMESTAMP
WHERE is_preset = TRUE AND task_family = 'SPECIAL_PASSENGER_SERVICE';

UPDATE baseline_templates
SET input_params = $j$[
  {"name":"flightNumber","type":"String","required":true,"defaultValue":"CA1001","range":null},
  {"name":"updateType","type":"String","required":true,"defaultValue":"GATE_CHANGE","range":null},
  {"name":"updateContent","type":"String","required":true,"defaultValue":"航班登机口变更至4号登机口(GATE_04)","range":null},
  {"name":"displayDuration","type":"Integer","required":true,"defaultValue":"60","range":"10~600"},
  {"name":"targetLocation","type":"String","required":true,"defaultValue":"GATE_04","range":null},
  {"name":"routePreference","type":"String","required":true,"defaultValue":"BARRIER_FREE","range":null},
  {"name":"displayContent","type":"String","required":true,"defaultValue":"航班登机口已变更，请按照指引前往4号登机口(GATE_04)。","range":null},
  {"name":"contentType","type":"String","required":true,"defaultValue":"TEXT","range":null},
  {"name":"notificationType","type":"String","required":true,"defaultValue":"BOTH","range":null},
  {"name":"notificationContent","type":"String","required":true,"defaultValue":"航班登机口已变更，请前往新登机口候机。","range":null},
  {"name":"repeatCount","type":"Integer","required":true,"defaultValue":"1","range":"1~5"}
]$j$::json,
    updated_at = CURRENT_TIMESTAMP
WHERE is_preset = TRUE AND task_family = 'FLIGHT_CHANGE_RESPONSE';

-- 3. 同步刷新标准能力模板及已继承设备能力中的旧 F2 默认点位示例
UPDATE capability_template
SET input_params = REPLACE(REPLACE(input_params::text, 'F2_TEST_GATE', 'GATE_04'), 'F2服务点', '服务台(SERVICE_DESK)')::json,
    updated_at = CURRENT_TIMESTAMP
WHERE input_params::text LIKE '%F2_%' OR input_params::text LIKE '%F2服务点%';

UPDATE device_capabilities
SET input_params = REPLACE(REPLACE(input_params::text, 'F2_TEST_GATE', 'GATE_04'), 'F2服务点', '服务台(SERVICE_DESK)')::json,
    updated_at = CURRENT_TIMESTAMP
WHERE input_params::text LIKE '%F2_%' OR input_params::text LIKE '%F2服务点%';
