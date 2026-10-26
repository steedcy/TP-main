"""Record the independently exercised login/logout audit rule."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
runs = list((stage / "evidence").glob("TC-001-session-audit-*.json"))
assert len(runs) == 1
ev = json.loads(runs[0].read_text(encoding="utf-8"))
assert not ev["failedLogin"]["unexpectedSuccess"]
assert ev["successfulLogin"]["sessionCreated"]
assert ev["cleanup"]["userStatus"] == "INACTIVE"
assert not ev["containsCredential"]
rows = ev["auditRows"]
assert {(r["operationType"], r["operationResult"]) for r in rows} == {
    ("LOGIN", "FAILED"), ("LOGIN", "SUCCESS"), ("LOGOUT", "SUCCESS")}
assert all(r["username"] == ev["username"] and r["createdAt"] and r["sourceIp"]
           and r["operationResult"] for r in rows)
ref = "acceptance/stage3/evidence/" + runs[0].name
path = stage / "rules.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rules = reader.fieldnames, list(reader)
row = next(r for r in rules if r["ruleId"] == "SRS_F001.R06")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-001.S3", evidence=ref)
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rules)
print(f"recorded SRS_F001.R06 P at {datetime.now().astimezone().isoformat()}")
