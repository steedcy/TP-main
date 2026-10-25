"""Record fresh capability creation and invalid input results for TC-020/022."""
import csv
import json
from pathlib import Path

here = Path(__file__).resolve().parent
ev = json.loads((here / "evidence/TC-020-022-capability-create.json").read_text(encoding="utf-8"))
ui = json.loads((here / "evidence/TC-020-type-options.json").read_text(encoding="utf-8"))
assert ev["runtimeInput"] == ui["runtimeInput"] == "V1.5"
assert ev["initialCapabilities"] == 0
assert ev["created"]["capabilityStatus"] == "UNTESTED" and ev["created"]["lastTestAt"] is None
assert ev["listed"] == [{"capabilityCode": "S3_TC020_INFO", "capabilityStatus": "UNTESTED", "lastTestAt": None}]
assert ev["codesAfterInvalid"] == ["S3_TC020_INFO"]
assert ev["invalid"]["duplicateCode"]["httpStatus"] == 409
assert all(ev["invalid"][key]["httpStatus"] == 400 for key in
           ("emptyInput", "emptyOutput", "missingInputName", "outOfBoundary", "unknownStandardType"))
assert ev["cleanup"] == {"deviceStatus": "DELETED", "capabilityRows": "0"}
assert ui["listRows"] == 3
assert ui["typeOptions"] == ["仿真状态生成", "综合信息展示", "航班变更信息发布", "空间引导"]
assert "可用状态" in ui["columnHeaders"] and "最近测试时间" in ui["columnHeaders"]


def read(name):
    with (here / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(name, rows):
    with (here / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


files = ("acceptance/stage3/evidence/TC-020-022-capability-create.json;"
         "acceptance/stage3/evidence/TC-020-type-options.json;"
         "acceptance/stage3/evidence/TC-020-type-options.png")
steps = read("steps.csv")
for row in steps:
    if row["stepId"] == "TC-020.S1":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", observedAt="2026-10-26", issue="",
            actual="隔离航显能力保存编码/名称/类型/输入输出/条件/说明，列表状态UNTESTED且最近测试时间为空；仿真航显页面仅列仿真状态及继承的三项能力类型并显示状态/最近测试时间列",
            evidence=files)
    elif row["stepId"] == "TC-022.S1":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", observedAt="2026-10-26", issue="",
            actual="同设备重复编码409；空输入、空输出、缺参数名、越界能力及未知第九类均400且有对应提示；列表仍仅原合法能力",
            evidence=files)
write("steps.csv", steps)

rules = read("rules.csv")
for row in rules:
    if row["ruleId"] == "SRS_F006.R01":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", verifiedBy="TC-020.S1", evidence=files)
    elif row["ruleId"] == "SRS_F006.R02":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", verifiedBy="TC-022.S1", evidence=files)
    elif row["ruleId"] == "SRS_F006.R09":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", verifiedBy="TC-022.S1", evidence=files)
write("rules.csv", rules)
