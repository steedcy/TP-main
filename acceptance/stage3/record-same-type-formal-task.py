"""Record TC-093.S2 after a formal business task used the new device agent."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
name = "TC-093-same-type-formal-task-20261027T062013Z.json"
ev = json.loads((stage / "evidence" / name).read_text(encoding="utf-8"))
assert ev["runtimeInput"] == "V1.5" and ev["isolatedSchema"] == "tip_stage2_v14"
assert ev["sourceTaskId"] == 19 and ev["task"]["id"] == 89
assert ev["task"]["taskFamily"] == "OVERSIZE_BAGGAGE_HANDLING"
assert ev["task"]["status"] == "COMPLETED"
assert ev["newDevice"]["deviceCode"] == "S3_TC093_DISPLAY_D"
assert ev["connectionTest"]["result"] == "PASSED"
assert ev["capabilityEnabled"]["capabilityType"] == "CAP_INFO_DISPLAY"
assert ev["capabilityEnabled"]["capabilityStatus"] == "ENABLED"
assert ev["newAgentOnline"]["onlineStatus"] == "ONLINE"
assert ev["existingDisplayDisabled"]["agentStatus"] == "DISABLED"
assert ev["newAgentBeforeTask"]["workStatus"] == "IDLE"
assert any(p["source"] == "BASELINE_TEMPLATE" and all(p[k] == "PASS" for k in
           ("structureCheckResult", "capabilityCheckResult", "constraintCheckResult"))
           for p in ev["plans"])
assignments = ev["assignments"]
assert len(assignments) == 4 and all(x["stepStatus"] == "COMPLETED" for x in assignments)
display = next(x for x in assignments if x["deviceAgentCode"] == ev["newAgent"]["agentId"])
assert display["stepSeq"] == 4 and display["executionResult"] == "SUCCESS"
assert display["outputParams"]["displayStatus"] == "SUCCESS"
assert {x["commandType"]: x["commandStatus"] for x in ev["newDeviceCommands"]} == {
    "TASK_ACCEPT": "ACCEPTED", "EXECUTE_CAPABILITY": "SUCCEEDED"}
assert {"AGENT_ASSIGNED", "STEP_DISPATCHED", "EXECUTION_FEEDBACK_RECEIVED",
        "STEP_COMPLETED", "TASK_COMPLETED"}.issubset({x["eventType"] for x in ev["events"]})
assert ev["cleanup"]["newDeviceStatus"] == "DELETED"
assert ev["cleanup"]["simulatorStopped"] and ev["cleanup"]["originalSixOnlineIdle"]
ref = "acceptance/stage3/evidence/" + name

target = stage / "steps.csv"
with target.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(x for x in rows if x["stepId"] == "TC-093.S2")
assert row["status"] == "NOT_RUN"
row.update(status="P", observedAt=datetime.now().strftime("%Y-%m-%d"),
           actual=("正式提交超规行李任务89，原航显代理已停用，新建同类航显代理ONLINE且能力ENABLED；"
                   "自主候选能力校验失败后基线V2三类校验PASS，四步全部完成，其中信息发布步4由新代理承接，"
                   "TASK_ACCEPT与EXECUTE_CAPABILITY分别ACCEPTED/SUCCEEDED，反馈displayStatus=SUCCESS，"
                   "步骤完成和任务完成事件落库。旧代理恢复、新设备软删、六原代理在线空闲。"
                   "此结果只证明同类设备正式任务调用，不把降级原因判为通过。"), evidence=ref)
prior = next(x for x in rows if x["stepId"] == "TC-093.S1")
assert prior["status"] == "P" and "该步仍未执行" in prior["actual"]
prior["actual"] = prior["actual"].replace(
    "试运行不替代TC-093.S2要求的正式任务，该步仍未执行。",
    "试运行仅支持S1；TC-093.S2另以正式任务89完成。")
with target.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
assert "原 200 步：P 47、F 67、NT 19、未执行 67" in body
body = body.replace("原 200 步：P 47、F 67、NT 19、未执行 67",
                    "原 200 步：P 48、F 67、NT 19、未执行 66", 1)
body = body.replace("TC-093.S2要求正式已有任务调用，试运行不代替该步骤，保持未执行。",
                    "该试运行仅用于S1；S2已随后用正式任务89另行复测。", 1)
note = ("- TC-093.S2：正式超规行李任务89沿既有业务提交入口进入，原航显代理在空闲时临时停用，"
        "新同类航显在线且CAP_INFO_DISPLAY经测试启用。自主候选能力校验失败并降级，基线V2三类校验PASS；"
        "四步均完成，信息发布步4明确分配给新代理，两类真实指令ACCEPTED/SUCCEEDED，反馈SUCCESS，"
        "步骤/任务完成事件留存。步骤按新设备真实承接判P；不将自主候选失败当作通过。"
        "清理后原代理恢复、临时设备软删、六原代理在线空闲。见`evidence/TC-093-same-type-formal-task-*`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 14:09（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded TC-093.S2 P")
