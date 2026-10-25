"""Record device re-enable failing to re-enable its existing agent."""
import csv
import json
from pathlib import Path

here = Path(__file__).resolve().parent
ev = json.loads((here / "evidence/TC-012-status-sync.json").read_text(encoding="utf-8"))
assert ev["afterDisableDeviceStatus"] == "INACTIVE"
assert ev["afterDisableAgentStatus"] == "DISABLED" and ev["afterDisableOnlineStatus"] == "OFFLINE"
assert ev["afterEnableDeviceStatus"] == "ACTIVE"
assert ev["afterEnableAgentStatus"] == "DISABLED" and ev["afterEnableOnlineStatus"] == "OFFLINE"
assert ev["restoredDeviceStatus"] == "ACTIVE"
assert ev["restoredAgentStatus"] == "ENABLED" and ev["restoredOnlineStatus"] == "ONLINE"

path = here / "steps.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    rows = list(csv.DictReader(stream))
for row in rows:
    if row["stepId"] == "TC-012.S2":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", observedAt="2026-10-25", issue="DEF-S3-021",
                   actual="停用空闲设备时代理同步DISABLED/OFFLINE；重新启用设备后代理仍DISABLED/OFFLINE，未同步启用。已通过创建启用代理操作恢复原ONLINE状态；删除归档分支未执行",
                   evidence="acceptance/stage3/evidence/TC-012-status-sync.json")
with path.open("w", encoding="utf-8-sig", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

path = here / "issues.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    issues = list(csv.DictReader(stream))
assert "DEF-S3-021" not in {row["编号"] for row in issues}
issues.append(dict(zip(issues[0].keys(), [
    "DEF-S3-021", "缺陷", "高", "TC-012.S2", "SRS_F004", "待修复",
    "设备停用时代理同步停用；重新启用设备后代理仍DISABLED/OFFLINE，未恢复可用候选",
    "acceptance/stage3/evidence/TC-012-status-sync.json",
    "设备重新启用时按连接测试条件同步启用原代理并恢复绑定；复测删除归档和在线候选",
])))
with path.open("w", encoding="utf-8-sig", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=issues[0].keys())
    writer.writeheader()
    writer.writerows(issues)
