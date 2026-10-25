"""Promote TC-027/029 after live version/failure checks; retain TC-030 partial."""
import csv
import json
from pathlib import Path

here = Path(__file__).resolve().parent
cancel = json.loads((here / "evidence/TC-030-baseline-dryrun-cancel.json").read_text(encoding="utf-8"))
failures = json.loads((here / "evidence/TC-029-baseline-dryrun-failures.json").read_text(encoding="utf-8"))
running = json.loads((here / "evidence/TC-027-baseline-running-version.json").read_text(encoding="utf-8"))
assert all(x["runtimeInput"] == "V1.5" for x in (cancel, failures, running))
assert cancel["observations"]["dispatchedBeforeCancel"]
assert cancel["observations"]["preCancelTaskStatus"] == "EXECUTING"
assert cancel["observations"]["cancelApiResult"] == "CANCELLED"
assert cancel["observations"]["finalTaskStatus"] == "MANUAL_TERMINATED"
assert "TASK_CANCEL_REQUESTED" in cancel["observations"]["events"]
assert "TASK_CANCEL|SENT" in cancel["observations"]["commands"]
assert cancel["restore"] == {"delayMs": 1000, "templateStatus": "DISABLED",
                             "agent": "ENABLED|ONLINE|IDLE|0"}
assert [x["scenario"] for x in failures["cases"]] == ["FAILED", "TIMEOUT"]
assert all(x["result"] == "FAILED" and x["afterTemplateStatus"] == "DRAFT"
           and x["enableAfterFailure"][0] == 400 and x["stepResults"][0]["duration"] >= 1
           and x["dbTask"] == "FAILED|t|t" for x in failures["cases"])
assert failures["restore"] == {"scenario": "SUCCESS", "templateStatus": "DISABLED",
                               "agent": "ENABLED|ONLINE|IDLE|0"}
obs = running["observations"]
assert obs["runVersion"] == obs["snapshotBeforeEdit"] == obs["snapshotImmediatelyAfterEdit"] == obs["snapshotAfterResult"] == "V1.7"
assert obs["taskStatusAtEdit"] == "EXECUTING" and obs["dispatchedBeforeEdit"]
assert obs["editedVersion"] == "V1.8" and obs["statusAfterEdit"] == obs["templateStatusAfterOldRun"] == "DRAFT"
assert obs["result"] == "SUCCESS" and obs["taskStatusAfterResult"] == "COMPLETED"
assert running["restore"] == {"delayMs": 1000, "templateStatus": "DISABLED",
                              "agent": "ENABLED|ONLINE|IDLE|0"}


def read(name):
    with (here / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(name, rows):
    with (here / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


running_file = "acceptance/stage3/evidence/TC-027-baseline-running-version.json"
failure_file = "acceptance/stage3/evidence/TC-029-baseline-dryrun-failures.json"
cancel_file = "acceptance/stage3/evidence/TC-030-baseline-dryrun-cancel.json"
steps = read("steps.csv")
for row in steps:
    if row["stepId"] == "TC-027.S1":
        assert row["status"] == "NT" and row["issue"] == "NT-S3-019"
        row.update(status="P", observedAt="2026-10-26", issue="",
            actual="V1.0启用模板编辑生成新草稿并可停用；任务32在EXECUTING期间模板从V1.7改V1.8，任务仍按冻结V1.7完成且V1.8保持DRAFT，增改启停审计齐全",
            evidence=row["evidence"] + ";" + running_file)
    elif row["stepId"] == "TC-029.S2":
        assert row["status"] == "NT" and row["issue"] == "NT-S3-021"
        row.update(status="P", observedAt="2026-10-26", issue="",
            actual="模拟设备FAILED/TIMEOUT使任务30/31失败，各保存步骤原因和1秒耗时，模板保持DRAFT且两次启用均400；未试运行草稿启用亦400",
            evidence=row["evidence"] + ";" + failure_file)
    elif row["stepId"] == "TC-030.S1":
        assert row["status"] == "NOT_RUN"
        row.update(status="NT", observedAt="2026-10-26", issue="NT-S3-022",
            actual="任务29在EXECUTING且STEP_DISPATCHED后管理员取消返回CANCELLED，TASK_CANCEL已下发并有中止事件；五步和运动安全边界在该中止路径未独立挑战",
            evidence=cancel_file)
write("steps.csv", steps)

rules = read("rules.csv")
for row in rules:
    if row["ruleId"] == "SRS_F008.R07":
        assert row["status"] == "NT" and row["issue"] == "NT-S3-019"
        row.update(status="P", verifiedBy="TC-027.S1", issue="", evidence=row["evidence"] + ";" + running_file)
    elif row["ruleId"] == "SRS_F009.R04":
        assert row["status"] == "NT" and row["issue"] == "NT-S3-021"
        row.update(status="P", verifiedBy="TC-029.S2", issue="", evidence=row["evidence"] + ";" + failure_file)
    elif row["ruleId"] == "SRS_F009.R07":
        assert row["status"] == "NOT_RUN"
        row.update(status="NT", verifiedBy="TC-030.S1", issue="NT-S3-022", evidence=cancel_file)
write("rules.csv", rules)

issues = read("issues.csv")
for row in issues:
    if row["编号"] == "NT-S3-019":
        row["状态"] = "已补证"
        row["事实"] = "任务32执行中修改模板，原计划V1.7冻结并完成，新V1.8维持草稿"
        row["证据"] += ";" + running_file
    elif row["编号"] == "NT-S3-021":
        row["状态"] = "已补证"
        row["事实"] = "模拟FAILED/TIMEOUT两次试运行均失败、保存原因且模板草稿不可启用"
        row["证据"] += ";" + failure_file
ident = "NT-S3-022"
assert ident not in {row["编号"] for row in issues}
issues.append(dict(zip(issues[0].keys(), [
    ident, "前置缺口", "待定", "TC-030.S1", "SRS_F009.R07", "待补边界中止",
    "执行中取消和TASK_CANCEL已证；五步及运动安全边界在该中止路径未独立挑战",
    cancel_file, "以五步及拒绝安全字段的隔离试运行重核中止前置与代理拦截"])))
write("issues.csv", issues)
