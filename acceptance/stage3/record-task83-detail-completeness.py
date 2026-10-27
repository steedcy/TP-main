"""Classify TC-063.S2 using live UI/API and the preserved pending-manual snapshot."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
ui_name = "TC-063-task-detail-fields-task83.json"
api_name = "TC-063-task83-detail-api-20261027T054857Z.json"
pending_name = "TC-050-baseline-failure-20261027T042130Z.json"
cadence_name = "SRS_F020-R09-refresh-live-20261026T214810Z.json"
ui = json.loads((stage / "evidence" / ui_name).read_text(encoding="utf-8"))
api = json.loads((stage / "evidence" / api_name).read_text(encoding="utf-8"))
pending = json.loads((stage / "evidence" / pending_name).read_text(encoding="utf-8"))
cadence = json.loads((stage / "evidence" / cadence_name).read_text(encoding="utf-8"))
assert ui["runtimeInput"] == api["runtimeInput"] == pending["runtimeInput"] == "V1.5"
assert ui["taskId"] == api["task"]["id"] == pending["task"]["id"] == 83
assert pending["task"]["status"] == "PENDING_MANUAL"
assert api["task"]["status"] == "MANUAL_TERMINATED"
assert ui["timelineItemCount"] == len(api["events"]) == len(pending["events"]) + 1 == 30
assert api["task"]["taskGoal"] == pending["request"]["taskGoal"]
assert api["task"]["taskGoal"] in ui["header"]
assert len(ui["planTabs"]) == len(api["planVersions"]) == 2
assert len(api["assignments"]) == 4
timeline = ui["cards"][-1]["text"]
for event in api["events"]:
    assert event["occurredAt"] in timeline and event["eventType"] in timeline
assert api["events"][-1]["eventType"] == "MANUAL_TERMINATED"
assert not any(event["eventType"] in ("TASK_PENDING_MANUAL", "TASK_MANUAL_REQUIRED")
               for event in api["events"])
assert any(event["eventType"] == "REPLAN_FAILED" for event in api["events"])
assert any(event["eventType"] == "EXCEPTION_RECOVERED" for event in api["events"])
assert cadence["runtimeInput"] == "V1.5"
refs = ";".join("acceptance/stage3/evidence/" + name for name in
                (ui_name, ui["screenshot"], api_name, pending_name, cadence_name))

steps_file = stage / "steps.csv"
with steps_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(item for item in rows if item["stepId"] == "TC-063.S2")
assert row["status"] == "NOT_RUN"
row.update(status="F", observedAt=datetime.now().strftime("%Y-%m-%d"),
           actual=("V1.5任务83的Chrome详情展示原目标、两版计划、设备分配进度与30条只读时间线，"
                   "页面事件时间/类型与同期API 30条对应；另有任务67执行中约10秒刷新独立证据。"
                   "但任务83原始API已进入PENDING_MANUAL时，时间线只有REPLAN_FAILED后错误的EXCEPTION_RECOVERED，"
                   "没有待人工状态转换事件；其后人工终止才追加MANUAL_TERMINATED。时间线无法完整还原关键状态，整步判F。"
                   "未以任务67的刷新样本代替任务83的其他场景覆盖。"),
           evidence=refs, issue="DEF-S3-066")
with steps_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

issues_file = stage / "issues.csv"
with issues_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(item for item in rows if item["编号"] == "DEF-S3-066")
assert "TC-063.S2" not in row["关联用例步骤"]
row["关联用例步骤"] += ";TC-063.S2"
row["事实"] += (" V1.5 Chrome任务83详情与API均展示30条事件，仍无进入PENDING_MANUAL的转换记录；"
                "原始任务当时确为PENDING_MANUAL，人工终止后只追加MANUAL_TERMINATED。")
row["证据"] += ";" + refs
with issues_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
old = "原 200 步：P 46、F 65、NT 19、未执行 70"
assert old in body
body = body.replace(old, "原 200 步：P 46、F 66、NT 19、未执行 69", 1)
note = ("- TC-063.S2：Chrome任务83的原目标、两版计划、设备分配与30条事件在详情可见，页面时间/类型与本轮API一致；"
        "任务67已有执行中约10秒自动刷新独立证据。但任务83曾实际进入PENDING_MANUAL，"
        "时间线在REPLAN_FAILED后反而写EXCEPTION_RECOVERED，且无待人工状态转换，人工终止才追加第30条。"
        "完整状态时间线未满足，按`DEF-S3-066`判F；该用例其他分支不能据此算通过。见`evidence/TC-063-task83-*`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 13:46（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded TC-063.S2 F using DEF-S3-066")
