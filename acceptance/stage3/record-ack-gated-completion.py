"""Classify the receipt-vs-completion rule from the Stage3 delayed dry-run."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
name = "SRS_F017-R07-ack-gated-20261027T055541Z.json"
ev = json.loads((stage / "evidence" / name).read_text(encoding="utf-8"))
assert ev["runtimeInput"] == "V1.5" and ev["started"]["taskId"] == 84
assert ev["delayDuringMs"] == 20000
before = ev["receivedCommands"]
assert {row["commandType"] for row in before} == {"TASK_ACCEPT", "EXECUTE_CAPABILITY"}
assert len({row["commandId"] for row in before}) == 1
assert next(row for row in before if row["commandType"] == "TASK_ACCEPT")["commandStatus"] == "ACCEPTED"
assert ev["taskAtReceipt"]["status"] == "EXECUTING"
assert len(ev["assignmentsAtReceipt"]) == 1
assert ev["assignmentsAtReceipt"][0]["stepStatus"] == "EXECUTING"
assert ev["assignmentsAtReceipt"][0]["executionResult"] is None
assert ev["assignmentsAtReceipt"][0]["outputParams"] is None
assert "STEP_COMPLETED" not in [row["eventType"] for row in ev["eventsAtReceipt"]]
assert ev["taskAfterFeedback"]["status"] == "COMPLETED"
assert len(ev["assignmentsAfterFeedback"]) == 1
final = ev["assignmentsAfterFeedback"][0]
assert final["stepStatus"] == "COMPLETED" and final["executionResult"] == "SUCCESS"
assert final["outputParams"]["displayStatus"] == "SUCCESS"
types = [row["eventType"] for row in ev["eventsAfterFeedback"]]
assert types.index("EXECUTION_FEEDBACK_RECEIVED") < types.index("STEP_COMPLETED") < types.index("TASK_COMPLETED")
assert ev["restore"]["delayMs"] == 1000 and ev["restore"]["templateStatus"] == "DISABLED"
assert ev["restore"]["allSixOnlineIdle"]
ref = "acceptance/stage3/evidence/" + name

rules_file = stage / "rules.csv"
with rules_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(item for item in rows if item["ruleId"] == "SRS_F017.R07")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-054.S1", evidence=ref)
with rules_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
old = "281 条需求规则为 P 103、F 49、NT 11、未执行 118"
assert old in body
body = body.replace(old, "281 条需求规则为 P 104、F 49、NT 11、未执行 117", 1)
note = ("- `SRS_F017.R07`：本轮V1.5任务84试运行将仿真航显执行延迟20秒。"
        "同一指令号的TASK_ACCEPT已ACCEPTED、EXECUTE_CAPABILITY已SENT时，任务仍EXECUTING、步骤仍EXECUTING，"
        "无执行结果或STEP_COMPLETED；随后设备回报`displayStatus=SUCCESS`，才依次出现反馈、步骤完成和任务完成。"
        "规则“收到不等于完成”判P。单步试运行未覆盖TC-054.S1要求的多步前置顺序，该整步维持未执行。"
        "延迟恢复1000ms、模板停用、六代理在线空闲，见`evidence/SRS_F017-R07-ack-gated-20261027T055541Z.json`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 13:54（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded SRS_F017.R07 P; TC-054.S1 remains NOT_RUN")
