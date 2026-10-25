"""Record missing runtime heartbeat-threshold configuration control."""
import csv
import json
from pathlib import Path

here = Path(__file__).resolve().parent
ev = json.loads((here / "evidence/TC-014-heartbeat-threshold.json").read_text(encoding="utf-8"))
assert ev["menuHeartbeatControlCount"] == ev["deviceListHeartbeatControlCount"] == ev["deviceFormHeartbeatControlCount"] == 0
assert ev["reportingIntervalControlCount"] == 1

path = here / "steps.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    rows = list(csv.DictReader(stream))
for row in rows:
    if row["stepId"] == "TC-014.S3":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", observedAt="2026-10-25", issue="DEF-S3-015",
                   actual="配置管理员菜单、设备列表和新增设备表单均无心跳超时阈值配置，仅有5～60秒状态上报周期；无法设置10/120秒及验证超界拒绝和新阈值生效",
                   evidence="acceptance/stage3/evidence/TC-014-heartbeat-threshold.json;acceptance/stage3/evidence/TC-014-heartbeat-threshold-ui.png")
with path.open("w", encoding="utf-8-sig", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

path = here / "issues.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    issues = list(csv.DictReader(stream))
assert "DEF-S3-015" not in {row["编号"] for row in issues}
issues.append(dict(zip(issues[0].keys(), [
    "DEF-S3-015", "缺陷", "中", "TC-014.S3", "SRS_F005", "待修复",
    "配置管理员运行界面没有心跳超时阈值设置；仅有状态上报周期，无法执行10～120秒阈值边界与生效验证",
    "acceptance/stage3/evidence/TC-014-heartbeat-threshold.json;acceptance/stage3/evidence/TC-014-heartbeat-threshold-ui.png",
    "提供可验证的心跳超时阈值配置和10～120秒校验，再按新阈值重测离线",
])))
with path.open("w", encoding="utf-8-sig", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=issues[0].keys())
    writer.writeheader()
    writer.writerows(issues)
