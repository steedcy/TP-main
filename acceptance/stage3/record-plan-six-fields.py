"""Record TC-039 failures for missing plan metadata and core definition mismatch."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
names = ["TC-039-plan-six-fields-20261026T042149Z.json",
         "TC-039-plan-six-fields-20261026T042249Z.json",
         "TC-039-task-definition-coverage-20261026T042427Z.json"]
oversize, flight, definitions = [json.loads((stage / "evidence" / n).read_text(encoding="utf-8"))
                                 for n in names]
assert oversize["schema"] == flight["schema"] == definitions["schema"] == "tip_stage2_v14"
assert oversize["fixtureModeRestored"] and flight["fixtureModeRestored"]
assert oversize.get("sourceMode", "oversize") == "oversize" and flight["sourceMode"] == "flight"
for run in [oversize, flight]:
    assert len(run["agentsAfter"]) == 6 and all(
        a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE" and
        a["workStatus"] == "IDLE" for a in run["agentsAfter"])
    assert [c["label"] for c in run["cases"]] == [
        "complete_candidate", "missing_precondition_and_failure_handling"]
    for case in run["cases"]:
        assert case["afterMaxTaskId"] == case["beforeMaxTaskId"] + 1
        assert case["task"]["status"] == "COMPLETED"
        assert [r["phase"] for r in case["modelRequests"]] == ["goal", "planning"]
        assert len(case["plans"]) == 2
        assert case["plans"][0]["source"] == "AUTONOMOUS"
        assert case["plans"][1]["source"] == "BASELINE_TEMPLATE"
        assert all(case["plans"][1][k] == "PASS" for k in
                   ["structureCheckResult", "capabilityCheckResult", "constraintCheckResult"])
        assert case["plans"][1]["frozenAt"]
o_complete, o_missing = oversize["cases"]
f_complete, f_missing = flight["cases"]
for case in [o_complete, o_missing]:
    plan = case["plans"][0]
    assert plan["structureCheckResult"] == plan["capabilityCheckResult"] == "PASS"
    assert plan["constraintCheckResult"] == "FAIL" and not plan["frozenAt"]
    assert any(e["reasonCode"] == "ERR_CAPABILITY_NOT_IN_TASK_DEFINITION"
               for e in plan["validationErrors"])
assert "CAP_INFO_DISPLAY" not in definitions["oversizeDefinition"]["availableCapabilityTypes"]
assert "CAP_INFO_DISPLAY" in definitions["flightDefinition"]["availableCapabilityTypes"]
for case in [f_complete, f_missing]:
    plan = case["plans"][0]
    assert all(plan[k] == "PASS" for k in
               ["structureCheckResult", "capabilityCheckResult", "constraintCheckResult"])
    assert plan["frozenAt"] and plan["validationErrors"] == []
    assert any(e["eventType"] == "PLAN_VALIDATED" and e["reasonCode"] is None
               for e in case["events"])
    assert any(e["eventType"] == "SUPERVISION_JUDGED" for e in case["events"])
assert all("precondition" in s and "failureHandling" in s for s in f_complete["plans"][0]["planSteps"])
assert all("precondition" not in s and "failureHandling" not in s
           for s in f_missing["plans"][0]["planSteps"])
refs = ";".join("acceptance/stage3/evidence/" + n for n in names)
day = datetime.now().astimezone().date().isoformat()

def update(name, key, changes):
    path = stage / name
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    for row in rows:
        if row[key] in changes:
            assert row["status"] == "NOT_RUN", row[key]
            row.update(changes[row[key]])
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

update("steps.csv", "stepId", {
    "TC-039.S1": {"status": "F", "observedAt": day,
        "actual": "任务55完整四步自主候选三类PASS后冻结并进入监督；任务56删除全部步骤的前置条件和失败处理后仍三类PASS、无错误清单并冻结自主版本，完整性闸门失效",
        "evidence": refs, "issue": "DEF-S3-034"},
    "TC-039.S2": {"status": "F", "observedAt": day,
        "actual": "任务56缺两项必需步骤字段仍结构PASS并冻结；任务53/54超规完整四步自主候选含必需CAP_INFO_DISPLAY，却因该任务定义允许能力清单缺该类型而约束FAIL，只能降级基线",
        "evidence": refs, "issue": "DEF-S3-034;DEF-S3-035"},
})
update("rules.csv", "ruleId", {
    "SRS_F012.R04": {"status": "F", "verifiedBy": "TC-039.S1;TC-039.S2",
                     "evidence": refs, "issue": "DEF-S3-034"},
    "SRS_F013.R01": {"status": "F", "verifiedBy": "TC-039.S2",
                     "evidence": refs, "issue": "DEF-S3-034"},
})
issues = stage / "issues.csv"
with issues.open(encoding="utf-8-sig", newline="") as stream:
    existing = {row["编号"] for row in csv.DictReader(stream)}
assert "DEF-S3-034" not in existing and "DEF-S3-035" not in existing
with issues.open("a", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["DEF-S3-034", "缺陷", "高", "TC-039.S1;TC-039.S2",
                     "SRS_F012.R04;SRS_F013.R01", "待修复",
                     "任务56四步自主候选全部删除precondition与failureHandling，结构/能力/约束仍全部PASS、无错误且冻结；任务55完整候选作同环境对照",
                     refs, "阶段4将六项步骤字段完整性纳入结构硬校验，缺字段不得冻结/监督/分配；复测所有来源和空值边界"])
    writer.writerow(["DEF-S3-035", "缺陷", "高", "TC-039.S2", "", "待修复",
                     "超规任务定义可用能力不含CAP_INFO_DISPLAY，而核心超规场景要求智慧航显提示；任务53/54完整四步自主候选因该类型超出定义范围被约束拒绝并降级",
                     refs, "阶段4使超规任务定义可用能力与核心场景所需渠道一致，复测自主候选三类校验及场景闭环"])
print("recorded TC-039.S1/S2, two rules and DEF-S3-034/035")
