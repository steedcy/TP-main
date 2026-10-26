"""Classify oversize baggage closure from original Stage3 task 19 events."""
import csv
import json
from pathlib import Path

stage = Path(__file__).resolve().parent
name = "TC-072-073-baggage-202230.json"
ev = json.loads((stage / "evidence" / name).read_text(encoding="utf-8"))
task = next(r for r in ev["results"] if r["task"]["id"] == 19)
assert task["task"]["status"] == "COMPLETED"
actions = {a["capability"]: a for a in task["actions"]}
assert all(actions[c]["status"] == "COMPLETED" for c in (
    "CAP_NAVIGATION", "CAP_BAGGAGE_MEASURE", "CAP_OVERSIZE_ALERT", "CAP_INFO_DISPLAY"))
assert actions["CAP_NAVIGATION"]["output"]["routeGenerated"]
assert actions["CAP_BAGGAGE_MEASURE"]["output"]["measureStatus"] == "SUCCESS"
assert actions["CAP_OVERSIZE_ALERT"]["output"]["reportStatus"] == "SUCCESS"
assert actions["CAP_INFO_DISPLAY"]["output"]["displayStatus"] == "SUCCESS"
assert sum(e["eventType"] == "STEP_COMPLETED" for e in task["events"]) == 4
assert task["events"][-1]["eventType"] == "TASK_COMPLETED"
path = stage / "rules.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["ruleId"] == "SRS_F024.R08")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-072.S3",
           evidence="acceptance/stage3/evidence/" + name)
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print("recorded SRS_F024.R08 P from task 19")
