"""Classify SRS_F020.R01 from the saved V1.5 task 83 detail retest."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
ui_name = "TC-063-task-detail-fields-task83.json"
api_name = "TC-063-task83-detail-api-20261027T054857Z.json"
pending_name = "TC-050-baseline-failure-20261027T042130Z.json"
ui = json.loads((stage / "evidence" / ui_name).read_text(encoding="utf-8"))
api = json.loads((stage / "evidence" / api_name).read_text(encoding="utf-8"))
pending = json.loads((stage / "evidence" / pending_name).read_text(encoding="utf-8"))
assert api["task"]["taskGoal"] in ui["header"]
assert len(ui["planTabs"]) == 2 and len(api["assignments"]) == 4
assert {"目标理解结果", "计划版本与校验/判定结果", "步骤设备分配与执行情况"}.issubset(
    {card["title"] for card in ui["cards"]})
timeline = ui["cards"][-1]["text"]
assert "REPLANNING_TRIGGERED" in timeline and "REPLAN_FAILED" in timeline
assert "EXCEPTION_RECOVERED" in timeline and "MANUAL_TERMINATED" in timeline
assert pending["task"]["status"] == "PENDING_MANUAL"
assert not any(event["eventType"] in ("TASK_PENDING_MANUAL", "TASK_MANUAL_REQUIRED")
               for event in api["events"])
assert ui["timelineItemCount"] == len(api["events"]) == 30
refs = ";".join("acceptance/stage3/evidence/" + name for name in
                (ui_name, ui["screenshot"], api_name, pending_name))

rules_file = stage / "rules.csv"
with rules_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(item for item in rows if item["ruleId"] == "SRS_F020.R01")
assert row["status"] == "NOT_RUN"
row.update(status="F", verifiedBy="TC-063.S2", evidence=refs, issue="DEF-S3-066")
with rules_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

issues_file = stage / "issues.csv"
with issues_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(item for item in rows if item["编号"] == "DEF-S3-066")
assert "SRS_F020.R01" not in row["关联需求规则"]
row["关联需求规则"] += ";SRS_F020.R01"
with issues_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
old = "281 条需求规则为 P 103、F 48、NT 11、未执行 119"
assert old in body
body = body.replace(old, "281 条需求规则为 P 103、F 49、NT 11、未执行 118", 1)
note = ("- `SRS_F020.R01`：任务83详情已展示目标、解析、计划版本、设备分配与重规划事件，"
        "30条页面时间线与API存储一致；但原始任务明确进入PENDING_MANUAL后没有对应状态转移事件，"
        "反有REPLAN_FAILED后的EXCEPTION_RECOVERED，故完整事件时间线要求判F并关联`DEF-S3-066`。"
        "该判断不改变仅检验时间正序和不可编辑删除的`SRS_F020.R07`既有P。见`evidence/TC-063-task83-*`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 13:51（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded SRS_F020.R01 F")
