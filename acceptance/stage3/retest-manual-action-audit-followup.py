"""Read task 20's terminal event and the three required audit operation types."""
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
system = local.API("系统管理员")
task = operator("/tasks/20")
events = operator("/tasks/20/events")
assert task["status"] == "FAILED"
types = ("TASK_MANUAL_ACTION", "TASK_DEFINITION_UPDATE", "RISK_RULE_CHANGE")
logs = {}
for kind in types:
    response = system("/operation-logs?operationType=" + kind + "&page=1&size=100")
    selected = [row for row in response["content"] if
                task["taskCode"] in (row.get("operationTarget") or "")] if kind == "TASK_MANUAL_ACTION" else response["content"][:3]
    logs[kind] = [{key: row.get(key) for key in
                   ("id", "username", "role", "operationType", "operationTarget",
                    "operationResult", "sourceIp", "createdAt", "detail")}
                  for row in selected]
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "taskId": 20,
      "task": {key: task.get(key) for key in
               ("id", "taskCode", "status", "failureReason", "updatedAt")},
      "events": [{key: row.get(key) for key in
                  ("id", "eventType", "occurredAt", "trigger", "reasonCode", "detailSummary")}
                 for row in events], "audit": logs,
      "controlTask68Status": operator("/tasks/68")["status"]}
out = stage / "evidence" / ("SRS_F028-manual-action-followup-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "taskStatus": task["status"],
                  "taskFailedEvents": sum(row["eventType"] == "TASK_FAILED" for row in events),
                  "auditCounts": {kind: len(rows) for kind, rows in logs.items()},
                  "controlTask68Status": ev["controlTask68Status"]}, ensure_ascii=False))
