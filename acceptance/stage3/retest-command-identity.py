"""SRS_F007.R02: compare actual message IDs across distinct dispatched types."""
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

columns = query(
    "SELECT json_build_object('taskId',task_id,'agentCode',agent_code,"
    "'commandId',command_id,'commandType',command_type,'attemptNo',attempt_no,"
    "'status',command_status,'payloadCommandId',command_payload::jsonb->>'commandId',"
    "'payloadCommandType',command_payload::jsonb->>'commandType',"
    "'createdAt',created_at,'updatedAt',updated_at)::text "
    "FROM tip_stage2_v14.device_commands WHERE task_id IN (59,60) ORDER BY task_id,id")
commands = [json.loads(row) for row in columns]
assert len(commands) == 5
assert all(row["commandId"] == row["payloadCommandId"] and
           row["commandType"] == row["payloadCommandType"] for row in commands)
assert {row["commandType"] for row in commands if row["taskId"] == 60} == {
    "TASK_ACCEPT", "EXECUTE_CAPABILITY", "TASK_CANCEL"}
collisions = query(
    "SELECT command_id || '|' || count(*) || '|' || "
    "string_agg(DISTINCT command_type,',') "
    "FROM tip_stage2_v14.device_commands WHERE task_id BETWEEN 38 AND 60 "
    "GROUP BY command_id HAVING count(DISTINCT command_type)>1 ORDER BY count(*) DESC,command_id")
indexes = query(
    "SELECT indexname || '|' || indexdef FROM pg_indexes "
    "WHERE schemaname='tip_stage2_v14' AND tablename='device_commands' ORDER BY indexname")
timeline = query(
    "SELECT json_build_object('taskId',task_id,'eventType',event_type,"
    "'reasonCode',reason_code,'occurredAt',occurred_at)::text "
    "FROM tip_stage2_v14.task_events WHERE task_id IN (59,60) ORDER BY task_id,id")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "sourceTaskIds": [59, 60],
      "commands": commands, "multiTypeCommandIdsInTasks38To60": collisions,
      "databaseIndexes": indexes, "taskEvents": [json.loads(row) for row in timeline]}
assert all(len({row["commandId"] for row in commands if row["taskId"] == task_id}) == 1
           for task_id in [59, 60])
assert len(collisions) >= 2
out = stage / "evidence" / ("TC-023-command-identity-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "commandRows": len(commands),
                  "multiTypeIds": len(collisions),
                  "types59": [r["commandType"] for r in commands if r["taskId"] == 59],
                  "types60": [r["commandType"] for r in commands if r["taskId"] == 60]},
                 ensure_ascii=False))
