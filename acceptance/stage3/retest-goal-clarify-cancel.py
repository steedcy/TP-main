"""TC-031.S2/S3: submit an incomplete fictional goal, clarify, then cancel pre-plan."""
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
goal = "请处理一件虚构超规行李，详细位置和尺寸尚待确认。"
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "submitRequest": {"taskGoal": goal, "taskFamily": "OVERSIZE_BAGGAGE_HANDLING"},
      "observations": {}, "cleanup": {}}
out = Path(__file__).parent / "evidence/TC-031-goal-clarify-cancel.json"
before = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
task_id = None
try:
    try:
        ev["observations"]["submitResponse"] = api("/tasks", "POST", ev["submitRequest"])
    except RuntimeError as error:
        ev["observations"]["submitError"] = str(error)
    after = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
    ev["observations"]["beforeMaxId"] = before
    ev["observations"]["afterMaxId"] = after
    if after <= before:
        raise RuntimeError("submission did not create a task")
    task_id = after
    task = api(f"/tasks/{task_id}")
    ev["observations"]["afterSubmit"] = task
    if task["status"] == "PLANNING" and task.get("missingInfoQuestions"):
        answers = {q: "虚构测试信息尚待确认" for q in task["missingInfoQuestions"]}
        ev["observations"]["clarifyRequest"] = {"answers": answers}
        try:
            ev["observations"]["clarifyResponse"] = api(f"/tasks/{task_id}/clarify", "POST", {"answers": answers})
        except RuntimeError as error:
            ev["observations"]["clarifyError"] = str(error)
    ev["observations"]["afterClarify"] = api(f"/tasks/{task_id}")
    if ev["observations"]["afterClarify"]["status"] == "PLANNING":
        ev["observations"]["cancelResponse"] = api(f"/tasks/{task_id}/cancel", "POST",
            {"reason": "阶段3目标理解补充后取消复测"})
    ev["observations"]["finalTask"] = api(f"/tasks/{task_id}")
    ev["observations"]["events"] = api(f"/tasks/{task_id}/events")
    ev["observations"]["planVersionCount"] = len(api(f"/tasks/{task_id}/plan-versions"))
finally:
    if task_id:
        try:
            state = api(f"/tasks/{task_id}")
            if state["status"] in ["PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT", "DOWNGRADING", "EXECUTING"]:
                ev["cleanup"]["terminate"] = api(f"/tasks/{task_id}/terminate", "POST",
                    {"confirmed": True, "reason": "阶段3目标理解隔离任务清场"})["status"]
        except Exception as error:
            ev["cleanup"]["error"] = str(error)
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"taskId": task_id,
                  "afterSubmit": ev["observations"].get("afterSubmit", {}).get("status"),
                  "afterClarify": ev["observations"].get("afterClarify", {}).get("status"),
                  "final": ev["observations"].get("finalTask", {}).get("status"),
                  "eventTypes": [x["eventType"] for x in ev["observations"].get("events", [])],
                  "planVersions": ev["observations"].get("planVersionCount")}, ensure_ascii=False))
