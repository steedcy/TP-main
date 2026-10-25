"""Record TC-017.S2 boundary validation and missing change-content audit."""
import csv
import json
from pathlib import Path

here = Path(__file__).resolve().parent
ev = json.loads((here / "evidence/TC-017-type-edit.json").read_text(encoding="utf-8"))
assert all(ev[key] == 400 for key in (
    "emptyCapabilitiesStatus", "description501Status", "scenarios1001Status", "constraints1001Status"))
assert ev["maxBoundariesAccepted"] and ev["zeroLengthsAccepted"] and ev["restoredOriginalFields"]
assert ev["updatedByPresent"] and ev["updatedAtPresent"]
assert ev["auditRecordDelta"] == 3 and ev["auditDetailRecordDelta"] == 0


def read(name):
    with (here / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(name, rows):
    with (here / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


file = "acceptance/stage3/evidence/TC-017-type-edit.json"
steps = read("steps.csv")
for row in steps:
    if row["stepId"] == "TC-017.S2":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", observedAt="2026-10-25", issue="DEF-S3-019",
                   actual="零支持及501/1001越界均400；500/1000边界与空文本保存成功且已恢复原值，修改人时间更新；三条变更审计无detail，缺修改内容",
                   evidence=file)
write("steps.csv", steps)

rules = read("rules.csv")
for row in rules:
    if row["ruleId"] == "SRS_F006A.R03":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", verifiedBy="TC-017.S2", evidence=file)
    elif row["ruleId"] == "SRS_F006A.R09":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", verifiedBy="TC-017.S2", issue="DEF-S3-019", evidence=file)
write("rules.csv", rules)

issues = read("issues.csv")
assert "DEF-S3-019" not in {row["编号"] for row in issues}
issues.append(dict(zip(issues[0].keys(), [
    "DEF-S3-019", "缺陷", "中", "TC-017.S2", "SRS_F006A.R09", "待修复",
    "设备类型边界修改已记录操作人和时间，但三条审计的detail均为空，无法追溯修改内容",
    file, "写入脱敏的前后支持能力及文本字段摘要；复测审计和边界有效性",
])))
write("issues.csv", issues)
