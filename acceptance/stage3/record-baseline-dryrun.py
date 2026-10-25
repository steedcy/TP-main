"""Record fresh TC-027–030 browser/API/DB dry-run observations conservatively."""
import csv
import json
from pathlib import Path

here = Path(__file__).resolve().parent


def ev(name):
    return json.loads((here / "evidence" / name).read_text(encoding="utf-8"))


guards = ev("TC-029-baseline-dryrun-guards.json")
life = ev("TC-028-030-baseline-dryrun-lifecycle.json")
ui1 = ev("TC-028-baseline-dryrun-ui-attempt1.json")
ui2 = ev("TC-028-baseline-dryrun-ui.json")
summary = ev("TC-028-030-baseline-dryrun-summary.json")
audit = ev("TC-028-baseline-dryrun-audit.json")
assert all(x["runtimeInput"] == "V1.5" for x in (guards, life, ui1, ui2, summary, audit))
assert guards["createdStatus"] == guards["afterGuardStatus"] == "DRAFT"
assert guards["beforeTaskCount"] == guards["afterGuardTaskCount"]
assert all(x[0] == 400 for x in guards["guards"].values())
assert guards["cleanup"]["nameAbsent"]
assert len(life["runs"]) == 2 and all(x["result"] == "SUCCESS" for x in life["runs"])
assert life["lifecycle"]["created"] == ["V1.0", "DRAFT"]
assert life["lifecycle"]["afterFirstTrial"] == ["V1.0", "DRY_RUN_PASSED"]
assert life["lifecycle"]["afterFirstEnable"] == "ENABLED"
assert life["lifecycle"]["afterEdit"] == ["V1.1", "DRAFT"]
assert life["lifecycle"]["enableEditedWithoutTrial"].startswith("HTTP 400")
assert life["lifecycle"]["afterSecondTrial"] == ["V1.1", "DRY_RUN_PASSED"]
assert life["lifecycle"]["afterSecondEnable"] == "ENABLED"
assert ui2["editedVersion"] == "V1.3" and ui2["versionVisible"]
assert ui2["defaultInputs"] == ["TEXT", "阶段三试运行信息", "60"]
assert ui2["resultVisible"] and ui2["stepRows"] == 1 and ui2["durationHeaderVisible"]
assert ui2["eventsVisible"] == 8 and ui2["statusAfterEnable"] == "ENABLED"
assert ui2["finalStatus"] == summary["templateFinalStatus"] == "DISABLED"
assert len(summary["taskPlanRows"]) == 4 and len(summary["commandRows"]) == 8
assert [x.split("|")[4] for x in summary["taskPlanRows"]] == ["V1.0", "V1.1", "V1.2", "V1.3"]
assert all("|COMPLETED|t|BASELINE_TEMPLATE|" in x for x in summary["taskPlanRows"])
assert all(x.split("|")[2] in ("ACCEPTED", "SUCCEEDED") and x.endswith("|Y")
           for x in summary["commandRows"])
assert summary["formalCompletedSql"] == 7 and summary["dryRunCompletedSql"] == 10
assert summary["dashboardCompleted"] == summary["allCompletedSql"] == 17
assert audit["startOperationCount"] == audit["successEventCount"] == 4
assert audit["completionOperationCount"] == 0
assert "BASELINE_TEMPLATE_DISABLE" in summary["templateAuditTypes"]


def read(name):
    with (here / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(name, rows):
    with (here / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


guards_file = "acceptance/stage3/evidence/TC-029-baseline-dryrun-guards.json"
files = ("acceptance/stage3/evidence/TC-028-030-baseline-dryrun-lifecycle.json;"
         "acceptance/stage3/evidence/TC-028-baseline-dryrun-ui-attempt1.json;"
         "acceptance/stage3/evidence/TC-028-baseline-dryrun-ui.json;"
         "acceptance/stage3/evidence/TC-028-baseline-dryrun-ui.png;"
         "acceptance/stage3/evidence/TC-028-030-baseline-dryrun-summary.json;"
         "acceptance/stage3/evidence/TC-028-baseline-dryrun-audit.json")
steps = read("steps.csv")
for row in steps:
    if row["stepId"] == "TC-027.S1":
        assert row["status"] == "NOT_RUN"
        row.update(status="NT", observedAt="2026-10-26", issue="NT-S3-019",
            actual="启用模板编辑生成V1.1草稿，旧完成试运行计划仍冻结V1.0；停用退出启用状态且增改启停有操作记录；执行中任务冻结旧版本尚未实测",
            evidence=files)
    elif row["stepId"] == "TC-028.S1":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", observedAt="2026-10-26", issue="",
            actual="页面预填模板输入并显示V1.2/V1.3版本，选择在线航显仿真代理后顺序执行；成功页有总体/步骤结果、1秒耗时及8条事件；DB任务标记试运行、计划来源基线模板",
            evidence=files)
    elif row["stepId"] == "TC-028.S2":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", observedAt="2026-10-26", issue="DEF-S3-002;DEF-S3-027",
            actual="成功版本在页面启用，四个试运行任务有冻结计划及完整事件/命令响应；正式完成7、试运行完成10，运行总览COMPLETED=17；试运行发起和启用有操作记录，结果仅在任务事件无操作记录",
            evidence=files)
    elif row["stepId"] == "TC-029.S1":
        assert row["status"] == "NOT_RUN"
        row.update(status="NT", observedAt="2026-10-26", issue="NT-S3-020",
            actual="缺必填输入、未选设备或能力不匹配均400，任务数不变；未静态通过模板无法正常创建，试运行五步与运动安全前置未独立执行",
            evidence=guards_file)
    elif row["stepId"] == "TC-029.S2":
        assert row["status"] == "NOT_RUN"
        row.update(status="NT", observedAt="2026-10-26", issue="NT-S3-021",
            actual="未试运行草稿启用400且仍DRAFT；步骤失败或超时及失败版本启用拒绝尚未注入",
            evidence=guards_file)
    elif row["stepId"] == "TC-030.S2":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", observedAt="2026-10-26", issue="",
            actual="V1.0试运行通过启用后编辑为V1.1草稿，直接启用400；V1.1再次试运行成功后启用；四次计划快照分别冻结V1.0～V1.3，模板操作有审计",
            evidence=files)
write("steps.csv", steps)

rules = read("rules.csv")
for row in rules:
    ident = row["ruleId"]
    updates = {
        "SRS_F008.R07": ("NT", "TC-027.S1", "NT-S3-019", files),
        "SRS_F008.R08": ("P", "TC-027.S1", "", files),
        "SRS_F009.R01": ("NT", "TC-029.S1", "NT-S3-020", guards_file),
        "SRS_F009.R02": ("P", "TC-029.S1", "", guards_file),
        "SRS_F009.R03": ("P", "TC-028.S2", "", files),
        "SRS_F009.R04": ("NT", "TC-029.S2", "NT-S3-021", guards_file),
        "SRS_F009.R05": ("F", "TC-028.S2", "DEF-S3-002", files),
        "SRS_F009.R06": ("P", "TC-030.S2", "", files),
        "SRS_F009.R08": ("F", "TC-028.S2", "DEF-S3-027", files),
    }
    if ident in updates:
        assert row["status"] == "NOT_RUN"
        status, verified, issue, evidence = updates[ident]
        row.update(status=status, verifiedBy=verified, issue=issue, evidence=evidence)
write("rules.csv", rules)

issues = read("issues.csv")
for row in issues:
    if row["编号"] == "DEF-S3-002":
        row["关联用例步骤"] += ";TC-028.S2"
        row["关联需求规则"] += ";SRS_F009.R05"
        row["事实"] += "；本轮四次试运行后正式完成7、试运行完成10，API总览COMPLETED=17"
        row["证据"] += ";acceptance/stage3/evidence/TC-028-030-baseline-dryrun-summary.json"
for ident, kind, level, related, rule, state, fact, evidence, action in [
    ("DEF-S3-027", "缺陷", "中", "TC-028.S2", "SRS_F009.R08", "待修复",
     "四次试运行成功均有任务结果事件；操作日志只有四条RUNNING发起，没有成功/失败结果记录",
     files, "试运行完成和失败时分别写结果操作日志，带模板版本与任务ID，再复测"),
    ("NT-S3-019", "前置缺口", "待定", "TC-027.S1", "SRS_F008.R07", "待补执行中版本",
     "启用模板编辑变新草稿、已完成试运行计划冻结原版本；执行中任务持续使用旧版本未实测",
     files, "启动隔离较长任务，在执行中修改模板并核对运行计划快照"),
    ("NT-S3-020", "前置缺口", "待定", "TC-029.S1", "SRS_F009.R01", "待补安全前置",
     "缺输入、未选设备和能力不匹配均拒绝且无任务；静态不通过模板、五步及运动安全试运行前置未独立实测",
     guards_file, "以隔离无效模板状态和五步/安全夹具复核试运行拒绝"),
    ("NT-S3-021", "前置缺口", "待定", "TC-029.S2", "SRS_F009.R04", "待补失败试运行",
     "未试运行草稿启用拒绝；步骤执行失败、超时与失败版本启用尚未注入",
     guards_file, "注入单步失败和超时，核对失败原因、草稿状态和启用拒绝"),
]:
    assert ident not in {row["编号"] for row in issues}
    issues.append(dict(zip(issues[0].keys(), [ident, kind, level, related, rule, state, fact, evidence, action])))
write("issues.csv", issues)
