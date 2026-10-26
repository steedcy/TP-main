"""TC-038: live six-step, malformed, and 65-second planning responses."""
import importlib.util
import json
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
db_spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(db_spec)
db_spec.loader.exec_module(db)
operator, config = local.API("运行操作员"), local.API("配置管理员")
source = operator("/tasks/19")
assert source["status"] == "COMPLETED"
request = {"taskGoal": source["taskGoal"], "taskFamily": source["taskFamily"],
           "sceneParams": source["sceneParams"]}
mode_path = root / ".local-test/planning-fault.json"
journal = root / ".local-test/planning-requests.jsonl"
old_mode = mode_path.read_text(encoding="utf-8")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "schema": "tip_stage2_v14", "fixtureModeBefore": json.loads(old_mode),
      "request": request, "cases": [], "fixtureModeRestored": False,
      "agentsAfter": None}
out = Path(__file__).parent / "evidence" / (
    "TC-038-planning-faults-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
try:
    for selected in ["too_many_steps", "malformed", "timeout"]:
        mode = json.loads(old_mode)
        mode.update(goal="success", planning=selected, replanning="success", delaySeconds=65)
        mode_path.write_text(json.dumps(mode, ensure_ascii=False), encoding="utf-8")
        old_lines = len(journal.read_text(encoding="utf-8").splitlines()) if journal.exists() else 0
        case = {"mode": selected, "fixtureModeDuring": mode,
                "beforeMaxTaskId": int(db.query(db.source,
                    "SELECT max(id) FROM tip_stage2_v14.tasks")),
                "response": None, "submitError": None, "elapsedSeconds": None,
                "afterMaxTaskId": None, "task": None, "events": None, "contexts": None,
                "plans": None, "deviceCommands": None, "assignments": None,
                "modelRequests": None, "cleanup": None}
        ev["cases"].append(case)
        started = time.monotonic()
        try:
            case["response"] = operator("/tasks", "POST", request)
        except Exception as error:
            case["submitError"] = str(error)
        case["elapsedSeconds"] = time.monotonic() - started
        case["afterMaxTaskId"] = int(db.query(db.source,
            "SELECT max(id) FROM tip_stage2_v14.tasks"))
        if case["afterMaxTaskId"] > case["beforeMaxTaskId"]:
            task_id = case["afterMaxTaskId"]
            deadline = time.monotonic() + 50
            while time.monotonic() < deadline:
                case["task"] = operator(f"/tasks/{task_id}")
                if case["task"]["status"] not in ["PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT",
                                                   "DOWNGRADING", "EXECUTING"]:
                    break
                time.sleep(1)
            case["events"] = operator(f"/tasks/{task_id}/events")
            case["contexts"] = operator(f"/tasks/{task_id}/context-snapshots")
            case["plans"] = operator(f"/tasks/{task_id}/plan-versions")
            case["deviceCommands"] = db.query(db.source,
                f"SELECT command_status,capability_type FROM tip_stage2_v14.device_commands WHERE task_id={task_id} ORDER BY id")
            case["assignments"] = db.query(db.source,
                f"SELECT step_seq,step_status FROM tip_stage2_v14.task_step_assignments WHERE task_id={task_id} ORDER BY id")
        case["modelRequests"] = [json.loads(line) for line in
            journal.read_text(encoding="utf-8").splitlines()[old_lines:]]
        out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
finally:
    mode_path.write_text(old_mode, encoding="utf-8")
    ev["fixtureModeRestored"] = mode_path.read_text(encoding="utf-8") == old_mode
    ev["agentsAfter"] = [a for a in config("/device-agents?page=1&size=100")["content"]
                         if a["deviceCode"].startswith("SIM_F2_")]
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"cases": [{"mode": c["mode"], "taskId": c["afterMaxTaskId"],
                             "status": c["task"]["status"] if c["task"] else None,
                             "seconds": round(c["elapsedSeconds"], 2),
                             "modelPhases": [r["phase"] for r in c["modelRequests"]],
                             "reasonCodes": [e["reasonCode"] for e in c["events"] if e["reasonCode"]]
                             if c["events"] else []} for c in ev["cases"]],
                  "restored": ev["fixtureModeRestored"], "evidence": str(out)}, ensure_ascii=False))
