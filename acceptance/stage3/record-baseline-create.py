"""Record fresh TC-025/026 baseline editor, validation and safety evidence."""
import csv
import json
from pathlib import Path

here = Path(__file__).resolve().parent


def ev(name):
    return json.loads((here / "evidence" / name).read_text(encoding="utf-8"))


created = ev("TC-025-026-baseline-create.json")
editor = ev("TC-025-026-baseline-editor.json")
bounds = ev("TC-025-baseline-boundaries.json")
names = ev("TC-025-baseline-invalid-names.json")
safety = ev("TC-026-baseline-motion-safety-matrix.json")
assert all(x["runtimeInput"] == "V1.5" for x in (created, editor, bounds, names, safety))
assert created["created"]["templateVersion"] == "V1.0"
assert created["created"]["templateStatus"] == "DRAFT"
assert created["savedStepSeq"] == [1, 2, 3, 4]
assert created["savedStepTimeouts"] == [60] * 4
assert created["detailMatchesList"] and created["cleanup"]["countRestored"]
assert editor["sequentialCaption"] and editor["defaultTimeouts"] == ["60", "60"]
assert editor["afterUp"] == ["second-condition", "first-condition"]
assert editor["afterDown"] == ["first-condition", "second-condition"]
assert editor["afterDeleteCount"] == 1 and editor["fiveStepCount"] == 5
assert editor["sixthStepButtonDisabled"] and not editor["motionOrComplexControls"]
assert [(x["nameLength"], x["stepCount"], x["timeouts"][0]) for x in bounds["cases"]] == [
    (1, 1, 10), (64, 5, 600)]
assert bounds["createAuditCount"] == 2 and bounds["beforeTemplateCount"] == bounds["afterTemplateCount"]
assert all(x["httpStatus"] == 400 for x in names["cases"].values())
assert names["beforeTemplateCount"] == names["afterTemplateCount"]
invalid = created["invalid"]
assert invalid["duplicateName"]["httpStatus"] == 409
assert all(invalid[x]["httpStatus"] == 400 for x in
           ("sixSteps", "capabilityGap", "undefinedInput", "requiredUnmapped",
            "emptyCompletion", "timeoutBelowTen", "timeoutAboveSixHundred"))
assert invalid["undefinedPriorOutput"] == {"httpStatus": 200, "message": "success", "createdStatus": "DRAFT"}
assert safety["variants"]["speedParam"]["httpStatus"] == 400
assert all(safety["variants"][x]["httpStatus"] == 200 for x in
           ("pathPointsParam", "emergencyStopParam", "lostConnectionParkingParam", "emergencyStopCondition"))
assert not safety["cleanupErrors"] and safety["beforeTemplateCount"] == safety["afterTemplateCount"]


def read(name):
    with (here / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(name, rows):
    with (here / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


files = ("acceptance/stage3/evidence/TC-025-026-baseline-create.json;"
         "acceptance/stage3/evidence/TC-025-026-baseline-editor.json;"
         "acceptance/stage3/evidence/TC-025-026-baseline-editor.png;"
         "acceptance/stage3/evidence/TC-025-baseline-boundaries.json;"
         "acceptance/stage3/evidence/TC-025-baseline-invalid-names.json")
safety_files = ("acceptance/stage3/evidence/TC-026-baseline-motion-safety-attempt1.json;"
                "acceptance/stage3/evidence/TC-026-baseline-motion-safety-matrix.json;"
                "acceptance/stage3/evidence/TC-025-026-baseline-editor.json")
steps = read("steps.csv")
for row in steps:
    if row["stepId"] == "TC-025.S1":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", observedAt="2026-10-26", issue="",
            actual="名称1/64位、步骤1/5个、超时10/600秒及默认60秒均保存为V1.0草稿；四步顺序重排后自动编号1～4，页面上移下移有效，第六步按钮禁用",
            evidence=files)
    elif row["stepId"] == "TC-025.S2":
        assert row["status"] == "NOT_RUN"
        row.update(status="NT", observedAt="2026-10-26", issue="NT-S3-018",
            actual="输入参数及草稿版本可查询，页面添加/上移/下移/删除序号一致，新建留痕；从原任务目标解析降级参数映射尚未实测",
            evidence=files)
    elif row["stepId"] == "TC-026.S1":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", observedAt="2026-10-26", issue="DEF-S3-025",
            actual="重复名、六步、能力缺口、未定义模板输入、必填输入无映射均拒绝；STEP3_OUTPUT.noSuchOutput引用不存在的前序输出仍保存200并成为DRAFT",
            evidence=files)
    elif row["stepId"] == "TC-026.S2":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", observedAt="2026-10-26", issue="DEF-S3-026",
            actual="页面仅顺序步骤且无复杂编排控件；speed/acceleration/attitude/obstacleAvoidance/speedLimit被拒，但pathPoints、emergencyStop、lostConnectionParking及急停完成条件仍保存为草稿",
            evidence=safety_files)
write("steps.csv", steps)

rules = read("rules.csv")
for row in rules:
    ident = row["ruleId"]
    if ident == "SRS_F008.R01":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", verifiedBy="TC-025.S1", evidence=files)
    elif ident == "SRS_F008.R02":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", verifiedBy="TC-026.S1", evidence=files)
    elif ident == "SRS_F008.R03":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", verifiedBy="TC-026.S1", evidence=files, issue="DEF-S3-025")
    elif ident == "SRS_F008.R04":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", verifiedBy="TC-026.S1", evidence=files)
    elif ident == "SRS_F008.R05":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", verifiedBy="TC-026.S1", evidence=files, issue="DEF-S3-025")
    elif ident == "SRS_F008.R06":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", verifiedBy="TC-026.S2", evidence=safety_files, issue="DEF-S3-026")
write("rules.csv", rules)

issues = read("issues.csv")
for ident, kind, level, related, rule, state, fact, evidence, action in [
    ("DEF-S3-025", "缺陷", "高", "TC-026.S1", "SRS_F008.R03;SRS_F008.R05", "待修复",
     "基线步骤引用不存在的前序STEP3_OUTPUT.noSuchOutput仍可保存为DRAFT，静态校验未核对源步骤输出定义",
     files, "校验前序步骤输出参数名与类型，拒绝不存在或类型不匹配引用并重跑TC-025/026"),
    ("DEF-S3-026", "缺陷", "高", "TC-026.S2", "SRS_F008.R06", "待修复",
     "运动安全字段矩阵中pathPoints、emergencyStop、lostConnectionParking及急停完成条件被接受为草稿",
     safety_files, "覆盖安全控制字段中英文/驼峰别名及完成条件，拒绝保存并回归全部字段矩阵"),
    ("NT-S3-018", "前置缺口", "待定", "TC-025.S2", "SRS_F008", "待补降级任务",
     "模板输入、编辑排序、草稿和新增留痕已证；从原任务目标解析降级参数映射未实测",
     files, "以隔离降级任务核对目标到模板输入映射和执行输出"),
]:
    assert ident not in {row["编号"] for row in issues}
    issues.append(dict(zip(issues[0].keys(), [ident, kind, level, related, rule, state, fact, evidence, action])))
write("issues.csv", issues)
