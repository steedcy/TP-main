"""Read task 19 events after browser inspection; compare UI order and API records."""
import hashlib
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
ui = json.loads((stage / "evidence/SRS_F020-R07-timeline-task19.json").read_text(encoding="utf-8"))
events = operator("/tasks/19/events")
assert isinstance(events, list)
raw = json.dumps(events, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
rows = [{"id": row["id"], "occurredAt": row["occurredAt"],
         "eventType": row["eventType"], "detailSummary": row.get("detailSummary")}
        for row in events]
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "taskId": 19,
      "count": len(rows), "sha256": hashlib.sha256(raw).hexdigest(),
      "events": rows,
      "uiCount": len(ui["items"]),
      "uiTimestamps": [item.split(" - ", 1)[0] for item in ui["items"]],
      "uiTypes": [item.split(" - ", 1)[1].split("：", 1)[0].strip() for item in ui["items"]]}
out = stage / "evidence/SRS_F020-R07-timeline-api-task19.json"
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"count": ev["count"], "uiCount": ev["uiCount"],
                  "apiAscending": ev["events"] == sorted(ev["events"], key=lambda row: (row["occurredAt"], row["id"])),
                  "uiAscending": ev["uiTimestamps"] == sorted(ev["uiTimestamps"]),
                  "uiMatchesApi": [(e["occurredAt"], e["eventType"]) for e in ev["events"]] ==
                  list(zip(ev["uiTimestamps"], ev["uiTypes"]))}, ensure_ascii=False))
