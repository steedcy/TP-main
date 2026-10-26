"""SRS_F021.R01: server rejects absent reason, missing confirmation, >200 chars."""
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
task = api("/tasks/20")
events = api("/tasks/20/events")
assert task["status"] == "PENDING_MANUAL"
digest = lambda rows: hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "taskId": 20,
      "before": {"status": task["status"], "eventCount": len(events), "eventsSha256": digest(events)},
      "cases": []}
for name, body in [
    ("emptyReason", {"reason": "", "confirmed": True}),
    ("notConfirmed", {"reason": "阶段3验证无二次确认", "confirmed": False}),
    ("over200", {"reason": "X" * 201, "confirmed": True})]:
    try:
        api("/tasks/20/terminate", "POST", body)
        ev["cases"].append({"name": name, "accepted": True})
    except RuntimeError as error:
        ev["cases"].append({"name": name, "accepted": False, "error": str(error)})
after = api("/tasks/20")
after_events = api("/tasks/20/events")
ev["after"] = {"status": after["status"], "eventCount": len(after_events),
               "eventsSha256": digest(after_events)}
out = stage / "evidence" / ("TC-066-terminate-validation-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "cases": ev["cases"],
                  "after": ev["after"]}, ensure_ascii=False))
