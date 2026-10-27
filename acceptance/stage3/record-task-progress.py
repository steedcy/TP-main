"""Record TC-054.S2's missing progress display and SRS_F017.R09 completion."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
ui_name = "TC-054-progress-ui-20261027T055114Z.json"
api_name = "TC-054-progress-api-20261027T055135Z.json"
ui = json.loads((stage / "evidence" / ui_name).read_text(encoding="utf-8"))
api = json.loads((stage / "evidence" / api_name).read_text(encoding="utf-8"))
assert ui["runtimeInput"] == api["runtimeInput"] == "V1.5"
assert ui["taskId"] == api["task"]["id"] == 19
assert api["task"]["status"] == "COMPLETED" and "已完成" in ui["detailHeader"]
assert not ui["listProgressColumn"] and not ui["detailProgressLabel"]
assert len(ui["assignmentRows"]) == len(api["assignments"]) == len(api["currentPlan"]["planSteps"]) == 4
assert [a["stepSeq"] for a in api["assignments"]] == [1, 2, 3, 4]
assert all(a["stepStatus"] == "COMPLETED" and a["executionResult"] == "SUCCESS"
           for a in api["assignments"])
for step, assignment in zip(api["currentPlan"]["planSteps"], api["assignments"]):
    key, expected = step["completionCondition"].split("=", 1)
    actual = assignment["outputParams"][key]
    assert str(actual).lower() == expected.lower()
events = api["events"]
assert sum(event["eventType"] == "STEP_COMPLETED" for event in events) == 4
assert events[-1]["eventType"] == "TASK_COMPLETED"
assert all(event["occurredAt"] < events[-1]["occurredAt"] for event in events
           if event["eventType"] == "STEP_COMPLETED")
refs = ";".join("acceptance/stage3/evidence/" + name for name in
                (ui_name, api_name, ui["listScreenshot"], ui["detailScreenshot"]))


def update_csv(name, key, value, update):
    path = stage / name
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    row = next(item for item in rows if item[key] == value)
    update(row)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def update_step(row):
    assert row["status"] == "NOT_RUN"
    row.update(status="F", observedAt=datetime.now().strftime("%Y-%m-%d"),
               actual=("V1.5真实任务19当前基线四步计划的四项完成条件与设备成功反馈逐项匹配，"
                       "API四条STEP_COMPLETED先于TASK_COMPLETED，任务最终COMPLETED。"
                       "Chrome详情列出四行已完成及只读时间线，但任务列表无进度列，详情也无完成数/总数或当前步指标；"
                       "不能仅凭四行状态代替要求的明确进度显示，故整步判F。九状态全路径仍需独立覆盖。"),
               evidence=refs, issue="DEF-S3-068")


def update_rule(row):
    assert row["status"] == "NOT_RUN"
    row.update(status="P", verifiedBy="TC-054.S2", evidence=refs)


update_csv("steps.csv", "stepId", "TC-054.S2", update_step)
update_csv("rules.csv", "ruleId", "SRS_F017.R09", update_rule)
issues_file = stage / "issues.csv"
with issues_file.open(encoding="utf-8-sig", newline="") as stream:
    assert "DEF-S3-068" not in {item["编号"] for item in csv.DictReader(stream)}
with issues_file.open("a", encoding="utf-8", newline="") as stream:
    csv.writer(stream, lineterminator="\n").writerow([
        "DEF-S3-068", "缺陷", "中", "TC-054.S2", "SRS_F017.R01", "待修复",
        "真实完成任务19的四步均满足完成条件、任务最终COMPLETED；Chrome任务列表无进度列，详情仅有四行步骤状态，未呈现完成数/总数和当前步的明确进度指标。",
        refs,
        "在任务列表或详情明确显示完成数/总数及当前步，执行中和结束后均验证；回归九状态流转与时间线。"])

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
old_steps = "原 200 步：P 46、F 66、NT 19、未执行 69"
old_rules = "281 条需求规则为 P 102、F 48、NT 11、未执行 120"
assert old_steps in body and old_rules in body
body = body.replace(old_steps, "原 200 步：P 46、F 67、NT 19、未执行 68", 1)
body = body.replace(old_rules, "281 条需求规则为 P 103、F 48、NT 11、未执行 119", 1)
note = ("- TC-054.S2与`SRS_F017.R09`：任务19的四个计划完成条件与四次实际设备反馈逐一匹配，"
        "四条STEP_COMPLETED后才有TASK_COMPLETED，任务最终COMPLETED，R09判P。"
        "Chrome任务列表无进度列、详情无完成数/总数和当前步指标，尽管四行步骤显示已完成，整步按`DEF-S3-068`判F；"
        "九状态完整流转仍需分别测。见`evidence/TC-054-progress-*`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 13:49（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded TC-054.S2 F / SRS_F017.R09 P")
