"""SRS_F007.R06: inspect three real Stage 3 simulator feedback categories."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db)

rows = db.query(db.source,
    "SELECT json_build_object('taskId',task_id,'commandId',command_id,"
    "'commandStatus',command_status,'response',response_payload::jsonb)::text "
    "FROM tip_stage2_v14.device_commands "
    "WHERE task_id IN (30,31,59) AND command_type='EXECUTE_CAPABILITY' ORDER BY task_id").splitlines()
commands = [json.loads(row) for row in rows]
assert [row["taskId"] for row in commands] == [30, 31, 59]
assert [row["response"]["executionResult"] for row in commands] == ["FAILED", "TIMEOUT", "SUCCESS"]
events = db.query(db.source,
    "SELECT json_build_object('taskId',task_id,'eventType',event_type,"
    "'reasonCode',reason_code,'occurredAt',occurred_at)::text "
    "FROM tip_stage2_v14.task_events WHERE task_id IN (30,31,59) "
    "AND event_type='EXECUTION_FEEDBACK_RECEIVED' ORDER BY task_id").splitlines()
event_rows = [json.loads(row) for row in events]
assert [row["taskId"] for row in event_rows] == [30, 31, 59]
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "stage3TaskIds": [30, 31, 59],
      "commandFeedback": commands, "feedbackEvents": event_rows,
      "sourceEvidence": ["TC-029-baseline-dryrun-failures.json",
                         "TC-014-offline-assignment-alt-20261026T075511Z.json"]}
out = stage / "evidence" / ("TC-023-feedback-reason-codes-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "mapped": [
    {"result": row["response"]["executionResult"],
     "status": row["commandStatus"], "reasonCode": row["response"].get("reasonCode")}
    for row in commands]}, ensure_ascii=False))
