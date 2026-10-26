"""Classify TC-014.S1 from the two fresh signed reports and UI/DB samples."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
evidence = stage / "evidence"
runs = list(evidence.glob("TC-014-status-report-20261026T072608Z.json"))
assert len(runs) == 1
run = json.loads(runs[0].read_text(encoding="utf-8"))
a, b = (run["phases"][phase] for phase in ("A", "B"))
au, bu = (json.loads((evidence / f"TC-014-status-{phase}-ui.json").read_text(encoding="utf-8"))
          for phase in ("A", "B"))
assert run["reportIntervalDuring"] == 15 and b["elapsedSinceASeconds"] >= 15
assert all(p["response"]["code"] == 200 and p["browser"]["exitCode"] == 0
           for p in (a, b))
assert (a["after"]["agent"]["workStatus"], b["after"]["agent"]["workStatus"]) == ("BUSY", "IDLE")
assert (a["after"]["situation"]["location"]["zone"],
        b["after"]["situation"]["location"]["zone"]) == ("F2_TEST", "F2_TEST")
assert "F2_ZONE_A" in json.dumps(a["request"]) and "F2_ZONE_B" in json.dumps(b["request"])
assert '"testState": "PHASE_A"' in a["after"]["db"]
assert '"testState": "PHASE_B"' in b["after"]["db"]
assert '"testState": "PHASE_A"' not in b["after"]["db"]
assert a["after"]["deviceEventCount"] == b["after"]["deviceEventCount"] == run["before"]["deviceEventCount"]
assert "marker-busy" in au["markerClass"] and "marker-online" in bu["markerClass"]
assert "F2_TEST" in au["tableRow"] and "F2_TEST" in bu["tableRow"]
assert "900, 4300" in au["tableRow"] and "820, 4250" in bu["tableRow"]
assert run["restore"]["allSixOnlineIdle"]
assert run["restore"]["after"]["device"]["statusReportInterval"] == run["reportIntervalBefore"] == 5
assert run["restore"]["after"]["device"]["positionX"] == run["before"]["device"]["positionX"]
refs = ";".join("acceptance/stage3/evidence/" + name for name in [
    runs[0].name, "TC-014-status-A-ui.json", "TC-014-status-B-ui.json",
    "TC-014-status-A.png", "TC-014-status-B.png"])
date = datetime.now().astimezone().date().isoformat()

path = stage / "steps.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(row for row in rows if row["stepId"] == "TC-014.S1")
assert row["status"] == "NOT_RUN"
row.update(status="F", observedAt=date, issue="DEF-S3-046",
    actual="签名STATUS两次相隔15秒，代理/态势工作状态BUSY→IDLE、坐标900/4300→820/4250且地图橙→绿；数据库必要业务状态仅保留B，设备事件数不增。请求区域F2_ZONE_A/B均被忽略，设备、态势和界面始终F2_TEST；两次为人工定时发送，仿真器自动15秒上报周期另测",
    evidence=refs)
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

path = stage / "rules.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(row for row in rows if row["ruleId"] == "SRS_F005.R03")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-014.S1", evidence=refs)
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

path = stage / "issues.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    assert "DEF-S3-046" not in {row["编号"] for row in csv.DictReader(stream)}
with path.open("a", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["DEF-S3-046", "缺陷", "中", "TC-014.S1", "", "待修复",
        "STATUS上报location.zone从F2_ZONE_A改为F2_ZONE_B，后端两次均只更新坐标，不更新设备区域；态势快照与Chrome表格区域始终F2_TEST",
        refs, "将合法上报区域同步到当前设备位置/态势，复测双区域切换、地图和代理数据，并验证区域边界"])
print("recorded TC-014.S1 F, SRS_F005.R03 P and DEF-S3-046; R01 awaits automatic cadence")
