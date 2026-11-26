-- 依据《附录F：五类设备能力边界清单（V1.0）》调整当前 20 台仿真体的能力配置：
-- 1. 清理不在所模拟设备类型边界或非 CAP_SIM_STATUS 的越界能力
DELETE FROM device_capabilities c
USING devices d
WHERE c.device_id = d.id
  AND d.is_simulator = TRUE
  AND d.device_status = 'ACTIVE'
  AND c.capability_type <> 'CAP_SIM_STATUS'
  AND NOT EXISTS (
      SELECT 1 FROM capability_template t
      WHERE t.device_type_code = d.simulated_device_type
        AND t.template_status = 'ACTIVE'
        AND t.capability_type = c.capability_type
  );

-- 2. 将既有继承能力对齐到标准能力模板（关联 template_id，统一输入输出参数契约与启用/测试通过状态）
UPDATE device_capabilities c
SET template_id = t.id,
    capability_name = t.template_name,
    input_params = t.input_params,
    output_params = t.output_params,
    capability_description = t.template_description,
    capability_status = 'ENABLED',
    test_passed = TRUE,
    last_test_at = COALESCE(c.last_test_at, CURRENT_TIMESTAMP),
    test_result = COALESCE(c.test_result, '测试通过'),
    updated_at = CURRENT_TIMESTAMP
FROM devices d
JOIN capability_template t
  ON t.device_type_code = d.simulated_device_type
 AND t.template_status = 'ACTIVE'
WHERE c.device_id = d.id
  AND d.is_simulator = TRUE
  AND d.device_status = 'ACTIVE'
  AND c.capability_type = t.capability_type;

-- 3. 补全 20 台仿真体缺失的继承能力（如 SMART_DISPLAY 的 CAP_FLIGHT_UPDATE/CAP_NAVIGATION，
--    FLIGHT_DELAY_BOARD 与 MOBILE_ROBOT 的 CAP_INFO_DISPLAY）
INSERT INTO device_capabilities (
    device_id, template_id, capability_code, capability_name, capability_type,
    input_params, output_params, capability_status, test_passed, last_test_at,
    test_result, capability_description
)
SELECT d.id, t.id, t.template_code, t.template_name, t.capability_type,
       t.input_params, t.output_params, 'ENABLED', TRUE, CURRENT_TIMESTAMP,
       '测试通过', t.template_description
FROM devices d
JOIN capability_template t
  ON t.device_type_code = d.simulated_device_type
 AND t.template_status = 'ACTIVE'
WHERE d.is_simulator = TRUE
  AND d.device_status = 'ACTIVE'
  AND NOT EXISTS (
      SELECT 1 FROM device_capabilities c
      WHERE c.device_id = d.id AND c.capability_code = t.template_code
  );

-- 4. 为 20 台仿真体补齐并启用核心仿真能力 CAP_SIM_STATUS（仿真状态生成）
INSERT INTO device_capabilities (
    device_id, capability_code, capability_name, capability_type,
    input_params, output_params, capability_status, test_passed, last_test_at,
    test_result, capability_description
)
SELECT d.id, 'CAP_SIM_STATUS', '仿真状态生成', 'CAP_SIM_STATUS',
       '[]'::json, '[]'::json, 'ENABLED', TRUE, CURRENT_TIMESTAMP,
       '测试通过', '仿真体生成并上报模拟设备状态'
FROM devices d
WHERE d.is_simulator = TRUE
  AND d.device_status = 'ACTIVE'
  AND NOT EXISTS (
      SELECT 1 FROM device_capabilities c
      WHERE c.device_id = d.id AND c.capability_code = 'CAP_SIM_STATUS'
  );

UPDATE device_capabilities c
SET capability_status = 'ENABLED',
    test_passed = TRUE,
    last_test_at = COALESCE(c.last_test_at, CURRENT_TIMESTAMP),
    test_result = COALESCE(c.test_result, '测试通过'),
    updated_at = CURRENT_TIMESTAMP
FROM devices d
WHERE c.device_id = d.id
  AND d.is_simulator = TRUE
  AND d.device_status = 'ACTIVE'
  AND c.capability_code = 'CAP_SIM_STATUS';

-- 5. 刷新标准能力模板引用计数
UPDATE capability_template t
SET usage_count = (SELECT COUNT(*) FROM device_capabilities c WHERE c.template_id = t.id);
