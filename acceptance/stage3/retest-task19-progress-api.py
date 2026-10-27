"""Capture task 19's final step completion and event trail for TC-054.S2."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
operator = local.API("运行操作员")
task = operator("/tasks/19")
plans = operator("/tasks/19/plan-versions")
assignments = operator("/tasks/19/step-assignments")
events = operator("/tasks/19/events")
current = next(plan for plan in plans if plan["id"] == task["currentPlanVersionId"])
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "task": task,
      "currentPlan": current, "assignments": assignments, "events": events}
name = "TC-054-progress-api-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json"
out = stage / "evidence" / name
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": name, "status": task["status"],
                  "plannedSteps": len(current["planSteps"]), "assignments": len(assignments),
                  "assignmentStatuses": [a.get("status") for a in assignments],
                  "eventTypes": [e["eventType"] for e in events[-3:]]}, ensure_ascii=False))
