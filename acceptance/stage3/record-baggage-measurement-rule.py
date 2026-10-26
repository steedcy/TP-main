"""Classify F024.R02 from the completed simulated measurement action."""
import csv
import json
from pathlib import Path

stage = Path(__file__).resolve().parent
name = "TC-072-073-baggage-202230.json"
ev = json.loads((stage / "evidence" / name).read_text(encoding="utf-8"))
task = next(r for r in ev["results"] if r["task"]["id"] == 19)
measure = next(a for a in task["actions"] if a["capability"] == "CAP_BAGGAGE_MEASURE")
output = measure["output"]
assert measure["status"] == "COMPLETED" and output["measureStatus"] == "SUCCESS"
assert all(isinstance(output[key], (int, float)) and output[key] > 0
           for key in ("length", "width", "height", "weight"))
assert output["isOversize"] is True
path = stage / "rules.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["ruleId"] == "SRS_F024.R02")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-072.S3",
           evidence="acceptance/stage3/evidence/" + name)
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print("recorded SRS_F024.R02 P")
