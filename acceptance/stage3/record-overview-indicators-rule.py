"""Classify the narrow five-indicator rule from independent Stage3 SQL."""
import csv
import json
from pathlib import Path

stage = Path(__file__).resolve().parent
name = "TC-004-overview-api.json"
ev = json.loads((stage / "evidence" / name).read_text(encoding="utf-8"))
independent = ev["independent"]
today = ev["apiMetrics"]["today"]
week = ev["apiMetrics"]["week"]
assert all(today[key] == independent[key] for key in (
    "agentTotal", "agentOnline", "taskInProgress", "unhandledExceptions"))
assert today["replanningCount"] == independent["todayReplanningCount"]
assert week["replanningCount"] == independent["weekReplanningCount"]
assert not ev["checks"]["availableStatusCountsMatch"]
path = stage / "rules.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["ruleId"] == "SRS_F002.R01")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-004.S1",
           evidence="acceptance/stage3/evidence/" + name)
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print("recorded SRS_F002.R01 P for five present indicators")
