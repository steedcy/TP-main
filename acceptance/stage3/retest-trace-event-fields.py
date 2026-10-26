"""SRS_F027.R02: inspect all persisted event fields on completed task 19."""
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
task = api("/tasks/19")
assert task["status"] == "COMPLETED"
events = api("/tasks/19/events")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "taskId": 19,
      "taskStatus": task["status"], "events": events,
      "summary": {"count": len(events),
                  "missingReasonCode": sum(not e.get("reasonCode") for e in events),
                  "completeOtherFields": all(e.get("eventType") and e.get("occurredAt")
                                             and e.get("trigger") and e.get("detailSummary")
                                             for e in events)}}
out = stage / "evidence" / ("TC-084-trace-event-fields-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "summary": ev["summary"]}, ensure_ascii=False))
