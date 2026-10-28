"""Score TC-041.S1 after the non-exempt no-candidate branch is measured."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
names = ["TC-041-capability-validation-unknown-capability-20261027T062908Z.json",
         "TC-041-capability-validation-oversize-no-online-candidate-20261028T013211Z.json",
         "TC-041-plan-ui-task90-20261028T013509Z.json",
         "TC-041-no-candidate-plan-ui-20261028T013453Z.json",
         "TC-020-022-capability-create.json"]
unknown, absent, unknown_ui, absent_ui, type_boundary = [
    json.loads((stage / "evidence" / n).read_text(encoding="utf-8")) for n in names]
assert unknown["runtimeInput"] == absent["runtimeInput"] == "V1.5"
assert unknown["submitted"]["id"] == 90 and absent["submitted"]["id"] == 94
assert unknown["finished"]["plans"][0]["capabilityCheckResult"] == "FAIL"
assert any(x["stepSeq"] == 2 and x["reasonCode"] == "ERR_CAPABILITY_GAP"
           for x in unknown["finished"]["plans"][0]["validationErrors"])
assert set(absent["disabledAgents"]) == {"SIM_F2_BAGGAGE", "SIM_F2_BAGGAGE_B"}
assert all(x["agentStatus"] == "DISABLED" and x["onlineStatus"] == "OFFLINE"
           for x in absent["disabledAgents"].values())
assert absent["finished"]["task"]["taskFamily"] == "OVERSIZE_BAGGAGE_HANDLING"
assert absent["finished"]["task"]["status"] == "PENDING_MANUAL"
assert len(absent["finished"]["assignments"]) == 0
assert not any(x["eventType"] in ("SUPERVISION_JUDGED", "STEP_DISPATCHED")
               for x in absent["finished"]["events"])
assert all(p["capabilityCheckResult"] == "FAIL" for p in absent["finished"]["plans"])
assert all({2, 3}.issubset({x["stepSeq"] for x in p["validationErrors"]
                          if x["reasonCode"] == "ERR_NO_ONLINE_CANDIDATE"})
           for p in absent["finished"]["plans"])
assert absent["restore"]["cleanup"] == "MANUAL_TERMINATED"
assert absent["restore"]["fixtureModeExact"] and absent["restore"]["moonshotExitCode"] == 0
assert absent["restore"]["fixtureStopped"] and absent["restore"]["sixOnlineIdle"]
assert unknown_ui["taskId"] == 90 and "ERR_CAPABILITY_GAP" in unknown_ui["candidateDetail"]
assert absent_ui["taskId"] == 94 and absent_ui["candidateDetail"].count("ERR_NO_ONLINE_CANDIDATE") == 2
assert absent_ui["baselineDetail"].count("ERR_NO_ONLINE_CANDIDATE") == 2
assert type_boundary["invalid"]["outOfBoundary"]["httpStatus"] == 400
refs = ";".join("acceptance/stage3/evidence/" + n for n in names)

steps = stage / "steps.csv"
with steps.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
item = next(x for x in rows if x["stepId"] == "TC-041.S1")
assert item["status"] == "NOT_RUN"
item.update(status="P", observedAt=datetime.now().strftime("%Y-%m-%d"),
            actual=("任务90无效能力在V1.5能力校验FAIL，步骤2及ERR_CAPABILITY_GAP在Chrome可见；"
                    "任务94为不适用航班部分渠道例外的超规行李，两个行李代理停用/离线后自主与基线"
                    "能力校验均FAIL，步骤2/3列ERR_NO_ONLINE_CANDIDATE；未进入监督、未分配/下发，"
                    "转待人工。设备类型越界能力配置另有本轮HTTP400证据，六代理均恢复。"),
            evidence=refs, issue="")
with steps.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

rules = stage / "rules.csv"
with rules.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
item = next(x for x in rows if x["ruleId"] == "SRS_F013.R02")
assert item["status"] == "NOT_RUN"
item.update(status="P", verifiedBy="TC-041.S1", evidence=refs, issue="")
with rules.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
assert "原 200 步：P 48、F 67、NT 19、未执行 66" in body
assert "281 条需求规则为 P 106、F 51、NT 11、未执行 113" in body
body = body.replace("原 200 步：P 48、F 67、NT 19、未执行 66",
                    "原 200 步：P 49、F 67、NT 19、未执行 65", 1)
body = body.replace("281 条需求规则为 P 106、F 51、NT 11、未执行 113",
                    "281 条需求规则为 P 107、F 51、NT 11、未执行 112", 1)
note = ("- TC-041.S1与`SRS_F013.R02`：先用任务90验证无效能力在V1.5产生步骤2能力缺口及原因码；"
        "再以不适用航班部分渠道例外的超规行李任务94验证无在线候选：两台行李代理停用后，"
        "自主和基线计划均能力FAIL，步骤2/3的`ERR_NO_ONLINE_CANDIDATE`在API和Chrome错误清单可见，"
        "没有监督、分配或下发，转待人工。类型越界配置的HTTP400证据来自同轮TC-020；"
        "本步及能力校验规则判P。任务94取证后人工终止，环境恢复六代理在线空闲；"
        "TC-041.S2/S3及资源/安全分支仍须独立复测。见`evidence/TC-041-*`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-28 09:30（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded TC-041.S1 and SRS_F013.R02 P")
