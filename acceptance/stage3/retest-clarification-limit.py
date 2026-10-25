"""TC-032.S2: three real clarification submissions for an incomplete fictional goal."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
db_spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(db_spec)
db_spec.loader.exec_module(db)
api = local.API("运行操作员")
goal = "请协助一名虚构旅客，地点和服务类型尚待确认。"
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "submitRequest": {"taskGoal": goal, "taskFamily": "SPECIAL_PASSENGER_SERVICE"},
      "observations": {"rounds": []}, "cleanup": {}}
out = Path(__file__).parent / "evidence/TC-032-three-clarifications.json"
before = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
task_id = None
try:
    try:
        ev["observations"]["submitResponse"] = api("/tasks", "POST", ev["submitRequest"])
    except RuntimeError as error:
        ev["observations"]["submitError"] = str(error)
    after = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
    if after <= before:
        raise RuntimeError("submission did not create a task")
    task_id = after
    task = api(f"/tasks/{task_id}")
    ev["observations"]["afterSubmit"] = task
    for round_no in range(1, 4):
        if task["status"] != "PLANNING" or not task.get("missingInfoQuestions"):
            break
        answers = {q: "虚构测试资料未确认，暂不能给出该字段" for q in task["missingInfoQuestions"]}
        record = {"round": round_no, "questions": task["missingInfoQuestions"], "answers": answers}
        try:
            record["response"] = api(f"/tasks/{task_id}/clarify", "POST", {"answers": answers})
        except RuntimeError as error:
            record["error"] = str(error)
        task = api(f"/tasks/{task_id}")
        record["afterStatus"] = task["status"]
        record["remainingQuestions"] = task.get("missingInfoQuestions")
        ev["observations"]["rounds"].append(record)
    ev["observations"]["finalTask"] = task
    ev["observations"]["events"] = api(f"/tasks/{task_id}/events")
    ev["observations"]["planVersions"] = api(f"/tasks/{task_id}/plan-versions")
finally:
    if task_id:
        try:
            state = api(f"/tasks/{task_id}")
            if state["status"] in ["PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT", "DOWNGRADING", "EXECUTING"]:
                ev["cleanup"]["terminate"] = api(f"/tasks/{task_id}/terminate", "POST",
                    {"confirmed": True, "reason": "阶段3三轮补充复测清场"})["status"]
        except Exception as error:
            ev["cleanup"]["error"] = str(error)
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"taskId": task_id, "rounds": len(ev["observations"]["rounds"]),
                  "statuses": [r["afterStatus"] for r in ev["observations"]["rounds"]],
                  "final": ev["observations"].get("finalTask", {}).get("status"),
                  "planVersions": len(ev["observations"].get("planVersions", [])),
                  "events": [e["eventType"] for e in ev["observations"].get("events", [])]}, ensure_ascii=False))
