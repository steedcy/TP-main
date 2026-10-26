"""TC-066.S2-S3: verify final release, frozen step, cancel command and logs."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
db_spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(db_spec)
db_spec.loader.exec_module(db)
operator = local.API("运行操作员")
config = local.API("配置管理员")
task = operator("/tasks/64")
assignments = operator("/tasks/64/step-assignments")
events = operator("/tasks/64/events")
agent = next(a for a in config("/device-agents?page=1&size=100")["content"]
             if a["deviceCode"] == "SIM_F2_DISPLAY")
lines = db.query(db.source,
    "SELECT id,command_id,command_type,command_status,attempt_no,"
    "coalesce(response_payload,'') FROM tip_stage2_v14.device_commands "
    "WHERE task_id=64 ORDER BY id").splitlines()
commands = []
for line in lines:
    cells = line.split("|", 5)
    assert len(cells) == 6
    commands.append(dict(zip(("id", "commandId", "commandType", "status",
                              "attemptNo", "responsePayload"), cells)))
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "taskId": 64,
      "task": {k: task.get(k) for k in (
          "id", "taskCode", "status", "manualTerminateReason", "updatedAt")},
      "assignments": assignments, "events": events,
      "agent": {k: agent.get(k) for k in (
          "agentId", "deviceCode", "agentStatus", "onlineStatus", "workStatus", "currentTaskId")},
      "commands": commands}
out = stage / "evidence" / ("TC-066-terminate-followup-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "taskStatus": task["status"],
                  "assignmentStatuses": [a["stepStatus"] for a in assignments],
                  "agentWorkStatus": agent["workStatus"],
                  "commands": [(c["commandType"], c["status"]) for c in commands]},
                 ensure_ascii=False))
