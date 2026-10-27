"""Classify SRS_F017.R08 from the Stage3 two-step delayed dry-run."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
run_name = "TC-054-two-step-receipt-order-20261027T055732Z.json"
ui_name = "TC-054-two-step-order-ui-20261027T055812Z.json"
run = json.loads((stage / "evidence" / run_name).read_text(encoding="utf-8"))
ui = json.loads((stage / "evidence" / ui_name).read_text(encoding="utf-8"))
assert run["runtimeInput"] == ui["runtimeInput"] == "V1.5"
assert run["started"]["taskId"] == ui["taskId"] == 85
first, second, finished = (run[key] for key in ("step1Received", "step2Received", "finished"))
assert first["task"]["status"] == second["task"]["status"] == "EXECUTING"
assert [a["stepStatus"] for a in first["assignments"]] == ["EXECUTING", "PENDING_ASSIGNMENT"]
assert [a["executionResult"] for a in first["assignments"]] == [None, None]
assert not any(c["stepSeq"] == 2 for c in first["commands"])
assert "STEP_COMPLETED" not in [e["eventType"] for e in first["events"]]
assert [a["stepStatus"] for a in second["assignments"]] == ["COMPLETED", "EXECUTING"]
assert second["assignments"][0]["outputParams"]["displayStatus"] == "SUCCESS"
step2_commands = [c for c in second["commands"] if c["stepSeq"] == 2]
assert {c["commandType"] for c in step2_commands} == {"TASK_ACCEPT", "EXECUTE_CAPABILITY"}
ids = {c["commandId"] for c in second["commands"]}
assert len(ids) == 2
types = [e["eventType"] for e in second["events"]]
assert types.index("STEP_COMPLETED") < len(types) - 1
assert types.count("STEP_DISPATCHED") == 2
assert types.index("STEP_COMPLETED") < [i for i, kind in enumerate(types)
                                         if kind == "STEP_DISPATCHED"][1]
assert finished["task"]["status"] == "COMPLETED"
assert [a["stepStatus"] for a in finished["assignments"]] == ["COMPLETED", "COMPLETED"]
assert all(a["outputParams"]["displayStatus"] == "SUCCESS" for a in finished["assignments"])
assert [e["eventType"] for e in finished["events"]][-2:] == ["TASK_COMPLETED", "DRY_RUN_SUCCEEDED"]
assert len(ui["stepRows"]) == 2 and len(ui["timeline"]) == len(finished["events"]) == 13
assert all("CMD-" in row and "SUCCESS" in row for row in ui["stepRows"])
assert all("2026-10-27T" in row for row in ui["stepRows"])
assert run["restore"]["delayMs"] == 1000
assert run["restore"]["templateStatus"] == "DISABLED" and run["restore"]["templateStepsMatch"]
assert run["restore"]["allSixOnlineIdle"]
refs = ";".join("acceptance/stage3/evidence/" + name for name in
                (run_name, ui_name, ui["screenshot"]))

rules_file = stage / "rules.csv"
with rules_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(item for item in rows if item["ruleId"] == "SRS_F017.R08")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-054.S1", evidence=refs)
with rules_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
old = "281 条需求规则为 P 104、F 49、NT 11、未执行 117"
assert old in body
body = body.replace(old, "281 条需求规则为 P 105、F 49、NT 11、未执行 116", 1)
note = ("- `SRS_F017.R08`：V1.5任务85双步试运行使用同一仿真航显，执行反馈延迟12秒。"
        "第一步已承接并收到指令时仍EXECUTING，第二步PENDING_ASSIGNMENT且没有任何下发命令；"
        "第一步回报`displayStatus=SUCCESS`并记STEP_COMPLETED后才发第二步的独立指令号，最终两步完成，"
        "Chrome行与13条事件时间线对应。顺序规则判P。模板步骤已恢复原单步、停用，延迟1000ms、六代理空闲。"
        "TC-054.S1还要求监督通过的正式任务和指定反馈分支，此双步试运行不足以完成整步，维持未执行。"
        "证据见`evidence/TC-054-two-step-*`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 13:55（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded SRS_F017.R08 P; TC-054.S1 remains NOT_RUN")
