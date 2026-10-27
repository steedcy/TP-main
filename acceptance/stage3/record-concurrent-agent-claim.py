"""Record TC-052.S1 from a live two-step overlap and persistent command order."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
first_file = stage / "evidence/TC-052-concurrent-claim-20261027T040409Z.json"
follow_file = stage / "evidence/TC-052-concurrent-followup-20261027T040459Z.json"
first = json.loads(first_file.read_text(encoding="utf-8"))
follow = json.loads(follow_file.read_text(encoding="utf-8"))
assert first["runtimeInput"] == follow["runtimeInput"] == "V1.5"
assert first["isolatedSchema"] == follow["isolatedSchema"] == "tip_stage2_v14"
assert first["first"]["agentAtBusy"]["workStatus"] == "BUSY"
assert first["first"]["agentAtBusy"]["currentTaskId"] == first["first"]["start"]["taskId"]
assert first["sameAgentError"].startswith("HTTP 400:")
assert first["taskCountAfterSecond"] == first["taskCountBeforeSecond"]
assert first["agentAfterSecond"]["currentTaskId"] == first["first"]["start"]["taskId"]
assert first["first"]["commandsAtBusy"] == first["first"]["commandsAfterSecond"]
assert sum("|TASK_ACCEPT|" in r for r in first["first"]["commandsAtBusy"]) == 1
assert sum("|EXECUTE_CAPABILITY|" in r for r in first["first"]["commandsAtBusy"]) == 1
task = follow["tasks"][str(first["first"]["start"]["taskId"])]
events = [e["eventType"] for e in task["events"]]
assert events.index("AGENT_ASSIGNMENT_REQUESTED") < events.index("AGENT_ASSIGNED") < events.index("STEP_DISPATCHED")
assert follow["template"]["templateStatus"] == "DISABLED"
assert len(follow["agents"]) == 6 and all(a["agentStatus"] == "ENABLED" and
       a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE" and
       a["currentTaskId"] is None for a in follow["agents"])
assert first["restore"]["delayMs"] == 1000
refs = ";".join("acceptance/stage3/evidence/" + p.name for p in (first_file, follow_file))

for filename, key, value in (("steps.csv", "stepId", "TC-052.S1"),
                             ("rules.csv", "ruleId", "SRS_F016.R02")):
    target = stage / filename
    with target.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    row = next(r for r in rows if r[key] == value)
    assert row["status"] == "NOT_RUN"
    row["status"] = "P"
    row["evidence"] = refs
    if filename == "steps.csv":
        row["observedAt"] = datetime.now().strftime("%Y-%m-%d")
        row["actual"] = ("任务78的步骤1绑定SIM_F2_DISPLAY并处于BUSY时，再以相同代理请求另一试运行步骤返回HTTP400；"
                         "任务总数不变、占用仍属78、命令数不变。任务78事件按分配请求→承接→步骤下发排序；"
                         "命令记录一条TASK_ACCEPT和随后一条EXECUTE_CAPABILITY。独立尝试的SIM_F2_FLIGHT"
                         "因任务族物理通道不匹配而无候选，未把它视为可替代显示设备。测试结束模板停用、延时恢复、六代理空闲。")
    else:
        row["verifiedBy"] = "TC-052.S1"
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
assert "原 200 步：P 43、F 62、NT 19、未执行 76" in body
assert "281 条需求规则为 P 93、F 44、NT 11、未执行 133" in body
body = body.replace("原 200 步：P 43、F 62、NT 19、未执行 76",
                    "原 200 步：P 44、F 62、NT 19、未执行 75", 1)
body = body.replace("281 条需求规则为 P 93、F 44、NT 11、未执行 133",
                    "281 条需求规则为 P 94、F 44、NT 11、未执行 132", 1)
note = ("- TC-052.S1与`SRS_F016.R02`：两个同时请求同一仿真代理的试运行步骤中，"
        "首任务78占用SIM_F2_DISPLAY，第二请求HTTP400且没有创建任务、没有增加命令；"
        "事件顺序是分配请求、承接、业务下发。额外选SIM_F2_FLIGHT被物理通道约束拒绝，"
        "不算有效备用设备。结束后模板、延时及六代理恢复，判P。见`evidence/TC-052-concurrent-*`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 12:02（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded TC-052.S1 P and SRS_F016.R02 P")
