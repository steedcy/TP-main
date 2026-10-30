-- DEF-S3-023 / SRS_F006A.R12: immutable per-version snapshots of capability templates (V1.0, V1.1, ...).
CREATE TABLE capability_template_versions (
    id BIGSERIAL PRIMARY KEY,
    template_id BIGINT NOT NULL REFERENCES capability_template(id) ON DELETE CASCADE,
    template_version VARCHAR(16) NOT NULL,
    template_name VARCHAR(64) NOT NULL,
    input_params JSON NOT NULL,
    output_params JSON NOT NULL,
    template_description TEXT,
    changed_by VARCHAR(64),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_cap_template_version UNIQUE (template_id, template_version)
);

-- Back-fill: the current row of every existing template becomes its latest recorded version.
INSERT INTO capability_template_versions (template_id, template_version, template_name, input_params,
                                          output_params, template_description, changed_by)
SELECT id, template_version, template_name, input_params, output_params, template_description, 'migration'
FROM capability_template
ON CONFLICT (template_id, template_version) DO NOTHING;
