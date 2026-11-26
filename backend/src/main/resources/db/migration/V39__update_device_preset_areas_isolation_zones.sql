-- 将当前 20 台仿真体设备按其空间位置统一归入“隔离区内”（候机区）和“隔离区外”（值机区）
UPDATE devices
SET area_code = CASE
        WHEN position_y < 235 THEN '隔离区内'
        ELSE '隔离区外'
    END,
    updated_at = CURRENT_TIMESTAMP
WHERE is_simulator = TRUE
  AND device_status = 'ACTIVE';
