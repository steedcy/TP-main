"""Record rejected device reports without the required format exception event."""
import csv
import json
from pathlib import Path

here = Path(__file__).resolve().parent
ev = json.loads((here / "evidence/TC-015-invalid-report.json").read_text(encoding="utf-8"))
assert ev["invalidFormatHttpStatus"] == 400 and ev["invalidIdentityHttpStatus"] == 401
assert ev["deviceEventDelta"] == 0
assert ev["onlineStatusUnchanged"] and ev["workStatusUnchanged"] and ev["positionUnchanged"]


def update(name, key, ident, fields):
    path = here / name
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        if row[key] == ident:
            assert row["status"] == "NOT_RUN"
            row.update(fields)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


file = "acceptance/stage3/evidence/TC-015-invalid-report.json"
update("steps.csv", "stepId", "TC-015.S1", {
    "status": "F", "observedAt": "2026-10-25", "issue": "DEF-S3-016",
    "actual": "非法状态字段上报400、错误设备令牌401，代理在线/工作状态及位置均未被覆盖；两次请求后设备事件增量0，未记录格式异常事件",
    "evidence": file,
})
update("rules.csv", "ruleId", "SRS_F005.R08", {
    "status": "F", "verifiedBy": "TC-015.S1", "issue": "DEF-S3-016", "evidence": file,
})
path = here / "issues.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    issues = list(csv.DictReader(stream))
assert "DEF-S3-016" not in {row["编号"] for row in issues}
issues.append(dict(zip(issues[0].keys(), [
    "DEF-S3-016", "缺陷", "中", "TC-015.S1", "SRS_F005.R08", "待修复",
    "设备非法状态上报400、错误身份401且状态未覆盖，但未写任何格式异常设备事件",
    file, "对非法上报和身份拒绝记录脱敏异常事件并保持状态不变；复测事件数量和原因码",
])))
with path.open("w", encoding="utf-8-sig", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=issues[0].keys())
    writer.writeheader()
    writer.writerows(issues)
