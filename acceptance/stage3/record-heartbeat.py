"""Record TC-014.S2 partial UI gap and exact heartbeat subrules."""
import csv
import json
from pathlib import Path

here = Path(__file__).resolve().parent
ev = json.loads((here / "evidence/TC-014-heartbeat.json").read_text(encoding="utf-8"))
assert ev["beforeOnlineStatus"] == "ONLINE"
assert ev["offlineElapsedSeconds"] >= 30 and ev["offlineStatus"] == "OFFLINE"
assert ev["offlineEventDelta"] == 1 and ev["excludedFromOnlineFilter"]
assert ev["recoveredStatus"] == "ONLINE" and ev["recoveryEventDelta"] == 1
assert ev["offlineLastReportedAt"] == ev["beforeLastReportedAt"]


def read(name):
    with (here / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(name, rows):
    with (here / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


file = "acceptance/stage3/evidence/TC-014-heartbeat.json"
steps = read("steps.csv")
for row in steps:
    if row["stepId"] == "TC-014.S2":
        assert row["status"] == "NOT_RUN"
        row.update(status="NT", observedAt="2026-10-25", issue="NT-S3-010",
                   actual="停止SIM_F2_DISPLAY心跳36.5秒后离线、退出在线候选且产生1条离线事件；恢复即在线并产生1条恢复事件。未核对页面高亮、任务影响说明及新任务分配保护",
                   evidence=file)
write("steps.csv", steps)

rules = read("rules.csv")
for row in rules:
    if row["ruleId"] in {"SRS_F005.R02", "SRS_F005.R07"}:
        assert row["status"] == "NOT_RUN"
        row.update(status="P", verifiedBy="TC-014.S2", evidence=file)
write("rules.csv", rules)

issues = read("issues.csv")
assert "NT-S3-010" not in {row["编号"] for row in issues}
issues.append(dict(zip(issues[0].keys(), [
    "NT-S3-010", "前置缺口", "待定", "TC-014.S2", "SRS_F005.R04", "待补分支",
    "心跳暂停离线与恢复及候选过滤已实测；页面高亮、离线任务影响说明和新任务分配拒绝尚未执行",
    file, "准备离线占用任务与浏览器观察，复测离线提示及分配保护",
])))
write("issues.csv", issues)
