"""Try a controlled positive RETRY_PLANNING path after three unanswered questions."""
import importlib.util
import json
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
operator = local.API("运行操作员")
config = local.API("配置管理员")
mode_path = root / ".local-test/planning-fault.json"
journal = root / ".local-test/planning-requests.jsonl"
original_mode = mode_path.read_text(encoding="utf-8")
source_plan = operator("/tasks/69/plan-versions")[0]
assert source_plan["source"] == "BASELINE_TEMPLATE"
assert all(source_plan[key] == "PASS" for key in
           ("structureCheckResult", "capabilityCheckResult", "constraintCheckResult"))
marker = "S3_TC064_RETRY_POSITIVE_20261027"
goal = "请协助一名虚构旅客完成机场特殊旅客服务，服务类型及起终点尚待确认。" + marker
answer = "虚构测试资料未确认，暂不能给出该字段"
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "goalMarker": marker,
      "sourcePlanId": source_plan["id"], "fixtureModeBefore": json.loads(original_mode),
      "clarifications": [], "fixtureModeRestored": False}
out = stage / "evidence" / ("TC-064-retry-positive-fixture-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
task_id = None
try:
    task = operator("/tasks", "POST", {"taskGoal": goal,
                    "taskFamily": "SPECIAL_PASSENGER_SERVICE"})
    task_id = task["id"]
    ev["created"] = {k: task.get(k) for k in ("id", "taskCode", "status", "taskGoal")}
    for turn in range(3):
        deadline = time.monotonic() + 20
        while task["status"] == "PLANNING" and not task.get("missingInfoQuestions") and time.monotonic() < deadline:
            time.sleep(.5)
            task = operator(f"/tasks/{task_id}")
        assert task["status"] == "PLANNING" and task.get("missingInfoQuestions")
        questions = task["missingInfoQuestions"]
        task = operator(f"/tasks/{task_id}/clarify", "POST",
                        {"answers": {question: answer for question in questions}})
        ev["clarifications"].append({"turn": turn + 1, "questions": questions,
                                     "returnedStatus": task["status"]})
    assert task["status"] == "PENDING_MANUAL"
    ev["before"] = {k: task.get(k) for k in
                    ("status", "failureReason", "currentPlanVersionId")}
    mode = json.loads(original_mode)
    mode.update(goal="success", planning="success", replanning="success",
                initialPlanSteps=source_plan["planSteps"])
    mode_path.write_text(json.dumps(mode, ensure_ascii=False), encoding="utf-8")
    ev["fixtureModeDuring"] = mode
    journal_offset = len(journal.read_text(encoding="utf-8").splitlines())
    try:
        response = operator(f"/tasks/{task_id}/manual-actions", "POST",
                            {"action": "RETRY_PLANNING"})
        ev["action"] = {"accepted": True, "returned": {k: response.get(k) for k in
                        ("status", "failureReason", "currentPlanVersionId")}}
    except RuntimeError as error:
        ev["action"] = {"accepted": False, "error": str(error)}
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        task = operator(f"/tasks/{task_id}")
        if task["status"] not in {"PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT", "DOWNGRADING"}:
            break
        time.sleep(.5)
    ev["after"] = {k: task.get(k) for k in
                   ("status", "failureReason", "currentPlanVersionId", "replanUsed")}
    ev["plans"] = operator(f"/tasks/{task_id}/plan-versions")
    ev["events"] = operator(f"/tasks/{task_id}/events")
    ev["modelRequests"] = [json.loads(line) for line in
                           journal.read_text(encoding="utf-8").splitlines()[journal_offset:]]
finally:
    mode_path.write_text(original_mode, encoding="utf-8")
    ev["fixtureModeRestored"] = mode_path.read_text(encoding="utf-8") == original_mode
    if task_id is not None:
        current = operator(f"/tasks/{task_id}")
        ev["statusBeforeCleanup"] = current["status"]
        if current["status"] in {"PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT",
                                 "DOWNGRADING", "EXECUTING", "PENDING_MANUAL"}:
            try:
                ev["cleanup"] = operator(f"/tasks/{task_id}/terminate", "POST",
                                         {"reason": "阶段3正向重试规划夹具已记录",
                                          "confirmed": True})["status"]
            except RuntimeError as error:
                ev["cleanupError"] = str(error)
    ev["simulatorAgents"] = [{key: a.get(key) for key in
                              ("deviceCode", "agentStatus", "onlineStatus", "workStatus", "currentTaskId")}
                             for a in config("/device-agents?page=1&size=100")["content"]
                             if a["deviceCode"].startswith("SIM_F2_")]
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "taskId": task_id,
                  "action": ev.get("action"), "after": ev.get("after"),
                  "plans": [(p["source"], p["structureCheckResult"],
                             p["capabilityCheckResult"], p["constraintCheckResult"])
                            for p in ev.get("plans", [])],
                  "modelPhases": [r.get("phase") for r in ev.get("modelRequests", [])],
                  "restored": ev["fixtureModeRestored"], "cleanup": ev.get("cleanup")},
                 ensure_ascii=False))
