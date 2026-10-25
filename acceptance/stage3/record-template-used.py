"""Record fresh TC-018.S3 / TC-019.S1-S2 template reference checks."""
import csv
import json
from pathlib import Path

here = Path(__file__).resolve().parent
ev = json.loads((here / "evidence/TC-018-019-template-used-retry3.json").read_text(encoding="utf-8"))
boundary = json.loads((here / "evidence/TC-018-instance-boundary.json").read_text(encoding="utf-8"))
obs = ev["observations"]
assert ev["runtimeInput"] == boundary["runtimeInput"] == "V1.5"
assert obs["firstBrowserExit"] == obs["thirdBrowserExit"] == 0
assert obs["firstBrowser"]["templateSelectCount"] == 1
assert obs["firstBrowser"]["prefilledName"] == "阶段三已使用航显模板"
assert obs["firstBrowser"]["prefilledDefault"] == "template-default"
assert obs["firstCapabilityStatus"] == "UNTESTED"
assert obs["firstCustomizedDefault"] == "instance-custom"
assert boundary["httpStatus"] == 400 and boundary["rejectedCodeAbsent"]
assert boundary["beforeCapabilityCount"] == boundary["afterCapabilityCount"]
assert obs["usedDeleteHttpStatus"] == 409
assert obs["usedDeleteMessage"] == "该模板已被2个设备实例使用，不可删除"
assert obs["actualReferencedDeviceCount"] == "2" and obs["usageAfterSecond"] == 2
assert obs["stoppedTemplateStatus"] == "INACTIVE"
assert obs["thirdBrowser"]["templateSelectCount"] == 0
assert obs["thirdBrowser"]["activeTemplateOptionCount"] == 0
assert obs["oldInstanceStatusAfterStop"] == "UNTESTED"
assert obs["oldInstanceDefaultAfterStop"] == "instance-custom"
assert ev["cleanup"]["templateAbsent"] and ev["cleanup"]["capabilityRows"] == "0"
assert all(row.endswith("|DELETED") for row in ev["cleanup"]["deviceStates"])


def read(name):
    with (here / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(name, rows):
    with (here / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


files = ("acceptance/stage3/evidence/TC-018-019-template-used-retry3.json;"
         "acceptance/stage3/evidence/TC-018-template-prefill.png;"
         "acceptance/stage3/evidence/TC-019-inactive-template-excluded.png")
boundary_file = "acceptance/stage3/evidence/TC-018-instance-boundary.json"
steps = read("steps.csv")
for row in steps:
    if row["stepId"] == "TC-018.S3":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", observedAt="2026-10-26", issue="",
            actual="新航显实例页面加载唯一有效标准模板并预填默认值；实例引用模板后将contentData定制为instance-custom且状态UNTESTED；仿真航显越界能力创建返回400且数量不变",
            evidence=files + ";" + boundary_file)
    elif row["stepId"] == "TC-019.S1":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", observedAt="2026-10-26", issue="",
            actual="两台独立设备引用模板后usageCount=2且库中DISTINCT设备数=2；删除返回409及精确的已被2个设备实例使用提示；模板可停用",
            evidence=files)
    elif row["stepId"] == "TC-019.S2":
        assert row["status"] == "NOT_RUN"
        row.update(status="NT", observedAt="2026-10-26", issue="NT-S3-014",
            actual="模板停用后新同类设备页面无该模板；原实例参数与UNTESTED状态均未改变；原实例先启用后的可用性保持尚未实测",
            evidence=files)
write("steps.csv", steps)

rules = read("rules.csv")
for row in rules:
    if row["ruleId"] == "SRS_F006A.R05":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", verifiedBy="TC-018.S3", evidence=files)
    elif row["ruleId"] == "SRS_F006A.R06":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", verifiedBy="TC-018.S3", evidence=boundary_file)
    elif row["ruleId"] == "SRS_F006A.R08":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", verifiedBy="TC-019.S1", evidence=files)
write("rules.csv", rules)

issues = read("issues.csv")
ident = "NT-S3-014"
assert ident not in {row["编号"] for row in issues}
issues.append(dict(zip(issues[0].keys(), [
    ident, "前置缺口", "待定", "TC-019.S2", "SRS_F006A", "待补启用实例",
    "停用模板前原实例处于UNTESTED，仅证明状态不变；尚需对已启用且可调用实例验证停用后仍可用",
    files, "创建可连通隔离实例并通过能力测试后启用，停用模板，再验证原实例调用与新实例候选"])))
write("issues.csv", issues)
