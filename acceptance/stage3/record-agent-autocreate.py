"""Record the fresh TC-011.S1 and duplicate device-code observations."""
import csv
import json
from datetime import datetime
from pathlib import Path

here = Path(__file__).resolve().parent
files = sorted((here / "evidence").glob("TC-011-agent-autocreate-20*.json"))
assert len(files) == 1, files
ev = json.loads(files[0].read_text(encoding="utf-8"))
assert ev["initialConnectionStatus"] == "UNTESTED"
assert ev["duplicateHttpStatus"] == 409 and ev["duplicateCount"] == 1
assert ev["deviceCode"] not in ev["duplicateMessage"]
assert ev["testResponse"]["result"] == "PASSED"
assert not ev["agentsAfterSuccessfulTest"]
first, second = ev["firstExplicitCreate"], ev["secondExplicitCreate"]
assert first["agentId"] == second["agentId"]
assert len(ev["agentsAfterFirstCreate"]) == len(ev["agentsAfterSecondCreate"]) == 1
assert ev["agentsAfterFirstCreate"][0]["agentStatus"] == "ENABLED"
assert ev["agentsAfterFirstCreate"][0]["workStatus"] == "IDLE"
assert ev["cleanup"]["deviceStatus"] == "DELETED"
assert ev["cleanup"]["agentsAfterDelete"][0]["agentStatus"] == "ARCHIVED"
assert ev["cleanup"]["simulatorStopped"]
ref = "acceptance/stage3/evidence/" + files[0].name
prior = "acceptance/stage3/evidence/TC-009-connection-success-20261026T062515Z.json"
status_sync = "acceptance/stage3/evidence/TC-012-status-sync.json"
today = datetime.now().astimezone().date().isoformat()


def update(name, key, changes):
    path = here / name
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    for row in rows:
        if row[key] in changes:
            changes[row[key]](row)
    assert all(set(row).issubset(fields) for row in rows)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def step008(row):
    assert row["status"] == "F" and "DEF-S3-011" in row["issue"]
    row["actual"] += "；新档案重复提交409但仅提示设备编码已存在，未指明冲突编码"
    row["evidence"] += ";" + ref
    row["issue"] += ";DEF-S3-038"


def step011(row):
    assert row["status"] == "NOT_RUN"
    row.update(status="F", observedAt=today,
               actual="临时设备连接测试通过后代理列表仍为0，未自动创建；显式创建后代理启用空闲，第二次显式创建返回同一编号且数量保持1；删除设备后代理归档。能力加载分支未由此证明",
               evidence=ref, issue="DEF-S3-039")


update("steps.csv", "stepId", {"TC-008.S1": step008, "TC-011.S1": step011})


def rule(status, verified, evidence, issue=""):
    def apply(row):
        assert row["status"] == "NOT_RUN"
        row.update(status=status, verifiedBy=verified, evidence=evidence, issue=issue)
    return apply


update("rules.csv", "ruleId", {
    "SRS_F003.R01": rule("F", "TC-008.S1", ref, "DEF-S3-038"),
    "SRS_F004.R01": rule("P", "TC-011.S1", ref),
    "SRS_F004.R02": rule("P", "TC-009.S1;TC-011.S1", prior + ";" + ref),
    "SRS_F004.R03": rule("P", "TC-012.S2;TC-011.S1", status_sync + ";" + ref),
})
issues = here / "issues.csv"
with issues.open(encoding="utf-8-sig", newline="") as stream:
    found = {row["编号"] for row in csv.DictReader(stream)}
assert not {"DEF-S3-038", "DEF-S3-039"} & found
with issues.open("a", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["DEF-S3-038", "缺陷", "低", "TC-008.S1", "SRS_F003.R01", "待修复",
                     "有效新档案重复提交被409拒绝，但仅返回设备编码已存在，未指出实际冲突编码S3_TC011_AGENT",
                     ref, "重复编码响应指出冲突编码，复测API及新增表单提示"])
    writer.writerow(["DEF-S3-039", "缺陷", "中", "TC-011.S1", "", "待修复",
                     "新设备通过连接测试后代理列表仍为空；必须额外显式调用创建代理接口，原步骤要求连接测试通过后自动创建",
                     ref, "连接测试通过后自动创建或绑定唯一启用代理，复测重复触发、初始状态和能力加载"])
print("recorded TC-011.S1, SRS_F003.R01, SRS_F004.R01/R02 and DEF-S3-038/039")
