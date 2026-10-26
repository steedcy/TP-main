"""Record TC-037.S1 from the current Chrome task-detail render and task 55 API data."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
ui = json.loads((stage / "evidence/TC-037-candidate-plan-ui.json").read_text(encoding="utf-8"))
plan_run = json.loads((stage / "evidence/TC-039-plan-six-fields-20261026T042249Z.json").read_text(
    encoding="utf-8"))
candidate = plan_run["cases"][0]["plans"][0]
assert ui["route"] == "/tasks/55" and ui["taskId"] == plan_run["cases"][0]["afterMaxTaskId"]
assert ui["versionTabs"] == ["版本1（自主规划）", "版本2（基线模板）"]
assert len(ui["candidateRows"]) == len(candidate["planSteps"]) == 4
assert candidate["source"] == "AUTONOMOUS" and candidate["frozenAt"]
assert all(step.get("inputParams") for step in candidate["planSteps"])
assert ui["candidateHeaders"] == ["步骤", "步骤目标", "所需能力", "前置条件", "完成条件", "失败处理"]
assert ui["visibleLabels"]["任务目标"] and ui["visibleLabels"]["规划依据（上下文快照）"]
assert ui["visibleLabels"]["冻结时间"]
assert not any(label in ui["candidateHeaders"] for label in [
    "输入参数", "候选设备", "关键参数来源", "规划说明", "可执行步骤数", "剩余额度"])
assert all(not ui["visibleLabels"][label] for label in [
    "输入参数", "关键参数来源", "规划说明", "可执行步骤数", "剩余额度"])
refs = ";".join("acceptance/stage3/evidence/" + n for n in [
    "TC-037-candidate-plan-ui.json", "TC-037-candidate-plan-task55.png",
    "TC-039-plan-six-fields-20261026T042249Z.json"])
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

update("steps.csv", "stepId", {"TC-037.S1": {
    "status": "F", "observedAt": day,
    "actual": "任务55自主候选四步、目标、六项中的五项表格字段、快照与冻结时间可见；API步骤含inputParams，但页面候选表不展示输入参数，也缺逐步候选设备、关键参数来源、规划说明、可执行步骤数和剩余额度",
    "evidence": refs, "issue": "DEF-S3-036"}})
issues = stage / "issues.csv"
with issues.open(encoding="utf-8-sig", newline="") as stream:
    assert "DEF-S3-036" not in {row["编号"] for row in csv.DictReader(stream)}
with issues.open("a", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["DEF-S3-036", "缺陷", "中", "TC-037.S1", "", "待修复",
                     "Chrome任务55详情自主计划四步表格只显示步骤、目标、能力、前置、完成和失败处理；API已保存的inputParams未展示，逐步候选设备/参数来源、规划说明、可执行步骤数与剩余额度也未提供",
                     refs,
                     "阶段4补全自主候选计划详情字段与来源、候选设备、步骤数和剩余额度；对照API及界面实测新旧计划版本"])
print("recorded TC-037.S1 and DEF-S3-036")
