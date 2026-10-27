"""Read-only follow-up for the three independent TC-064.S2 action tasks."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
operator = local.API("运行操作员")
admin = local.API("系统管理员")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "tasks": {}}
for task_id in (35, 69, 70):
    task = operator(f"/tasks/{task_id}")
    events = operator(f"/tasks/{task_id}/events")
    plans = operator(f"/tasks/{task_id}/plan-versions")
    ev["tasks"][str(task_id)] = {
        "task": {key: task.get(key) for key in
                 ("id", "taskCode", "taskGoal", "status", "failureReason",
                  "manualTerminateReason", "replanUsed", "replanningReason",
                  "currentPlanVersionId", "updatedAt")},
        "plans": [{key: plan.get(key) for key in
                   ("id", "versionNo", "source", "structureCheckResult",
                    "capabilityCheckResult", "constraintCheckResult", "riskLevel",
                    "riskReasonCode", "frozenAt", "validationErrors", "planSteps")}
                  for plan in plans],
        "events": [{key: event.get(key) for key in
                    ("id", "eventType", "occurredAt", "trigger", "reasonCode", "detailSummary")}
                   for event in events]}
logs = admin("/operation-logs?operationType=TASK_MANUAL_ACTION&page=1&size=100")["content"]
ev["manualAudit"] = [log for log in logs if any(
    ev["tasks"][str(i)]["task"]["taskCode"] in (log.get("operationTarget") or "")
    for i in (69, 70))]
logs = admin("/operation-logs?operationType=TASK_TERMINATE&page=1&size=100")["content"]
ev["terminateAudit"] = [log for log in logs if
                        ev["tasks"]["35"]["task"]["taskCode"] in (log.get("operationTarget") or "")]
agents = admin("/device-agents?page=1&size=100")["content"]
ev["simulatorAgents"] = [{key: agent.get(key) for key in
                           ("deviceCode", "agentStatus", "onlineStatus", "workStatus", "currentTaskId")}
                          for agent in agents if agent["deviceCode"].startswith("SIM_F2_")]
out = stage / "evidence" / ("TC-064-manual-branches-followup-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out),
                  "statuses": {id: row["task"]["status"] for id, row in ev["tasks"].items()},
                  "auditCounts": {"manual": len(ev["manualAudit"]), "terminate": len(ev["terminateAudit"])},
                  "allSixOnlineIdle": len(ev["simulatorAgents"]) == 6 and all(
                      a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE"
                      and a["workStatus"] == "IDLE" and a["currentTaskId"] is None
                      for a in ev["simulatorAgents"])}, ensure_ascii=False))
