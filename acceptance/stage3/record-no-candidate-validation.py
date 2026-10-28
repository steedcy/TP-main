"""Record TC-041.S1 and the false-positive no-candidate validation defect."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
names = ["TC-041-capability-validation-unknown-capability-20261027T062908Z.json",
         "TC-041-capability-validation-no-online-candidate-20261027T063253Z.json",
         "TC-041-no-candidate-validation-followup-20261027T063555Z.json"]
unknown, missing, followup = [json.loads((stage / "evidence" / name).read_text(encoding="utf-8"))
                              for name in names]
assert all(x["runtimeInput"] == "V1.5" and x["isolatedSchema"] == "tip_stage2_v14"
           for x in (unknown, missing, followup))
assert unknown["submitted"]["id"] == 90 and missing["submitted"]["id"] == 91
first_plan = unknown["finished"]["plans"][0]
assert first_plan["source"] == "AUTONOMOUS"
assert first_plan["structureCheckResult"] == "PASS"
assert first_plan["capabilityCheckResult"] == "FAIL"
assert first_plan["constraintCheckResult"] == "FAIL"
assert any(x["reasonCode"] == "ERR_CAPABILITY_GAP" and x["stepSeq"] == 2
           for x in first_plan["validationErrors"])
assert first_plan["frozenAt"] is None
assert unknown["finished"]["plans"][1]["source"] == "BASELINE_TEMPLATE"
assert all(x["agentStatus"] == "DISABLED" and x["onlineStatus"] == "OFFLINE"
           for x in missing["disabledAgents"].values())
assert set(missing["disabledAgents"]) == {"SIM_F2_DISPLAY", "SIM_F2_FLIGHT"}
contexts = followup["contextSnapshots"]
assert contexts and all("CAP_FLIGHT_UPDATE" in json.loads(x["capabilityCoverage"])["missing"]
                        for x in contexts)
assert all(not any("CAP_FLIGHT_UPDATE" in a["capabilities"] for a in json.loads(x["agents"]))
           for x in contexts)
assert len(followup["plans"]) == 2
assert all(all(p[k] == "PASS" for k in ("structureCheckResult", "capabilityCheckResult",
                                        "constraintCheckResult")) for p in followup["plans"])
assert any(x["eventType"] == "SUPERVISION_JUDGED" for x in followup["events"])
assert [x["stepStatus"] for x in followup["assignments"]] == [
    "SKIPPED", "SKIPPED", "COMPLETED", "COMPLETED"]
assert all(x["reasonCode"] == "FLIGHT_CHANNEL_UNAVAILABLE"
           for x in followup["assignments"][:2])
assert sum(x["eventType"] == "FLIGHT_CHANNEL_UNCOVERED" for x in followup["events"]) == 2
assert followup["task"]["status"] == "COMPLETED"
assert all(x["restore"]["fixtureModeExact"] and x["restore"]["moonshotExitCode"] == 0
           and x["restore"]["fixtureStopped"] and x["restore"]["sixOnlineIdle"]
           for x in (unknown, missing))
refs = ";".join("acceptance/stage3/evidence/" + name for name in names)

steps_file = stage / "steps.csv"
with steps_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    step_fields, steps = reader.fieldnames, list(reader)
row = next(x for x in steps if x["stepId"] == "TC-041.S1")
assert row["status"] == "NOT_RUN"
row.update(status="F", observedAt=datetime.now().strftime("%Y-%m-%d"),
           actual=("受控候选任务90引用不存在能力，能力FAIL并列步骤2/原因码；随后任务91关闭两台唯一航班更新代理，"
                   "上下文明确CAP_FLIGHT_UPDATE缺口，然而自主和基线两版均三类校验PASS，进入监督和执行；"
                   "航班更新及航显两步被SKIPPED后任务仍COMPLETED。整步不满足无可承接代理时拦截。"),
           evidence=refs, issue="DEF-S3-070")
with steps_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=step_fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(steps)

rules_file = stage / "rules.csv"
with rules_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    rule_fields, rules = reader.fieldnames, list(reader)
for identifier in ("SRS_F013.R02", "SRS_F013.R04", "SRS_F017.R09"):
    item = next(x for x in rules if x["ruleId"] == identifier)
    assert item["status"] == ("P" if identifier == "SRS_F017.R09" else "NOT_RUN")
    item["status"] = "F"
    item["verifiedBy"] = "TC-041.S1"
    item["evidence"] = (item["evidence"] + ";" if item["evidence"] else "") + refs
    item["issue"] = "DEF-S3-070"
with rules_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=rule_fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rules)

issues_file = stage / "issues.csv"
with issues_file.open(encoding="utf-8-sig", newline="") as stream:
    assert "DEF-S3-070" not in {x["编号"] for x in csv.DictReader(stream)}
with issues_file.open("a", encoding="utf-8", newline="") as stream:
    csv.writer(stream, lineterminator="\n").writerow([
        "DEF-S3-070", "缺陷", "高", "TC-041.S1", "SRS_F013.R02;SRS_F013.R04;SRS_F017.R09", "待修复",
        "V1.5任务91在SIM_F2_DISPLAY及SIM_F2_FLIGHT均DISABLED/OFFLINE时构建上下文，明确缺CAP_FLIGHT_UPDATE且无该能力代理；自主与基线计划却均结构/能力/约束PASS，自主候选进入监督，基线执行时必需的航班更新与航显两步以FLIGHT_CHANNEL_UNAVAILABLE跳过，后两步完成后任务错误标记COMPLETED。任务90对不存在能力能正确报ERR_CAPABILITY_GAP，表明缺的是无在线承接者与核心渠道一致性校验。",
        refs,
        "能力校验以本次上下文的在线可用代理和类型渠道为准，缺任一步可承接者即阻断冻结/监督/执行；不得以SKIPPED的必需步骤满足任务完成条件，回归任务90/91及航班变更核心闭环。"])

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
assert "原 200 步：P 48、F 67、NT 19、未执行 66" in body
assert "281 条需求规则为 P 106、F 51、NT 11、未执行 113" in body
body = body.replace("原 200 步：P 48、F 67、NT 19、未执行 66",
                    "原 200 步：P 48、F 68、NT 19、未执行 65", 1)
body = body.replace("281 条需求规则为 P 106、F 51、NT 11、未执行 113",
                    "281 条需求规则为 P 105、F 54、NT 11、未执行 111", 1)
note = ("- TC-041.S1及`DEF-S3-070`：同一V1.5受控候选任务90的无效能力被正确拒绝；"
        "任务91的两台唯一航班更新代理在提交前均停用/离线，上下文明确CAP_FLIGHT_UPDATE缺口，"
        "但自主与基线两版三类校验全PASS，并进入监督/执行。航班更新和航显两项必需步骤被SKIPPED，"
        "任务仍错误置COMPLETED。整步判F；`SRS_F013.R02/R04`判F，先前正向样本给出的"
        "`SRS_F017.R09`由P更正为F。模型模式、服务与六代理均恢复，原始证据见"
        "`evidence/TC-041-capability-validation-*`和`evidence/TC-041-no-candidate-validation-followup-*`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 14:26（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded TC-041.S1 F, three rule failures, DEF-S3-070")
