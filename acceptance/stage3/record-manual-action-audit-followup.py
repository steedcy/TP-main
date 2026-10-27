"""Record the task-20 manual-action audit and cross-trace observations."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
ev = stage / "evidence"
api_file = ev / "SRS_F028-manual-action-followup-20261027T004818Z.json"
ui_file = ev / "TC-064-mark-failed-task20-ui.json"
trace_file = ev / "SRS_F028-R08-task20-cross-trace-ui.json"
api = json.loads(api_file.read_text(encoding="utf-8"))
ui = json.loads(ui_file.read_text(encoding="utf-8"))
trace = json.loads(trace_file.read_text(encoding="utf-8"))
assert api["runtimeInput"] == ui["runtimeInput"] == trace["runtimeInput"] == "V1.5"
assert api["isolatedSchema"] == "tip_stage2_v14"
assert api["taskId"] == ui["taskId"] == trace["taskId"] == 20
assert api["task"]["status"] == ui["actionResultStatus"] == "FAILED"
assert ui["beforeStatus"] == "待人工处理" and ui["actionHttpStatus"] == 200
assert ui["afterStatus"] == "失败" and ui["afterActionCount"] == 0
audit = api["audit"]["TASK_MANUAL_ACTION"]
assert len(audit) == 1
row = audit[0]
assert row["username"] == "oprator" and row["operationResult"] == "SUCCESS"
assert row["operationTarget"] == api["task"]["taskCode"] + " -> MARK_FAILED"
assert row["createdAt"] and row["detail"] is None
assert api["audit"]["TASK_DEFINITION_UPDATE"] and api["audit"]["RISK_RULE_CHANGE"]
assert api["events"][-1]["eventType"] == "TASK_FAILED"
assert api["events"][-1]["reasonCode"] is None
assert api["events"][-1]["detailSummary"] == api["task"]["failureReason"]
assert "MARK_FAILED" in trace["audit"]["rowText"]
assert "未附带详情" in trace["audit"]["modalText"]
assert api["task"]["taskCode"] in trace["audit"]["rowText"]
assert api["task"]["taskCode"] in trace["trace"]["taskRowText"]
assert trace["trace"]["failedEvents"]

rule_file = stage / "rules.csv"
with rule_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rules = reader.fieldnames, list(reader)
targets = {r["ruleId"]: r for r in rules if r["ruleId"] in
           {"SRS_F020.R08", "SRS_F028.R02", "SRS_F028.R08"}}
assert set(targets) == {"SRS_F020.R08", "SRS_F028.R02", "SRS_F028.R08"}
assert all(r["status"] == "NOT_RUN" for r in targets.values())
base = "acceptance/stage3/evidence/"
targets["SRS_F020.R08"].update(
    status="F", verifiedBy="TC-064.S2",
    evidence=";".join(base + f.name for f in (ui_file, api_file, trace_file)),
    issue="DEF-S3-062")
targets["SRS_F028.R02"].update(
    status="P", verifiedBy="TC-085.S1", evidence=base + api_file.name, issue="")
targets["SRS_F028.R08"].update(
    status="P", verifiedBy="TC-085.S1", evidence=base + trace_file.name, issue="")
with rule_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rules)

issue_file = stage / "issues.csv"
with issue_file.open(encoding="utf-8-sig", newline="") as stream:
    assert "DEF-S3-062" not in {r["编号"] for r in csv.DictReader(stream)}
with issue_file.open("a", encoding="utf-8", newline="") as stream:
    csv.writer(stream, lineterminator="\n").writerow([
        "DEF-S3-062", "缺陷", "中", "TC-064.S2", "SRS_F020.R08", "待修复",
        "任务20从待人工处理经操作员置为失败并成功留有操作者、时间、结果；但TASK_MANUAL_ACTION操作记录detail为空，页面详情显示未附带详情，TASK_FAILED事件reasonCode为空，仅有通用的手动置失败叙述，未记录本次处置原因。",
        ";".join(base + f.name for f in (ui_file, api_file, trace_file)),
        "人工处置时采集并持久化具体原因，在操作记录详情和任务事件中可追溯；复测四种处置与权限、结果。"])

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
old = "281 条需求规则为 P 90、F 39、NT 10、未执行 142"
new = "281 条需求规则为 P 92、F 40、NT 10、未执行 139"
assert old in body
body = body.replace(old, new, 1)
heading = "## 已执行\n\n"
assert heading in body
note = ("- TC-064.S2的`MARK_FAILED`分支：Chrome运行操作员对独立待人工任务20点击置为失败，"
        "HTTP200且任务转FAILED，按钮消失；操作日志有`TASK_MANUAL_ACTION/SUCCESS`，时间线有"
        "`TASK_FAILED`。转基线、重试规划及终止三个独立分支未执行，整步保持NOT_RUN。"
        "操作日志`detail=null`且页面提示未附详情，失败事件仅有通用叙述且`reasonCode=null`，"
        "没有本次处置的具体原因；`SRS_F020.R08`判F并登记`DEF-S3-062`。同轮读取任务定义"
        "变更、风险规则变更与人工处置三类审计，`SRS_F028.R02`判P；系统管理员日志与运行操作员"
        "时间线均以`TASK-20261025-0020`对应，`SRS_F028.R08`判P。任务68的尝试自然完成，"
        "未发生人工处置，原始尝试证据保留。详见`evidence/TC-064-mark-failed-task20-ui.json`、"
        "`evidence/SRS_F028-manual-action-followup-20261027T004818Z.json`及"
        "`evidence/SRS_F028-R08-task20-cross-trace-ui.json`。\n")
body = body.replace(heading, heading + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 06:45（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded F020.R08 F; F028.R02/R08 P; TC-064.S2 unchanged")
