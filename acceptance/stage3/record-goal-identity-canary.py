"""Record TC-031.S2 privacy failure from a fresh synthetic canary task."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
name = "TC-031-identity-canary-20261026T035059Z.json"
ev = json.loads((stage / "evidence" / name).read_text(encoding="utf-8"))
assert ev["schema"] == "tip_stage2_v14"
assert ev["afterMaxTaskId"] == ev["beforeMaxTaskId"] + 1 == 46
assert ev["submitError"] is None and ev["task"]["status"] == "COMPLETED"
assert ev["task"]["taskGoal"] == ev["request"]["taskGoal"]
assert ev["task"]["goalParsingResult"]["originalGoal"] == ev["request"]["taskGoal"]
assert ev["contexts"] and ev["planVersions"] and ev["events"]
for key, marker in ev["canaries"].items():
    assert marker not in ev["request"]["taskGoal"]
    assert ev["submit"]["sceneParams"][key] == marker
    assert ev["task"]["sceneParams"][key] == marker
ref = "acceptance/stage3/evidence/" + name
day = datetime.now().astimezone().date().isoformat()

def update(name, key, changes):
    path = stage / name
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    for row in rows:
        if row[key] in changes:
            assert row["status"] == "NOT_RUN", row[key]
            row.update(changes[row[key]])
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

update("steps.csv", "stepId", {"TC-031.S2": {
    "status": "F", "observedAt": day,
    "actual": "任务46原目标和解析字段保留且完整进入规划；API额外提交纯虚构passengerName/identityDocumentNumber后，响应及任务详情sceneParams原样保存两字段，违反只存必要协助信息；未用真实身份数据",
    "evidence": ref, "issue": "DEF-S3-032"}})
update("rules.csv", "ruleId", {
    "SRS_F024.R09": {"status": "F", "verifiedBy": "TC-031.S2", "evidence": ref,
                     "issue": "DEF-S3-032"},
    "SRS_NF003.R01": {"status": "F", "verifiedBy": "TC-031.S2", "evidence": ref,
                       "issue": "DEF-S3-032"},
})
issues = stage / "issues.csv"
with issues.open(encoding="utf-8-sig", newline="") as stream:
    assert "DEF-S3-032" not in {row["编号"] for row in csv.DictReader(stream)}
with issues.open("a", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["DEF-S3-032", "缺陷", "高", "TC-031.S2", "SRS_F024.R09;SRS_NF003.R01", "待修复",
                     "运行操作员向超规行李任务sceneParams提交passengerName和identityDocumentNumber纯虚构哨兵字段；任务46创建并完成，提交响应和任务详情均原样持久化两个非必要身份字段",
                     ref,
                     "阶段4按任务族对sceneParams实行字段白名单并拒绝身份字段，清理模型请求与任务持久化的非必要字段；补测特殊旅客和追溯路径"])
print("recorded TC-031.S2, two rules and DEF-S3-032")
