"""Cross-check original Stage3 HTTP, audit, and menu evidence for F001.R05."""
import csv
import json
from pathlib import Path

stage = Path(__file__).resolve().parent
files = ["TC-003-valid-denials.json", "TC-003-audit-scope.json", "TC-003-role-menus.json"]
denials, audit, menus = [json.loads((stage / "evidence" / name).read_text(encoding="utf-8"))
                         for name in files]
assert denials["pass"] and len(denials["checks"]) == 7
assert all(row["httpStatus"] == 403 for row in denials["checks"])
assert audit["pass"] and audit["scope"]
assert all("ACCESS_DENIED" in role["eventTypes"]
           for role in audit["scope"].values())
assert menus["pass"] and len(menus["roles"]) == 3
assert all(role["forbiddenHidden"] for role in menus["roles"])
path = stage / "rules.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["ruleId"] == "SRS_F001.R05")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-003.S1;TC-003.S2;TC-003.S3",
           evidence=";".join("acceptance/stage3/evidence/" + name for name in files))
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print("recorded SRS_F001.R05 P from original Stage3 probes")
