"""SRS_F027.R03: reject edits/deletes of a real persisted task event."""
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
api = local.API("运行操作员")
events = api("/tasks/19/events")
assert len(events) == 27
event_id = events[0]["id"]
def digest(rows):
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "taskId": 19, "eventId": event_id,
      "before": {"count": len(events), "sha256": digest(events)}, "attempts": []}
for method, body in (("PUT", {"detailSummary": "STAGE3_MUST_NOT_EDIT"}),
                     ("DELETE", None)):
    try:
        result = api(f"/tasks/19/events/{event_id}", method, body)
        ev["attempts"].append({"method": method, "accepted": True, "response": result})
    except RuntimeError as error:
        ev["attempts"].append({"method": method, "accepted": False, "error": str(error)})
after = api("/tasks/19/events")
ev["after"] = {"count": len(after), "sha256": digest(after),
               "eventStillPresent": any(e["id"] == event_id for e in after),
               "injectedTextAbsent": "STAGE3_MUST_NOT_EDIT" not in json.dumps(after)}
out = stage / "evidence" / ("TC-084-trace-immutability-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "attempts": ev["attempts"],
                  "before": ev["before"], "after": ev["after"]}, ensure_ascii=False))
