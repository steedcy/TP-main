"""TC-064.S2: isolated pending-manual tasks for switch and retry branches."""
import importlib.util
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
operator = local.API("运行操作员")
admin = local.API("系统管理员")
action = sys.argv[1] if len(sys.argv) > 1 else "SWITCH_TO_BASELINE"
assert action in {"SWITCH_TO_BASELINE", "RETRY_PLANNING"}
marker = "S3_TC064_" + action + "_20261027"
goal = "请协助一名虚构旅客完成机场特殊旅客服务，服务类型及起终点尚待确认。" + marker
answer = "虚构测试资料未确认，暂不能给出该字段"
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "goalMarker": marker,
      "requestedAction": action, "clarifications": []}
out = stage / "evidence" / ("TC-064-" + action.lower().replace("_", "-") + "-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
task_id = None
try:
    task = operator("/tasks", "POST", {"taskGoal": goal,
                    "taskFamily": "SPECIAL_PASSENGER_SERVICE"})
    task_id = task["id"]
    ev["created"] = {k: task.get(k) for k in ("id", "taskCode", "status", "taskGoal", "createdAt")}
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        questions = task.get("missingInfoQuestions") or []
        if task["status"] == "PLANNING" and questions and len(ev["clarifications"]) < 3:
            payload = {question: answer for question in questions}
            task = operator(f"/tasks/{task_id}/clarify", "POST", {"answers": payload})
            ev["clarifications"].append({"round": len(ev["clarifications"]) + 1,
                                         "questions": questions, "answers": payload,
                                         "returnedStatus": task["status"]})
            continue
        if task["status"] not in {"PLANNING", "SUPERVISING", "DOWNGRADING", "PENDING_ASSIGNMENT"}:
            break
        time.sleep(1)
        task = operator(f"/tasks/{task_id}")
    ev["before"] = {k: task.get(k) for k in
                    ("id", "taskCode", "status", "failureReason", "currentPlanVersionId",
                     "missingInfoQuestions")}
    if task["status"] == "PENDING_MANUAL":
        try:
            result = operator(f"/tasks/{task_id}/manual-actions", "POST",
                              {"action": action})
            ev["action"] = {"accepted": True, "returned": {k: result.get(k) for k in
                            ("status", "failureReason", "currentPlanVersionId")}}
        except RuntimeError as error:
            ev["action"] = {"accepted": False, "error": str(error)}
        time.sleep(3)
        after = operator(f"/tasks/{task_id}")
        ev["after"] = {k: after.get(k) for k in
                       ("id", "taskCode", "status", "failureReason", "currentPlanVersionId",
                        "missingInfoQuestions")}
    ev["planVersions"] = operator(f"/tasks/{task_id}/plan-versions")
    ev["events"] = operator(f"/tasks/{task_id}/events")
    logs = admin("/operation-logs?operationType=TASK_MANUAL_ACTION&page=1&size=100")["content"]
    ev["manualAudit"] = [row for row in logs if task["taskCode"] in (row.get("operationTarget") or "")]
finally:
    if task_id is not None:
        current = operator(f"/tasks/{task_id}")
        ev["finalStatusBeforeCleanup"] = current["status"]
        if current["status"] in {"PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT",
                                 "DOWNGRADING", "EXECUTING", "PENDING_MANUAL"}:
            try:
                ev["cleanup"] = operator(f"/tasks/{task_id}/terminate", "POST",
                                         {"reason": "阶段3隔离人工处置试验已记录",
                                          "confirmed": True})["status"]
            except RuntimeError as error:
                ev["cleanupError"] = str(error)
        out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "taskId": task_id,
                  "before": ev.get("before", {}).get("status"),
                  "action": ev.get("action"), "after": ev.get("after", {}).get("status"),
                  "plans": len(ev.get("planVersions", [])), "audit": len(ev.get("manualAudit", [])),
                  "cleanup": ev.get("cleanup")}, ensure_ascii=False))
