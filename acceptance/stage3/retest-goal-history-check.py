"""TC-031.S3: compare fresh canceled task and stage-3 downgraded task originals."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("运行操作员")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5", "tasks": {}}
for task_id in [19, 34]:
    task = api(f"/tasks/{task_id}")
    plans = api(f"/tasks/{task_id}/plan-versions")
    events = api(f"/tasks/{task_id}/events")
    ev["tasks"][str(task_id)] = {"task": task, "plans": plans, "events": events,
        "originalGoalUnchanged": task["taskGoal"] == (task.get("goalParsingResult") or {}).get("originalGoal")}
(Path(__file__).parent / "evidence/TC-031-goal-history-check.json").write_text(
    json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({task_id: {"status": row["task"]["status"], "goalUnchanged": row["originalGoalUnchanged"],
                            "planSources": [p.get("source") for p in row["plans"]],
                            "events": [e["eventType"] for e in row["events"]]}
                  for task_id, row in ev["tasks"].items()}, ensure_ascii=False))
