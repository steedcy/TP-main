"""Record role-scoped trace reads and audited forbidden access."""
import csv
import json
from pathlib import Path

stage = Path(__file__).resolve().parent
runs = list((stage / "evidence").glob("TC-084-trace-permissions-*.json"))
assert len(runs) == 1
ev = json.loads(runs[0].read_text(encoding="utf-8"))
assert ev["authorized"] == {"systemAdminEventCount": 27, "operatorEventCount": 27}
assert not ev["configAdmin"]["accepted"] and "HTTP 403" in ev["configAdmin"]["error"]
assert len(ev["denialLogs"]) == 1
assert all(row["operationType"] == "ACCESS_DENIED"
           and row["operationTarget"] == "/api/v1/tasks/19/events"
           and row["operationResult"] == "FAILED"
           and row["username"] and row["sourceIp"] and row["createdAt"]
           for row in ev["denialLogs"])
path = stage / "rules.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["ruleId"] == "SRS_F027.R08")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-084.S2",
           evidence="acceptance/stage3/evidence/" + runs[0].name)
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print("recorded SRS_F027.R08 P")
