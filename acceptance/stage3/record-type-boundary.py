"""Record TC-017 list/count and matrix/export observations."""
import csv
import json
from pathlib import Path

here = Path(__file__).resolve().parent
ui = json.loads((here / "evidence/TC-017-type-boundary.json").read_text(encoding="utf-8"))
api = json.loads((here / "evidence/TC-017-type-matrix-api.json").read_text(encoding="utf-8"))
assert ui["listRowCount"] == ui["matrixRowCount"] == 5
assert not ui["listHasCountColumns"] and not api["typeListHasCounts"]
assert api["capabilityColumnCount"] == 8 and api["matrixMatchesFrozenExpected"]
assert ui["exportControlCount"] == 0 and ui["addDeleteTypeButtons"] == 0


def read(name):
    with (here / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(name, rows):
    with (here / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


steps = read("steps.csv")
for row in steps:
    if row["stepId"] == "TC-017.S1":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", observedAt="2026-10-25", issue="DEF-S3-017",
                   actual="列表有五种类型且无新增删除入口；列表无三项计数，详情仅显式列出实例数，支持能力和模板须手数，未直接显示其数量",
                   evidence="acceptance/stage3/evidence/TC-017-type-boundary.json;acceptance/stage3/evidence/TC-017-type-matrix-api.json;acceptance/stage3/evidence/TC-017-type-list.png")
    elif row["stepId"] == "TC-017.S3":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", observedAt="2026-10-25", issue="DEF-S3-018",
                   actual="五类型×八能力 API 矩阵与冻结用例一致；页面无 Excel 导出入口，无法核对导出与页面一致；仿真体继承分支待补",
                   evidence="acceptance/stage3/evidence/TC-017-type-boundary.json;acceptance/stage3/evidence/TC-017-type-matrix-api.json;acceptance/stage3/evidence/TC-017-type-matrix.png")
write("steps.csv", steps)

rules = read("rules.csv")
for row in rules:
    if row["ruleId"] in {"SRS_F006A.R01", "SRS_F006A.R02"}:
        assert row["status"] == "NOT_RUN"
        row.update(status="P", verifiedBy="TC-017.S1", evidence="acceptance/stage3/evidence/TC-017-type-matrix-api.json;acceptance/stage3/evidence/TC-017-type-boundary.json")
write("rules.csv", rules)

issues = read("issues.csv")
for ident, step, fact, action in [
    ("DEF-S3-017", "TC-017.S1", "设备类型列表不显示支持能力数、模板数、实例数；详情仅显式显示实例数，另外两项只能手数", "在类型列表或详情显示三项数量并与实例/模板记录对照复测"),
    ("DEF-S3-018", "TC-017.S3", "五类型八能力矩阵正确，但能力约束矩阵页无Excel导出入口", "实现矩阵Excel导出并比对单元格；复测仿真体继承"),
]:
    assert ident not in {row["编号"] for row in issues}
    issues.append(dict(zip(issues[0].keys(), [ident, "缺陷", "中", step, "SRS_F006A", "待修复", fact,
                                             "acceptance/stage3/evidence/TC-017-type-boundary.json;acceptance/stage3/evidence/TC-017-type-matrix-api.json", action])))
write("issues.csv", issues)
