"""Capture isolated device command fields for manual-action follow-up."""
import importlib.util
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db)
rows = db.query(db.source,
    "SELECT task_id,step_seq,capability_type,command_payload,command_status,response_payload "
    "FROM tip_stage2_v14.device_commands WHERE task_id IN (69,70,71) ORDER BY task_id,id")
out = Path(__file__).resolve().parent / "evidence" / (
    "TC-064-manual-device-commands-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".txt")
out.write_text(rows + "\n", encoding="utf-8")
print("evidence=" + str(out) + " rows=" + str(len(rows.splitlines())))
