-- 对应5.6.1旅客服务任务定义管理（SRS_F022）。任务定义与5.3.1基线模板是两个不同概念：
-- 任务定义只规定场景数据、可用能力类型、约束和完成条件，不预先写死自主规划步骤（业务规则2）；
-- 基线模板则是预先写死的降级兜底执行步骤。此前系统把任务族硬编码为4个枚举值散落在多处
-- （SubmitTaskRequest.taskFamily、BaselineTemplate.taskFamily的@Pattern校验），本表补齐
-- 任务族的权威数据来源，后续两处硬编码枚举改为查询本表。
CREATE TABLE task_definitions (
    id BIGSERIAL PRIMARY KEY,
    definition_code VARCHAR(64) NOT NULL UNIQUE,
    task_name VARCHAR(64) NOT NULL UNIQUE,
    goal_template VARCHAR(500) NOT NULL,
    scene_params JSON NOT NULL,
    available_capability_types JSON NOT NULL,
    constraint_description TEXT,
    completion_condition TEXT NOT NULL,
    is_preset BOOLEAN NOT NULL DEFAULT FALSE,
    definition_status VARCHAR(16) NOT NULL DEFAULT 'ENABLED',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(64),
    CONSTRAINT chk_task_definition_status CHECK (definition_status IN ('ENABLED', 'DISABLED'))
);
CREATE INDEX idx_task_definition_status ON task_definitions(definition_status);

-- 预置三类核心任务族（对应业务规则1，definition_code与既有Task.taskFamily/BaselineTemplate.taskFamily
-- 历史枚举值保持一致，避免破坏已有任务记录和基线模板的任务族关联）
INSERT INTO task_definitions (definition_code, task_name, goal_template, scene_params,
                                available_capability_types, constraint_description, completion_condition, is_preset) VALUES
('OVERSIZE_BAGGAGE_HANDLING', '超规行李处置', '协助旅客处理超规行李，引导至行李处置点并完成尺寸重量测量',
 '[{"name":"baggageLocation","type":"String","required":true,"range":"行李当前所在位置编码"}]',
 '["CAP_BAGGAGE_MEASURE","CAP_OVERSIZE_ALERT","CAP_NAVIGATION","CAP_NOTIFICATION"]',
 '超规行李处置全程不得引导旅客脱离监控区域；测量结果超标须触发超规事件上报',
 '行李已完成尺寸重量测量且超规事件（如有）已上报', TRUE),
('SPECIAL_PASSENGER_SERVICE', '特殊旅客服务', '陪同或引导特殊旅客前往目标地点并完成必要通知',
 '[{"name":"assistanceType","type":"String","required":true,"range":"协助类型，如轮椅/视障/听障陪同"}]',
 '["CAP_ESCORT","CAP_NAVIGATION","CAP_NOTIFICATION","CAP_INFO_DISPLAY"]',
 '陪同对象为特殊旅客时优先安排陪同服务而非仅空间引导；全程与现场人员保持通知联动',
 '旅客已到达目标地点', TRUE),
('FLIGHT_CHANGE_RESPONSE', '航班变更应对', '将航班变更信息同步至受影响旅客并提供后续引导',
 '[{"name":"flightNumber","type":"String","required":true,"range":"航班号"}]',
 '["CAP_FLIGHT_UPDATE","CAP_INFO_DISPLAY","CAP_NOTIFICATION","CAP_NAVIGATION"]',
 '航班变更信息发布须在旅客到达登机口前完成；涉及登机口变更时须同步空间引导',
 '航班变更信息已送达且旅客后续引导（如需）已完成', TRUE);
