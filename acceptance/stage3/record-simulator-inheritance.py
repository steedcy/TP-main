"""Record missing CAP_SIM_STATUS in six live simulator instance profiles."""
import csv
import json
from pathlib import Path

here = Path(__file__).resolve().parent
ev = json.loads((here / "evidence/TC-017-simulator-inheritance.json").read_text(encoding="utf-8"))
assert ev["sampleCount"] == len(ev["samples"]) == 6
assert all(row["missingInheritedCapabilityTypes"] == ["CAP_SIM_STATUS"] for row in ev["samples"])


def read(name):
    with (here / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(name, rows):
    with (here / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


file = "acceptance/stage3/evidence/TC-017-simulator-inheritance.json"
steps = read("steps.csv")
for row in steps:
    if row["stepId"] == "TC-017.S3":
        assert row["status"] == "F" and row["issue"] == "DEF-S3-018"
        row["issue"] += ";DEF-S3-020"
        row["actual"] = row["actual"].replace("仿真体继承分支待补", "六个仿真体实例都继承了业务能力但缺CAP_SIM_STATUS")
        row["evidence"] += ";" + file
write("steps.csv", steps)

rules = read("rules.csv")
for row in rules:
    if row["ruleId"] == "SRS_F006A.R04":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", verifiedBy="TC-017.S3", issue="DEF-S3-020", evidence=file)
write("rules.csv", rules)

issues = read("issues.csv")
assert "DEF-S3-020" not in {row["编号"] for row in issues}
issues.append(dict(zip(issues[0].keys(), [
    "DEF-S3-020", "缺陷", "中", "TC-017.S3", "SRS_F006A.R04", "待修复",
    "六个在线仿真体实例继承了所模拟类型业务能力，但实例能力画像均缺CAP_SIM_STATUS",
    file, "为仿真体加载仿真状态生成能力并复测继承、配置边界及旧实例迁移",
])))
write("issues.csv", issues)
