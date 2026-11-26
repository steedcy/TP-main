-- 调整资源临界风险规则说明：仅要求可用候选设备数量大于 0，不再强制要求额外 1 台冗余备用设备
UPDATE risk_rules
SET rule_content = '任务申请资源时可用候选设备数量须大于0（不强制要求额外备用冗余设备，可用候选为0时命中）',
    updated_at = CURRENT_TIMESTAMP
WHERE rule_code = 'RULE_RESOURCE_CRITICAL';
