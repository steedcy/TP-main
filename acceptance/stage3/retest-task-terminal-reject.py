"""SRS_F021.R07: a manually terminated task cannot be terminated again."""
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
before = api("/tasks/64")
events = api("/tasks/64/events")
assert before["status"] == "MANUAL_TERMINATED"
digest = lambda rows: hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "taskId": 64,
      "before": {"status": before["status"], "eventCount": len(events), "eventsSha256": digest(events)}}
try:
    api("/tasks/64/terminate", "POST",
        {"reason": "阶段3终态重复终止必须拒绝", "confirmed": True})
    ev["repeatTerminate"] = {"accepted": True}
except RuntimeError as error:
    ev["repeatTerminate"] = {"accepted": False, "error": str(error)}
after = api("/tasks/64")
after_events = api("/tasks/64/events")
ev["after"] = {"status": after["status"], "eventCount": len(after_events),
               "eventsSha256": digest(after_events)}
out = stage / "evidence" / ("TC-066-terminal-reject-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "before": ev["before"],
                  "repeatTerminate": ev["repeatTerminate"], "after": ev["after"]},
                 ensure_ascii=False))
