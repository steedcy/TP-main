"""TC-032.S1: freeze final task 37, plan, context and event evidence."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("运行操作员")
start = json.loads((Path(__file__).parent / "evidence/TC-032-complete-start.json").read_text(encoding="utf-8"))
task_id = start["observations"]["task"]["id"]
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "taskId": task_id, "start": start["observations"]["task"],
      "final": api(f"/tasks/{task_id}"),
      "events": api(f"/tasks/{task_id}/events"),
      "plans": api(f"/tasks/{task_id}/plan-versions"),
      "contexts": api(f"/tasks/{task_id}/context-snapshots"),
      "assignments": api(f"/tasks/{task_id}/step-assignments")}
(Path(__file__).parent / "evidence/TC-032-complete-result.json").write_text(
    json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"taskId": task_id, "status": ev["final"]["status"],
                  "goalUnchanged": ev["final"]["taskGoal"] == start["request"]["taskGoal"],
                  "planCount": len(ev["plans"]), "contextCount": len(ev["contexts"]),
                  "assignments": len(ev["assignments"]),
                  "eventTypes": [x["eventType"] for x in ev["events"][:8]]}, ensure_ascii=False))
