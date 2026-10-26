"""Record the independently observed simulator cadence without changing S1's failure."""
import csv
import json
from pathlib import Path

stage = Path(__file__).resolve().parent
run = json.loads((stage / "evidence/TC-014-status-cadence-20261026T073137Z.json").read_text(encoding="utf-8"))
db = json.loads((stage / "evidence/TC-014-status-cadence-db.json").read_text(encoding="utf-8"))
assert run["createdDevice"]["statusReportInterval"] == run["configuredIntervalSeconds"] == 15
assert run["connectionTest"]["result"] == "PASSED" and run["binding"]["status"] == "BOUND"
assert len(run["reports"]) == 2 and 14.0 <= run["reportIntervalObservedSeconds"] <= 16.0
assert all(r["onlineStatus"] == "ONLINE" and r["workStatus"] == "IDLE" for r in run["reports"])
assert all(r["device"]["positionX"] == 835 and r["device"]["positionY"] == 4240 for r in run["reports"])
assert db["afterSoftDeleteDatabaseRow"]["businessStatus"] == {
    "scenarioResult": "SUCCESS", "simulatedDeviceType": "SMART_DISPLAY"}
assert db["afterSoftDeleteDatabaseRow"]["lastReportedAt"] == run["reports"][1]["lastReportedAt"]
assert run["cleanup"]["deviceStatus"] == "DELETED"
assert "simulatorExitCode" in run["cleanup"]
refs = ";".join("acceptance/stage3/evidence/" + name for name in [
    "TC-014-status-cadence-20261026T073137Z.json", "TC-014-status-cadence-db.json"])

path = stage / "rules.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(row for row in rows if row["ruleId"] == "SRS_F005.R01")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-014.S1", evidence=refs)
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

path = stage / "steps.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(row for row in rows if row["stepId"] == "TC-014.S1")
assert row["status"] == "F" and row["issue"] == "DEF-S3-046"
row["actual"] += "。独立临时仿真体自动两次上报实测间隔15.033秒，在线/空闲/坐标与必要业务状态在隔离库可见；临时对象已清理"
row["evidence"] += ";" + refs
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print("recorded SRS_F005.R01 P; TC-014.S1 remains F")
