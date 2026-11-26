-- 新增通用协同服务任务族（GENERAL_SERVICE），用于承接无法归类到三类预置场景、但设备能力可支持的开放式任务目标
INSERT INTO task_definitions (
    definition_code,
    task_name,
    goal_template,
    scene_params,
    available_capability_types,
    constraint_description,
    completion_condition,
    is_preset,
    definition_status
) VALUES (
    'GENERAL_SERVICE',
    '通用协同服务',
    '理解开放式机场服务目标，在可用设备能力范围内自主规划并执行协同任务',
    '[]'::json,
    '["CAP_INFO_DISPLAY","CAP_BAGGAGE_MEASURE","CAP_OVERSIZE_ALERT","CAP_FLIGHT_UPDATE","CAP_NAVIGATION","CAP_ESCORT","CAP_NOTIFICATION"]'::json,
    '禁止进入西侧商铺及设施区(REG_SHOP_BLOCK_W)和东侧商铺及设施区(REG_SHOP_BLOCK_E)；仅在可用设备能力范围内规划执行，禁止虚构设备能力或运动安全控制指令',
    '规划模型确定的任务目标已完成且所有必需设备动作已执行成功',
    TRUE,
    'ENABLED'
)
ON CONFLICT (definition_code) DO NOTHING;
