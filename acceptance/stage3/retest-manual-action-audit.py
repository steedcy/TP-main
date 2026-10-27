"""Create an isolated pending-manual baggage task and record MARK_FAILED audit."""
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
system = local.API("系统管理员")
marker = "S3_TC064_MARK_FAILED_20261027"
goal = ("请为虚构旅客P-" + marker + "的行李R-" + marker +
        "在F2_BAGGAGE_POINT测量，尺寸为55×40×20厘米、重量10千克。"
        "按附录F阈值：长宽高之和超过158厘米或重量超过32千克即为超规；"
        "该件为非超规样本，请如实测量判定，仅记录测量后结束，不触发超规事件、航显提示或机器人引导。"
        "全部是虚构测试对象。")
scene = {"baggageId": "R-" + marker, "baggageLocation": "F2_BAGGAGE_POINT",
         "length": 55, "width": 40, "height": 20, "weight": 10,
         "targetLocation": "F2_TEST_GATE", "routePreference": "BARRIER_FREE",
         "measureMode": "AUTO", "timeout": 30, "alertLevel": "WARNING",
         "contentType": "TEXT", "displayDuration": 60,
         "contentData": "虚构非超规行李，仅测量记录"}
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "goalMarker": marker, "clarifications": []}
out = stage / "evidence" / ("SRS_F028-manual-action-audit-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
task_id = None
action_done = False
try:
    task = operator("/tasks", "POST", {"taskGoal": goal,
                    "taskFamily": "OVERSIZE_BAGGAGE_HANDLING", "sceneParams": scene})
    task_id = task["id"]
    ev["created"] = {key: task.get(key) for key in ("id", "taskCode", "status", "taskGoal", "createdAt")}
    deadline = time.monotonic() + 150
    rounds = 0
    while time.monotonic() < deadline:
        questions = task.get("missingInfoQuestions") or []
        if task["status"] == "PLANNING" and questions and rounds < 3:
            answer = ("虚构旅客P-" + marker + "及行李R-" + marker +
                      "位于F2_BAGGAGE_POINT；尺寸55×40×20厘米，重量10千克。"
                      "本件如实判定为非超规，只测量记录后结束，自动测量无需人工复核。")
            ev["clarifications"].append({"round": rounds + 1, "questions": questions,
                                         "answer": answer})
            task = operator(f"/tasks/{task_id}/clarify", "POST",
                            {"answers": {question: answer for question in questions}})
            rounds += 1
            continue
        if task["status"] in {"COMPLETED", "FAILED", "PENDING_MANUAL", "MANUAL_TERMINATED"}:
            break
        time.sleep(2)
        task = operator(f"/tasks/{task_id}")
    ev["beforeAction"] = {key: task.get(key) for key in
                          ("id", "taskCode", "status", "failureReason", "missingInfoQuestions",
                           "currentPlanVersionId", "updatedAt")}
    if task["status"] == "PENDING_MANUAL":
        after = operator(f"/tasks/{task_id}/manual-actions", "POST", {"action": "MARK_FAILED"})
        action_done = True
        ev["afterAction"] = {key: after.get(key) for key in
                             ("id", "taskCode", "status", "failureReason", "updatedAt")}
    ev["events"] = [{key: row.get(key) for key in
                     ("id", "eventType", "occurredAt", "trigger", "reasonCode", "detailSummary")}
                    for row in operator(f"/tasks/{task_id}/events")]
    types = ("TASK_MANUAL_ACTION", "TASK_DEFINITION_UPDATE", "RISK_RULE_CHANGE")
    ev["audit"] = {}
    for kind in types:
        logs = system("/operation-logs?operationType=" + kind + "&page=1&size=100")["content"]
        selected = [row for row in logs if (row["operationTarget"] or "").startswith(task["taskCode"])] if kind == "TASK_MANUAL_ACTION" else logs[:2]
        ev["audit"][kind] = [{key: row.get(key) for key in
                              ("id", "username", "role", "operationType", "operationTarget",
                               "operationResult", "sourceIp", "createdAt", "detail")}
                             for row in selected]
finally:
    if task_id is not None:
        current = operator(f"/tasks/{task_id}")
        ev["finalStatus"] = current["status"]
        if not action_done and current["status"] in (
                "PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT", "DOWNGRADING",
                "EXECUTING", "PENDING_MANUAL"):
            ev["cleanup"] = operator(f"/tasks/{task_id}/terminate", "POST",
                                     {"reason": "阶段3隔离人工处置审计测试结束", "confirmed": True})
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "taskId": task_id,
                  "before": ev.get("beforeAction", {}).get("status"),
                  "after": ev.get("afterAction", {}).get("status"),
                  "manualAuditCount": len(ev.get("audit", {}).get("TASK_MANUAL_ACTION", [])),
                  "finalStatus": ev.get("finalStatus")}, ensure_ascii=False))
