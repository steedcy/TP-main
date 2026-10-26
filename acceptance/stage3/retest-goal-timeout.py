"""TC-034: controlled >60s goal-understanding response and concurrent read checks."""
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
assert source["status"] == "COMPLETED"
mode_path = root / ".local-test/planning-fault.json"
journal = root / ".local-test/planning-requests.jsonl"
old_mode = mode_path.read_text(encoding="utf-8")
old_count = len(journal.read_text(encoding="utf-8").splitlines()) if journal.exists() else 0
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "schema": "tip_stage2_v14", "fixtureModeBefore": json.loads(old_mode),
      "fixtureModeDuring": None, "beforeMaxTaskId": int(db.query(db.source,
      "SELECT max(id) FROM tip_stage2_v14.tasks")), "request": None,
      "submit": None, "submitError": None, "submitElapsedSeconds": None,
      "concurrentReads": {}, "afterMaxTaskId": None, "task": None,
      "events": None, "contexts": None, "plans": None, "modelRequests": [],
      "fixtureModeRestored": False}
out = Path(__file__).parent / "evidence" / (
    "TC-034-goal-timeout-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
request = {"taskGoal": source["taskGoal"], "taskFamily": source["taskFamily"],
           "sceneParams": source["sceneParams"]}
ev["request"] = request

def submit():
    start = time.monotonic()
    try:
        return {"response": operator("/tasks", "POST", request), "error": None,
                "elapsedSeconds": time.monotonic() - start}
    except Exception as error:
        return {"response": None, "error": str(error),
                "elapsedSeconds": time.monotonic() - start}

try:
    mode = json.loads(old_mode)
    mode.update(goal="timeout", planning="success", replanning="success", delaySeconds=65)
    mode_path.write_text(json.dumps(mode, ensure_ascii=False), encoding="utf-8")
    ev["fixtureModeDuring"] = mode
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(submit)
        time.sleep(5)
        pending_id = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
        ev["concurrentReads"]["taskIdAtFiveSeconds"] = pending_id
        paths = {"dashboard": "/dashboard/overview?period=TODAY",
                 "devices": "/devices?page=1&size=20",
                 "task": "/tasks/19"}
        for label, path in paths.items():
            start = time.monotonic()
            try:
                data = config(path) if label == "devices" else operator(path)
                ev["concurrentReads"][label] = {"ok": True,
                    "elapsedSeconds": time.monotonic() - start,
                    "status": data.get("status") if isinstance(data, dict) else None,
                    "response": data}
            except Exception as error:
                ev["concurrentReads"][label] = {"ok": False,
                    "elapsedSeconds": time.monotonic() - start, "error": str(error)}
        result = future.result(timeout=80)
    ev["submit"] = result["response"]
    ev["submitError"] = result["error"]
    ev["submitElapsedSeconds"] = result["elapsedSeconds"]
finally:
    mode_path.write_text(old_mode, encoding="utf-8")
    ev["fixtureModeRestored"] = mode_path.read_text(encoding="utf-8") == old_mode
    ev["afterMaxTaskId"] = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
    if ev["afterMaxTaskId"] > ev["beforeMaxTaskId"]:
        task_id = ev["afterMaxTaskId"]
        ev["task"] = operator(f"/tasks/{task_id}")
        ev["events"] = operator(f"/tasks/{task_id}/events")
        ev["contexts"] = operator(f"/tasks/{task_id}/context-snapshots")
        ev["plans"] = operator(f"/tasks/{task_id}/plan-versions")
    ev["modelRequests"] = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()[old_count:]]
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"taskId": ev["afterMaxTaskId"] if ev["afterMaxTaskId"] > ev["beforeMaxTaskId"] else None,
                  "submitError": ev["submitError"], "elapsedSeconds": ev["submitElapsedSeconds"],
                  "taskStatus": ev["task"]["status"] if ev["task"] else None,
                  "reads": {k: v.get("ok") for k, v in ev["concurrentReads"].items() if isinstance(v, dict)},
                  "modelPhases": [r["phase"] for r in ev["modelRequests"]],
                  "fixtureModeRestored": ev["fixtureModeRestored"], "evidence": str(out)}, ensure_ascii=False))
