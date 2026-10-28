"""Record TC-040.S1 failure from a frozen plan containing an explicit loop."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
names = ["TC-041-capability-validation-six-steps-20261028T014012Z.json",
         "TC-041-capability-validation-loop-marker-20261028T014201Z.json",
         "TC-041-capability-validation-unbounded-loop-text-20261028T014330Z.json",
         "TC-041-plan-ui-task96-20261028T014144Z.json",
         "TC-041-plan-ui-task98-20261028T014457Z.json"]
limit, marker, loop, limit_ui, loop_ui = [
    json.loads((stage / "evidence" / name).read_text(encoding="utf-8")) for name in names]
assert all(x["runtimeInput"] == "V1.5" for x in (limit, marker, loop, limit_ui, loop_ui))
assert [x["submitted"]["id"] for x in (limit, marker, loop)] == [96, 97, 98]
assert len(limit["initialPlanSteps"]) == 6
assert len(limit["finished"]["plans"]) == 1
assert limit["finished"]["plans"][0]["source"] == "BASELINE_TEMPLATE"
assert any(x["eventType"] == "PLAN_VALIDATED" and x["reasonCode"] == "ERR_STEP_LIMIT_EXCEEDED"
           for x in limit["finished"]["events"])
assert limit_ui["tabs"] == ["版本1（基线模板）"]
assert marker["initialPlanSteps"][1]["inputParams"]["__loop__"] is True
marked = marker["finished"]["plans"][0]
assert marked["structureCheckResult"] == "FAIL"
assert any(x["reasonCode"] == "ERR_STEP_LOOP_DETECTED" and x["stepSeq"] == 2
           for x in marked["validationErrors"])
assert marked["frozenAt"] is None
phrase = "while(true) { repeat this display step forever; }"
assert loop["initialPlanSteps"][1]["precondition"] == phrase
accepted = loop["finished"]["plans"][0]
assert accepted["source"] == "AUTONOMOUS" and accepted["planSteps"][1]["precondition"] == phrase
assert all(accepted[k] == "PASS" for k in ("structureCheckResult", "capabilityCheckResult",
                                           "constraintCheckResult"))
assert accepted["frozenAt"] and accepted["validationErrors"] == []
assert any(x["eventType"] == "SUPERVISION_JUDGED" for x in loop["finished"]["events"])
assert loop_ui["taskId"] == 98 and phrase in loop_ui["candidateDetail"]
assert "结构校验\t通过" in loop_ui["candidateDetail"]
assert all(x["restore"]["fixtureModeExact"] and x["restore"]["moonshotExitCode"] == 0
           and x["restore"]["fixtureStopped"] and x["restore"]["sixOnlineIdle"]
           for x in (limit, marker, loop))
refs = ";".join("acceptance/stage3/evidence/" + name for name in names)

steps = stage / "steps.csv"
with steps.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
item = next(x for x in rows if x["stepId"] == "TC-040.S1")
assert item["status"] == "NOT_RUN"
item.update(status="F", observedAt=datetime.now().strftime("%Y-%m-%d"),
            actual=("V1.5受控六步候选被ERR_STEP_LIMIT_EXCEEDED拒绝且未截断，显式__loop__标记在步骤2"
                    "被ERR_STEP_LOOP_DETECTED拒绝；但同一四步计划把`while(true) { repeat this display step forever; }`"
                    "写入步骤2前置条件后，三类校验PASS、自主版本冻结并进入监督，Chrome仍显示该无限循环原文。"
                    "故循环/无限执行语义没有被结构校验拦截，整步判F；未观察到真实代码执行。"),
            evidence=refs, issue="DEF-S3-071")
with steps.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

rules = stage / "rules.csv"
with rules.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
loop_rule = next(x for x in rows if x["ruleId"] == "SRS_F012.R03")
assert loop_rule["status"] == "NOT_RUN"
loop_rule.update(status="F", verifiedBy="TC-040.S1", evidence=refs, issue="DEF-S3-071")
structure = next(x for x in rows if x["ruleId"] == "SRS_F013.R01")
assert structure["status"] == "F" and structure["issue"] == "DEF-S3-034"
structure["issue"] += ";DEF-S3-071"
structure["evidence"] += ";" + refs
with rules.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

issues = stage / "issues.csv"
with issues.open(encoding="utf-8-sig", newline="") as stream:
    assert "DEF-S3-071" not in {x["编号"] for x in csv.DictReader(stream)}
with issues.open("a", encoding="utf-8", newline="") as stream:
    csv.writer(stream, lineterminator="\n").writerow([
        "DEF-S3-071", "缺陷", "中", "TC-040.S1", "SRS_F012.R03;SRS_F013.R01", "待修复",
        "同一V1.5受控计划的六步版本被上限校验拒绝，__loop__显式标记被结构校验拒绝；但任务98的步骤2前置条件原文为while(true) { repeat this display step forever; }，自主计划仍结构/能力/约束PASS、冻结并进入监督，Chrome保留无限重复原文。未观察到代码执行或实际循环，问题范围限于计划内容审核与冻结。",
        refs,
        "在候选计划结构/语义校验中拒绝循环、动态代码与无限协商指令，包括步骤目标、前置、完成和失败处理文字；保留逐步骤错误清单，回归六步/显式标记/文本循环及正常四步计划。"])

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
assert "原 200 步：P 49、F 67、NT 19、未执行 65" in body
assert "281 条需求规则为 P 108、F 51、NT 11、未执行 111" in body
body = body.replace("原 200 步：P 49、F 67、NT 19、未执行 65",
                    "原 200 步：P 49、F 68、NT 19、未执行 64", 1)
body = body.replace("281 条需求规则为 P 108、F 51、NT 11、未执行 111",
                    "281 条需求规则为 P 108、F 52、NT 11、未执行 110", 1)
note = ("- TC-040.S1与`DEF-S3-071`：同一V1.5受控计划的六步版本被`ERR_STEP_LIMIT_EXCEEDED`拒绝，"
        "显式`__loop__`也在步骤2被`ERR_STEP_LOOP_DETECTED`拒绝；但任务98前置条件含"
        "`while(true) { repeat this display step forever; }`，自主版本仍三类PASS、冻结并进入监督，"
        "Chrome展示原文。整步及`SRS_F012.R03`判F，既有`SRS_F013.R01`补证。"
        "本轮没有观察到真实代码执行或实际无限循环；只是候选内容未被拦截。"
        "三轮模型模式、服务及六代理恢复，证据见`evidence/TC-041-capability-validation-*`与"
        "`evidence/TC-041-plan-ui-task{96,98}-*`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-28 09:40（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded TC-040.S1 F, SRS_F012.R03 F and DEF-S3-071")
