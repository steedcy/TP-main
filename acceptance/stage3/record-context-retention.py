"""Record persisted completed-task context snapshots as a separate rule."""
import csv
import json
from pathlib import Path

stage = Path(__file__).resolve().parent
runs = list((stage / "evidence").glob("TC-084-context-retention-*.json"))
assert len(runs) == 1
ev = json.loads(runs[0].read_text(encoding="utf-8"))
assert ev["taskId"] == 19 and ev["taskStatus"] == "COMPLETED"
assert len(ev["snapshots"]) == 2
assert all(s["taskId"] == 19 and s["snapshotCode"] and s["generatedAt"]
           and s["agents"] and s["capabilityCoverage"] for s in ev["snapshots"])
assert ev["events"] and ev["events"][0]["eventType"] == "CONTEXT_SNAPSHOT_GENERATED"
path = stage / "rules.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["ruleId"] == "SRS_F027.R05")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-084.S1",
           evidence="acceptance/stage3/evidence/" + runs[0].name)
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print("recorded SRS_F027.R05 P")
