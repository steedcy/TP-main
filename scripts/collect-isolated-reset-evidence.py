"""Collect compact, non-secret evidence from the dedicated reset schema after tests."""
import importlib.util
import json
import pathlib
import xml.etree.ElementTree as ET

spec = importlib.util.spec_from_file_location("isolated", pathlib.Path(__file__).with_name("isolated-reset-db.py"))
isolated = importlib.util.module_from_spec(spec)
spec.loader.exec_module(isolated)
schema = isolated.isolated_schema
assert schema == "tip_f2_reset_20261024" and schema != "public"
sql = lambda query: isolated.sql(isolated.shared, query)
report = isolated.env.ROOT / "backend/target/surefire-reports/TEST-com.airport.ai.demo.DemoResetIntegrationTest.xml"
suite = ET.parse(report).getroot()
assert int(suite.attrib["failures"]) == 0 and int(suite.attrib["errors"]) == 0
assert int(suite.attrib["tests"]) == 1 and int(suite.attrib["skipped"]) == 0
success_digests = sql(f"SELECT string_agg(detail->>'contentDigest', ',') FROM "
                      f"(SELECT detail FROM {schema}.operation_logs WHERE operation_type='DEMO_DATA_RESET' "
                      f"AND operation_result='SUCCESS' ORDER BY id DESC LIMIT 2) recent")
digests = success_digests.split(",")
assert len(digests) == 2 and digests[0] == digests[1]
record = {
    "recordedAt": isolated.env.stamp(),
    "scope": "ISOLATED_POSTGRES_SCHEMA_ONLY",
    "schema": schema,
    "migrationVersion": sql(f"SELECT max(version) FROM {schema}.flyway_schema_history"),
    "junit": {key: int(suite.attrib[key]) for key in ["tests", "failures", "errors", "skipped"]},
    "canonicalDeviceCount": int(sql(f"SELECT count(*) FROM {schema}.devices WHERE device_code LIKE 'SIM_F2_%'")),
    "canonicalCapabilityCount": int(sql(f"SELECT count(*) FROM {schema}.device_capabilities c JOIN {schema}.devices d "
                                        f"ON d.id=c.device_id WHERE d.device_code LIKE 'SIM_F2_%'")),
    "draftPresetTemplateCount": int(sql(f"SELECT count(*) FROM {schema}.baseline_templates WHERE is_preset=TRUE AND template_status='DRAFT'")),
    "enabledPresetScenarioCount": int(sql(f"SELECT count(*) FROM {schema}.task_definitions WHERE is_preset=TRUE AND definition_status='ENABLED'")),
    "remainingTestTasks": int(sql(f"SELECT count(*) FROM {schema}.tasks WHERE task_code LIKE 'RESET-BLOCK-%'")),
    "successAuditCount": int(sql(f"SELECT count(*) FROM {schema}.operation_logs WHERE operation_type='DEMO_DATA_RESET' AND operation_result='SUCCESS'")),
    "failureAuditCount": int(sql(f"SELECT count(*) FROM {schema}.operation_logs WHERE operation_type='DEMO_DATA_RESET' AND operation_result='FAILED'")),
    "repeatedContentDigest": digests[0],
    "verifiedChecks": ["five-active-status-blockers", "wrong-phrase-no-change", "mid-reset-rollback-to-before-snapshot",
                       "repeat-content-digest", "success-and-failure-audit"]
}
path = isolated.env.EVIDENCE / "20261024-group3-reset-isolated.json"
isolated.env.save(path, record)
print(json.dumps({"schema": schema, "junit": record["junit"], "devices": record["canonicalDeviceCount"],
                  "capabilities": record["canonicalCapabilityCount"], "digest": digests[0],
                  "evidence": str(path)}, ensure_ascii=False))
