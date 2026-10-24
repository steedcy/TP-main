-- SRS 5.6.5 manual entry includes an earlier-departure event. Keep device schemas in sync.
UPDATE device_capabilities AS capability
SET input_params = (
    SELECT jsonb_agg(CASE
        WHEN field.value ->> 'name' = 'updateType'
             AND field.value ->> 'range' = 'DELAY/GATE_CHANGE/CANCEL'
        THEN jsonb_set(field.value, '{range}', '"DELAY/EARLY/GATE_CHANGE/CANCEL"'::jsonb)
        ELSE field.value END ORDER BY field.ordinality)
    FROM jsonb_array_elements(capability.input_params::jsonb) WITH ORDINALITY AS field(value, ordinality)
)::json
WHERE capability.capability_type = 'CAP_FLIGHT_UPDATE'
  AND capability.input_params::text LIKE '%DELAY/GATE_CHANGE/CANCEL%';

UPDATE capability_template AS template
SET input_params = (
    SELECT jsonb_agg(CASE
        WHEN field.value ->> 'name' = 'updateType'
             AND field.value ->> 'range' = 'DELAY/GATE_CHANGE/CANCEL'
        THEN jsonb_set(field.value, '{range}', '"DELAY/EARLY/GATE_CHANGE/CANCEL"'::jsonb)
        ELSE field.value END ORDER BY field.ordinality)
    FROM jsonb_array_elements(template.input_params::jsonb) WITH ORDINALITY AS field(value, ordinality)
)::json
WHERE template.capability_type = 'CAP_FLIGHT_UPDATE'
  AND template.input_params::text LIKE '%DELAY/GATE_CHANGE/CANCEL%';
