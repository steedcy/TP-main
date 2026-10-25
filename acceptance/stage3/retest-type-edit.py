"""TC-017.S2: type boundary validation, safe edit/restore, and audit detail."""
import csv
import importlib.util
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


local = module("local", root / "scripts/local-test-environment.py")
db = module("db", root / "acceptance/stage2/db-isolation.py")
api = local.API("配置管理员")
code = "SMART_DISPLAY"
path = "/device-types/" + code + "/capability-boundary"
original = api(path)
fields = {"supportedCapabilityTypes": original["supportedCapabilityTypes"],
          "typeDescription": original["typeDescription"],
          "typicalScenarios": original["typicalScenarios"],
          "constraintRules": original["constraintRules"]}


def status(payload):
    request = urllib.request.Request(local.BASE + path,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), method="PUT",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + api.token})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def audit():
    result = db.query(db.source,
        "SELECT count(*),count(detail) FROM tip_stage2_v14.operation_logs "
        "WHERE operation_type='DEVICE_TYPE_BOUNDARY_UPDATE' "
        "AND operation_target='SMART_DISPLAY'")
    count, detail_count = result.split("|")
    return {"count": int(count), "withDetail": int(detail_count)}


before_audit = audit()
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "deviceTypeCode": code,
      "emptyCapabilitiesStatus": status(dict(fields, supportedCapabilityTypes=[])),
      "description501Status": status(dict(fields, typeDescription="A" * 501)),
      "scenarios1001Status": status(dict(fields, typicalScenarios="B" * 1001)),
      "constraints1001Status": status(dict(fields, constraintRules="C" * 1001))}
try:
    max_fields = dict(fields, typeDescription="A" * 500,
                      typicalScenarios="B" * 1000, constraintRules="C" * 1000)
    updated = api(path, "PUT", max_fields)
    ev["maxBoundariesAccepted"] = (
        len(updated["typeDescription"]) == 500 and len(updated["typicalScenarios"]) == 1000
        and len(updated["constraintRules"]) == 1000)
    ev["updatedByPresent"] = bool(updated.get("updatedBy"))
    ev["updatedAtPresent"] = bool(updated.get("updatedAt"))
    zero = api(path, "PUT", dict(fields, typeDescription="", typicalScenarios="", constraintRules=""))
    ev["zeroLengthsAccepted"] = all(zero[key] == "" for key in ("typeDescription", "typicalScenarios", "constraintRules"))
finally:
    api(path, "PUT", fields)
    restored = api(path)
    ev["restoredOriginalFields"] = all(restored[key] == value for key, value in fields.items())
after_audit = audit()
ev["auditRecordDelta"] = after_audit["count"] - before_audit["count"]
ev["auditDetailRecordDelta"] = after_audit["withDetail"] - before_audit["withDetail"]
out = Path(__file__).resolve().parent / "evidence/TC-017-type-edit.json"
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(ev, ensure_ascii=False))
