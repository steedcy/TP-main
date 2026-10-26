"""TC-038 follow-up: missing plan field and parallel reads during model timeout."""
import concurrent.futures
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
request = {"taskGoal": source["taskGoal"], "taskFamily": source["taskFamily"],
           "sceneParams": source["sceneParams"]}
mode_path = root / ".local-test/planning-fault.json"
journal = root / ".local-test/planning-requests.jsonl"
original = mode_path.read_text(encoding="utf-8")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "schema": "tip_stage2_v14",
      "runtimeInput": "V1.5", "fixtureModeBefore": json.loads(original),
      "request": request, "cases": [], "fixtureModeRestored": False, "agentsAfter": None}
out = Path(__file__).parent / "evidence" / (
    "TC-038-planning-boundary-followup-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")

def submit():
    started = time.monotonic()
    try:
        return {"response": operator("/tasks", "POST", request), "error": None,
                "elapsedSeconds": time.monotonic() - started}
    except Exception as error:
        return {"response": None, "error": str(error),
                "elapsedSeconds": time.monotonic() - started}

try:
    for label in ["missing_field", "timeout_probe"]:
        mode = json.loads(original)
        mode.update(goal="success", planning="success" if label == "missing_field" else "timeout",
                    replanning="success", delaySeconds=65)
        if label == "missing_field":
            mode["initialPlanSteps"] = [{"stepSeq": 1, "capabilityType": "CAP_NAVIGATION",
                "inputParams": {"targetLocation": "F2_TEST_GATE", "routePreference": "BARRIER_FREE"},
                "precondition": "设备在线空闲", "completionCondition": "routeGenerated=true",
                "failureHandling": "失败转人工"}]
        else:
            mode.pop("initialPlanSteps", None)
        mode_path.write_text(json.dumps(mode, ensure_ascii=False), encoding="utf-8")
        old_lines = len(journal.read_text(encoding="utf-8").splitlines())
        case = {"label": label, "fixtureModeDuring": mode,
                "beforeMaxTaskId": int(db.query(db.source,
                    "SELECT max(id) FROM tip_stage2_v14.tasks")),
                "response": None, "submitError": None, "elapsedSeconds": None,
                "concurrentReads": {}, "afterMaxTaskId": None,
                "task": None, "events": None, "contexts": None, "plans": None,
                "deviceCommands": None, "modelRequests": None}
        ev["cases"].append(case)
        if label == "timeout_probe":
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(submit)
                time.sleep(5)
                for name, path in [("dashboard", "/dashboard/overview?period=TODAY"),
                                   ("devices", "/devices?page=1&size=20"),
                                   ("task", "/tasks/19")]:
                    started = time.monotonic()
                    try:
                        value = config(path) if name == "devices" else operator(path)
                        case["concurrentReads"][name] = {"ok": True,
                            "elapsedSeconds": time.monotonic() - started, "response": value}
                    except Exception as error:
                        case["concurrentReads"][name] = {"ok": False,
                            "elapsedSeconds": time.monotonic() - started, "error": str(error)}
                result = future.result(timeout=80)
        else:
            result = submit()
        case["response"], case["submitError"] = result["response"], result["error"]
        case["elapsedSeconds"] = result["elapsedSeconds"]
        case["afterMaxTaskId"] = int(db.query(db.source,
            "SELECT max(id) FROM tip_stage2_v14.tasks"))
        if case["afterMaxTaskId"] > case["beforeMaxTaskId"]:
            task_id = case["afterMaxTaskId"]
            deadline = time.monotonic() + 45
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
        case["modelRequests"] = [json.loads(line) for line in
            journal.read_text(encoding="utf-8").splitlines()[old_lines:]]
        out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
finally:
    mode_path.write_text(original, encoding="utf-8")
    ev["fixtureModeRestored"] = mode_path.read_text(encoding="utf-8") == original
    ev["agentsAfter"] = [a for a in config("/device-agents?page=1&size=100")["content"]
                         if a["deviceCode"].startswith("SIM_F2_")]
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"cases": [{"label": c["label"], "taskId": c["afterMaxTaskId"],
                             "status": c["task"]["status"] if c["task"] else None,
                             "elapsedSeconds": round(c["elapsedSeconds"], 2),
                             "reasons": [e["reasonCode"] for e in c["events"] if e["reasonCode"]]
                             if c["events"] else [],
                             "reads": {k: r["ok"] for k, r in c["concurrentReads"].items()}}
                            for c in ev["cases"]],
                  "restored": ev["fixtureModeRestored"], "evidence": str(out)}, ensure_ascii=False))
