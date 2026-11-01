-- DEF-S3-069 / SRS_F013.R03, SRS_F024.R04: the preset oversize-baggage task definition did not allow CAP_INFO_DISPLAY,
-- but the core scenario requires a smart-display step. Candidate plans that used it failed the constraint check
-- (ERR_CAPABILITY_NOT_IN_TASK_DEFINITION); plans that used only CAP_NOTIFICATION lacked the required display channel.
-- Add CAP_INFO_DISPLAY to the allowed list (idempotent; leaves a definition alone if it already contains it).
UPDATE task_definitions
SET available_capability_types = '["CAP_BAGGAGE_MEASURE","CAP_OVERSIZE_ALERT","CAP_NAVIGATION","CAP_NOTIFICATION","CAP_INFO_DISPLAY"]'::json,
    updated_at = CURRENT_TIMESTAMP
WHERE definition_code = 'OVERSIZE_BAGGAGE_HANDLING'
  AND is_preset = TRUE
  AND available_capability_types::text NOT LIKE '%CAP_INFO_DISPLAY%';
