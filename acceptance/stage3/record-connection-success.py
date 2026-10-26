"""Record fresh TC-009.S1 handshake and Chrome result display findings."""
import csv
import json
from datetime import datetime
from pathlib import Path

here = Path(__file__).resolve().parent
files = sorted((here / "evidence").glob("TC-009-connection-success-20*.json"))
assert len(files) == 1, files
run = json.loads(files[0].read_text(encoding="utf-8"))
ui = json.loads((here / "evidence/TC-009-connection-success-ui.json").read_text(encoding="utf-8"))
assert run["saved"]["connectionTestStatus"] == "UNTESTED"
assert run["untestedAgentCreateHttpStatus"] == 400
assert run["health"]["deviceCode"] == run["deviceCode"]
assert run["connectionTestResponse"]["result"] == "PASSED"
assert run["checked"]["connectionTestStatus"] == "PASSED"
assert run["agentListed"] and run["createdAgent"]["agentStatus"] == "ENABLED"
assert run["cleanup"] == {"deviceStatus": "DELETED", "simulatorStopped": True}
assert ui["httpStatus"] == 200 and ui["responseBody"]["data"]["result"] == "PASSED"
assert ui["toastText"] == "连接测试通过"
assert not ui["durationInToast"] and not ui["durationInResponse"]
refs = ";".join("acceptance/stage3/evidence/" + name for name in [
    files[0].name, "TC-009-connection-success-ui.json", "TC-009-connection-success-ui.png"])
today = datetime.now().astimezone().date().isoformat()


def update(name, key, changes):
    path = here / name
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    for row in rows:
        if row[key] in changes:
            assert row["status"] == "NOT_RUN", row[key]
            row.update(changes[row[key]])
    assert all(set(row).issubset(fields) for row in rows)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


update("steps.csv", "stepId", {"TC-009.S1": {
    "status": "F", "observedAt": today,
    "actual": "新建临时仿真航显档案初始UNTESTED且代理创建被拒；有效身份/协议/状态响应后连接测试PASSED并保存，允许创建启用代理；Chrome页面只提示连接测试通过，未显示耗时，接口也未返回耗时字段",
    "evidence": refs, "issue": "DEF-S3-037"}})
update("rules.csv", "ruleId", {
    "SRS_F003.R02": {"status": "P", "verifiedBy": "TC-009.S1", "evidence": refs},
    "SRS_F003.R03": {"status": "P", "verifiedBy": "TC-009.S1;TC-009.S2",
                     "evidence": refs + ";acceptance/stage3/evidence/TC-009-connection-failures.json"},
})
issues = here / "issues.csv"
with issues.open(encoding="utf-8-sig", newline="") as stream:
    assert "DEF-S3-037" not in {row["编号"] for row in csv.DictReader(stream)}
with issues.open("a", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["DEF-S3-037", "缺陷", "低", "TC-009.S1", "", "待修复",
                     "新档案初始未测试且连接成功可创建启用代理；Chrome连接测试成功仅提示结果，不显示该次测试耗时，接口响应也无耗时字段",
                     refs,
                     "连接测试返回并展示服务端测量耗时；复测成功及失败分支的结果、时间和保存状态"])
print("recorded TC-009.S1, SRS_F003.R02/R03 and DEF-S3-037")
