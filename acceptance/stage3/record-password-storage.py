"""Record fresh two-account salted password storage probe."""
import csv
import json
from pathlib import Path

stage = Path(__file__).resolve().parent
runs = list((stage / "evidence").glob("TC-001-password-storage-*.json"))
assert len(runs) == 1
ev = json.loads(runs[0].read_text(encoding="utf-8"))
checks = ev["hashChecks"]
assert checks["rowCount"] == 2 and checks["allBcryptFormat"]
assert checks["samePasswordDifferentHashes"] and checks["plaintextAbsentFromHashRows"]
assert len(ev["loginChecks"]) == 2 and all(row["accepted"] for row in ev["loginChecks"])
assert ev["auditChecks"]["loginAndLogoutPresent"] and ev["auditChecks"]["plaintextAbsent"]
assert list(ev["cleanup"].values()) == ["INACTIVE", "INACTIVE"]
path = stage / "rules.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["ruleId"] == "SRS_F001.R01")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-001.S3",
           evidence="acceptance/stage3/evidence/" + runs[0].name)
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print("recorded SRS_F001.R01 P")
