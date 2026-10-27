"""TC-092.S1: prove the current single Windows environment served a core task."""
import importlib.util
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


local = module("local", root / "scripts/local-test-environment.py")
db = module("db", root / "acceptance/stage2/db-isolation.py")
operator = local.API("运行操作员")
task_id = 73  # Created and completed in this Stage 3 run, after the recorded local startup.
task = operator(f"/tasks/{task_id}")
plans = operator(f"/tasks/{task_id}/plan-versions")
assignments = operator(f"/tasks/{task_id}/step-assignments")
events = operator(f"/tasks/{task_id}/events")
processes = json.loads((root / ".local-test/processes.json").read_text(encoding="utf-8"))
startup = {key: processes[key] for key in ("backend", "frontend", "planning-fixture")}
with urllib.request.urlopen("http://127.0.0.1:8080/actuator/health", timeout=5) as response:
    health = {"httpStatus": response.status, "body": json.load(response)}
with urllib.request.urlopen("http://127.0.0.1:5173/", timeout=5) as response:
    body = response.read().decode("utf-8")
    frontend = {"httpStatus": response.status, "htmlShell": "<div id=\"app\"></div>" in body,
                "contentType": response.headers.get("Content-Type")}
database = db.query(db.source, "SELECT current_database() || '|' || current_schema() || '|' || count(*) "
                    "FROM tip_stage2_v14.tasks")
evidence = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
            "environment": "one Windows development host, localhost backend/frontend and local database",
            "startupRecords": startup, "backendHealth": health, "frontend": frontend,
            "database": database, "coreTask": task, "planVersions": plans,
            "assignments": assignments, "events": events}
out = stage / "evidence" / ("TC-092-single-environment-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": out.name, "backendStatus": health,
                  "frontend": frontend, "database": database,
                  "taskId": task_id, "taskStatus": task["status"],
                  "assignmentStatuses": [row["stepStatus"] for row in assignments],
                  "eventCount": len(events)}, ensure_ascii=False))
