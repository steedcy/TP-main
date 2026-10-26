"""F028.R05: challenge a persisted task termination operation log with PUT/DELETE."""
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("系统管理员")

def target_row():
    response = api("/operation-logs?operationType=TASK_TERMINATE&page=1&size=100")
    rows = [row for row in response["content"]
            if row["operationTarget"] == "TASK-20261027-0064"]
    assert len(rows) == 1
    return rows[0]

def digest(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

before = target_row()
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "logId": before["id"],
      "operationType": before["operationType"], "target": before["operationTarget"],
      "before": {"sha256": digest(before), "createdAt": before["createdAt"],
                 "operationResult": before["operationResult"]}, "attempts": []}
for method, body in (("PUT", {"detail": "STAGE3_MUST_NOT_EDIT"}), ("DELETE", None)):
    try:
        result = api(f"/operation-logs/{before['id']}", method, body)
        ev["attempts"].append({"method": method, "accepted": True, "response": result})
    except RuntimeError as error:
        ev["attempts"].append({"method": method, "accepted": False, "error": str(error)})
after = target_row()
ev["after"] = {"sha256": digest(after), "createdAt": after["createdAt"],
               "operationResult": after["operationResult"],
               "injectedTextAbsent": "STAGE3_MUST_NOT_EDIT" not in json.dumps(after)}
out = stage / "evidence" / ("SRS_F028-audit-immutability-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "logId": ev["logId"],
                  "attempts": ev["attempts"], "unchanged": ev["before"]["sha256"] == ev["after"]["sha256"]},
                 ensure_ascii=False))
