"""SRS_F007.R04: inspect a real cancel command without claiming confirmation success."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db)

def query(sql):
    return db.query(db.source, sql).splitlines()

rows = query(
    "SELECT json_build_object('taskId',task_id,'agentCode',agent_code,"
    "'commandId',command_id,'commandType',command_type,'attemptNo',attempt_no,"
    "'payload',command_payload::jsonb,'status',command_status,'createdAt',created_at)::text "
    "FROM tip_stage2_v14.device_commands WHERE task_id=60 AND command_type='TASK_CANCEL'")
assert len(rows) == 1
cancel = json.loads(rows[0])
assert cancel["commandType"] == cancel["payload"]["commandType"] == "TASK_CANCEL"
assert cancel["payload"]["taskId"] == "TASK-20261026-0060"
assert cancel["payload"]["inputParams"] == {}
assert cancel["payload"]["capabilityType"] is None
event_types = query(
    "SELECT event_type FROM tip_stage2_v14.task_events WHERE task_id=60 ORDER BY id")
assert "TASK_CANCEL_REQUESTED" in event_types
task = query("SELECT status FROM tip_stage2_v14.tasks WHERE id=60")
assert len(task) == 1
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "taskId": 60, "cancelCommand": cancel,
      "taskStatus": task[0], "taskEventTypes": event_types,
      "interpretationScope": "business cancel message shape; confirmation timed out"}
out = stage / "evidence" / ("TC-023-cancel-semantics-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "taskStatus": task[0],
                  "cancelStatus": cancel["status"], "cancelEvent": "TASK_CANCEL_REQUESTED"},
                 ensure_ascii=False))
