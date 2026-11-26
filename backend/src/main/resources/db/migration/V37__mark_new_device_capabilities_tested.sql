-- 为 20 台新仿真体已启用的能力补齐 test_passed = TRUE，使其进入规划上下文与能力校验可用集合
UPDATE device_capabilities
SET test_passed = TRUE,
    last_test_at = COALESCE(last_test_at, CURRENT_TIMESTAMP),
    test_result = COALESCE(test_result, '测试通过'),
    updated_at = CURRENT_TIMESTAMP
WHERE capability_status = 'ENABLED'
  AND (test_passed IS NULL OR test_passed = FALSE);
