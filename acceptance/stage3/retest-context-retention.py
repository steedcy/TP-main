"""SRS_F027.R05: read original task 19's persisted planning snapshots."""
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
snapshots = api("/tasks/19/context-snapshots")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "taskId": 19,
      "taskCode": task["taskCode"], "taskStatus": task["status"],
      "snapshots": snapshots,
      "events": [e for e in api("/tasks/19/events")
                 if e["eventType"] == "CONTEXT_SNAPSHOT_GENERATED"]}
out = stage / "evidence" / ("TC-084-context-retention-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "snapshotCount": len(snapshots),
                  "snapshotIds": [x.get("id") for x in snapshots],
                  "eventCount": len(ev["events"])}, ensure_ascii=False))
