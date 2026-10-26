"""TC-066.S2: verify no late feedback reopens the terminated two-step task."""
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
task = operator("/tasks/65")
assignments = operator("/tasks/65/step-assignments")
events = operator("/tasks/65/events")
agent = next(a for a in config("/device-agents?page=1&size=100")["content"]
             if a["deviceCode"] == "SIM_F2_DISPLAY")
lines = db.query(db.source,
    "SELECT id,command_type,command_status,step_seq FROM tip_stage2_v14.device_commands "
    "WHERE task_id=65 ORDER BY id").splitlines()
commands = [dict(zip(("id", "type", "status", "stepSeq"), line.split("|")))
            for line in lines]
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "taskId": 65,
      "status": task["status"], "assignments": assignments,
      "eventTypes": [e["eventType"] for e in events],
      "commands": commands,
      "agent": {k: agent.get(k) for k in (
          "agentStatus", "onlineStatus", "workStatus", "currentTaskId")}}
out = stage / "evidence" / ("TC-066-terminate-prefix-followup-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "status": ev["status"],
                  "assignments": [(a["stepSeq"], a["stepStatus"])
                                  for a in assignments],
                  "commands": [(c["type"], c["status"]) for c in commands],
                  "agent": ev["agent"]}, ensure_ascii=False))
