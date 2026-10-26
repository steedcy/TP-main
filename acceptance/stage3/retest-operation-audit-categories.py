"""Read this stage's persisted operation categories and denied login records."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
admin = local.API("系统管理员")
fields = ("id", "username", "role", "operationType", "operationTarget",
          "operationResult", "sourceIp", "createdAt")

def rows(operation_type, result=None):
    query = "/operation-logs?operationType=" + quote(operation_type) + "&page=1&size=100"
    if result:
        query += "&operationResult=" + quote(result)
    return admin(query)["content"]

def pick(operation_type, predicate, result=None):
    matches = [row for row in rows(operation_type, result) if predicate(row)]
    assert matches, (operation_type, result)
    return {key: matches[0].get(key) for key in fields}

samples = {
    "loginSuccess": pick("LOGIN", lambda r: r["operationResult"] == "SUCCESS", "SUCCESS"),
    "loginFailure": pick("LOGIN", lambda r: r["operationResult"] == "FAILED" and
                         r["username"].startswith("s3"), "FAILED"),
    "deviceConfig": pick("DEVICE_CREATE", lambda r: (r["operationTarget"] or "").startswith("S3_")),
    "capabilityEnable": pick("DEVICE_CAPABILITY_STATUS_CHANGE", lambda r:
                             (r["operationTarget"] or "").endswith(" -> ENABLED")),
    "capabilityDisable": pick("DEVICE_CAPABILITY_STATUS_CHANGE", lambda r:
                              (r["operationTarget"] or "").endswith(" -> DISABLED")),
    "templateEnable": pick("BASELINE_TEMPLATE_ENABLE", lambda r:
                           r["operationTarget"] == "S3_TC028_DISPLAY_DRYRUN"),
    "templateDisable": pick("BASELINE_TEMPLATE_DISABLE", lambda r:
                            r["operationTarget"] == "S3_TC028_DISPLAY_DRYRUN"),
    "manualTerminate": pick("TASK_TERMINATE", lambda r:
                            r["operationTarget"] == "TASK-20261027-0064"),
    "accessDenied": pick("ACCESS_DENIED", lambda r:
                         r["operationTarget"] == "/api/v1/tasks/19/events" and
                         r["operationResult"] == "FAILED")}
assert all(row["createdAt"] >= "2026-10-25" for row in samples.values())
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "source": "system administrator operation-logs API",
      "samples": samples,
      "linkedStage3Evidence": [
          "acceptance/stage3/evidence/TC-002-lockout.json",
          "acceptance/stage3/evidence/TC-043-risk-rule-crud-20261026T071245Z.json",
          "acceptance/stage3/evidence/TC-066-terminate-live-20261026T174242Z.json",
          "acceptance/stage3/evidence/TC-084-trace-permissions-20261026T204811Z.json"]}
out = stage / "evidence" / ("SRS_F028-audit-categories-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "sampleIds": {key: row["id"] for key, row in samples.items()}},
                 ensure_ascii=False))
