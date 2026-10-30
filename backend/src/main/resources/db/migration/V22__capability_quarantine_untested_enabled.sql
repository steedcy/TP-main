-- DEF-S3-080 follow-up: quarantine legacy ENABLED capabilities that have no real test-pass evidence.
-- V21 back-filled test_passed from stored results, but rows that were ENABLED via the old status bypass
-- remain in the ENABLED state with test_passed=FALSE. This migration moves them out of the usable set.
UPDATE device_capabilities
SET capability_status = 'DISABLED',
    test_result = COALESCE(test_result, 'Auto-disabled during upgrade: no successful test evidence'),
    updated_at = CURRENT_TIMESTAMP
WHERE capability_status = 'ENABLED'
  AND test_passed = FALSE;
