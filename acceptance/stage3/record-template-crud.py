"""Record isolated TC-018/019 template validation, version, and cleanup results."""
import csv
import json
from pathlib import Path

here = Path(__file__).resolve().parent
ev = json.loads((here / "evidence/TC-018-019-template-crud.json").read_text(encoding="utf-8"))
assert all(x["httpStatus"] == 400 for x in ev["invalid"].values())
assert ev["invalid"]["outOfBoundaryType"]["boundaryMessage"]
assert ev["invalid"]["missingInputName"]["missingNameMessage"]
assert ev["invalidRequestsCreatedNoTemplate"]
assert ev["createdVersion"] == "V1.0" and ev["updatedVersion"] == ev["listedVersionAfterUpdate"] == "V1.1"
assert ev["updatedDefaultVisible"] and ev["duplicateHttpStatus"] == 409
assert ev["versionRowsAfterUpdate"] == ["V1.1"] and ev["historicalVersionEndpointStatus"] != 200
assert ev["incompleteRequiredInputHttpStatus"] == 200
assert ev["beforeTemplateCount"] == ev["afterCleanupTemplateCount"] == 0
assert ev["createdUsageCount"] == 0 and not ev["cleanupErrors"] and ev["temporaryCodesAbsentAfter"]


def read(name):
    with (here / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(name, rows):
    with (here / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


file = "acceptance/stage3/evidence/TC-018-019-template-crud.json"
steps = read("steps.csv")
for row in steps:
    if row["stepId"] == "TC-018.S1":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", observedAt="2026-10-26", issue="DEF-S3-022",
                   actual="编码/名称/说明边界、重复、越界能力、空输入输出和缺参数名均拒绝；但CAP_INFO_DISPLAY只含任意输入参数的模板仍保存200，缺能力调用必填参数校验",
                   evidence=file)
    elif row["stepId"] == "TC-018.S2":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", observedAt="2026-10-26", issue="DEF-S3-023",
                   actual="新模板V1.0、编辑后V1.1且默认值更新；库中只剩V1.1当前行，旧V1.0无可查询历史版本；关联实例样例测试未执行",
                   evidence=file)
    elif row["stepId"] == "TC-019.S3":
        assert row["status"] == "NOT_RUN"
        row.update(status="NT", observedAt="2026-10-26", issue="NT-S3-012",
                   actual="两个未使用临时模板均经API删除且列表恢复0；浏览器二次确认、数量和操作审计尚未核对",
                   evidence=file)
write("steps.csv", steps)

rules = read("rules.csv")
for row in rules:
    if row["ruleId"] == "SRS_F006A.R07":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", verifiedBy="TC-018.S1", evidence=file)
    elif row["ruleId"] == "SRS_F006A.R10":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", verifiedBy="TC-018.S1", issue="DEF-S3-022", evidence=file)
    elif row["ruleId"] == "SRS_F006A.R11":
        assert row["status"] == "NOT_RUN"
        row.update(status="NT", verifiedBy="TC-018.S1", issue="NT-S3-013", evidence=file)
    elif row["ruleId"] == "SRS_F006A.R12":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", verifiedBy="TC-018.S2", issue="DEF-S3-023", evidence=file)
write("rules.csv", rules)

issues = read("issues.csv")
for ident, kind, level, related, rule, state, fact, action in [
    ("DEF-S3-022", "缺陷", "高", "TC-018.S1", "SRS_F006A.R10", "待修复",
     "CAP_INFO_DISPLAY模板仅有任意输入参数仍可保存，缺该能力调用全部必填参数校验", "按类型能力契约校验输入定义，再复测缺字段与有效模板"),
    ("DEF-S3-023", "缺陷", "中", "TC-018.S2", "SRS_F006A.R12", "待修复",
     "模板从V1.0编辑成V1.1后仅保留当前行，旧版本不可查询追溯", "保存不可变历史版本并提供查询与实例引用，复测V1.0/V1.1"),
    ("NT-S3-012", "前置缺口", "待定", "TC-019.S3", "SRS_F006A", "待补页面",
     "未使用模板API删除及列表恢复已见，浏览器二次确认与操作审计未核对", "浏览器取消及确认删除并核对日志"),
    ("NT-S3-013", "前置缺口", "待定", "TC-018.S1", "SRS_F006A.R11", "待补流程",
     "空输出定义被拒绝，但未以任务步骤验证输出定义用于完成条件", "以关联设备实例执行样例任务核对输出判定"),
]:
    assert ident not in {row["编号"] for row in issues}
    issues.append(dict(zip(issues[0].keys(), [ident, kind, level, related, rule, state, fact, file, action])))
write("issues.csv", issues)
