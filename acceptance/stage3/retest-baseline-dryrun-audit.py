"""Confirm stage-3 dry-run completion records in operation logs and task events."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db)
name = "S3_TC028_DISPLAY_DRYRUN"
logs = db.query(db.source,
    "SELECT operation_type,operation_target,operation_result FROM tip_stage2_v14.operation_logs "
    "WHERE operation_target LIKE 'S3_TC028_DISPLAY_DRYRUN%' ORDER BY id").splitlines()
events = db.query(db.source,
    "SELECT task_id,event_type FROM tip_stage2_v14.task_events "
    "WHERE task_id IN (25,26,27,28) AND event_type LIKE 'DRY_RUN_%' ORDER BY task_id,id").splitlines()
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "templateName": name, "operationRows": logs, "dryRunEventRows": events,
      "startOperationCount": sum(x.startswith("BASELINE_TEMPLATE_DRY_RUN|") for x in logs),
      "completionOperationCount": sum("DRY_RUN_RESULT" in x or "DRY_RUN_SUCCEEDED" in x for x in logs),
      "successEventCount": sum(x.endswith("|DRY_RUN_SUCCEEDED") for x in events)}
out = Path(__file__).resolve().parent / "evidence/TC-028-baseline-dryrun-audit.json"
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(ev, ensure_ascii=False))
