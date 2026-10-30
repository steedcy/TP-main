-- DEF-S3-080 / SRS_F006.R04: "tested and passed with the current parameters" becomes its own fact instead of
-- being inferred from the status enum (DISABLED was wrongly read as "tested before").
ALTER TABLE device_capabilities ADD COLUMN test_passed BOOLEAN NOT NULL DEFAULT FALSE;

-- Back-fill only what the stored evidence proves: a real device-agent test pass that is still the latest result.
-- (Rows that are ENABLED without such evidence are left untouched; they simply cannot be re-enabled after a disable
-- until they pass a real test.)
UPDATE device_capabilities
SET test_passed = TRUE
WHERE capability_status IN ('TESTED_PASSED', 'ENABLED', 'DISABLED')
  AND last_test_at IS NOT NULL
  AND test_result LIKE '实际设备代理调用通过%';
