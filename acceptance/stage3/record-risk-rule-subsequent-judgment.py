"""Record TC-043.S2 and the unresolved paired-risk fixture gap."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
ev = stage / "evidence"
first_file = ev / "TC-043-risk-rule-subsequent-judgment-20261027T034211Z.json"
pair1_file = ev / "TC-043-risk-rule-paired-plan-20261027T034405Z.json"
pair2_file = ev / "TC-043-risk-rule-paired-plan-20261027T034740Z.json"
follow_file = ev / "TC-043-risk-rule-subsequent-followup-20261027T035011Z.json"
first = json.loads(first_file.read_text(encoding="utf-8"))
pair1 = json.loads(pair1_file.read_text(encoding="utf-8"))
pair2 = json.loads(pair2_file.read_text(encoding="utf-8"))
follow = json.loads(follow_file.read_text(encoding="utf-8"))
assert all(x["runtimeInput"] == "V1.5" and x["isolatedSchema"] == "tip_stage2_v14"
           for x in (first, pair1, pair2, follow))
assert first["riskRuleBefore"]["enabled"] and first["riskRuleBefore"]["ruleVersion"] == "V1.0"
assert first["cases"][0]["ruleAtSubmit"]["enabled"]
assert not first["cases"][1]["ruleAtSubmit"]["enabled"]
assert first["cases"][0]["plans"][0]["constraintCheckResult"] == "FAIL"
low = first["cases"][1]["plans"][0]
assert low["source"] == "AUTONOMOUS" and low["riskLevel"] == "LOW"
assert all(low[key] == "PASS" for key in
           ("structureCheckResult", "capabilityCheckResult", "constraintCheckResult"))
assert pair1["cases"][0]["task"]["status"] == pair1["cases"][1]["task"]["status"] == "PLANNING"
assert pair1["cases"][0]["cleanup"] == pair1["cases"][1]["cleanup"] == "MANUAL_TERMINATED"
assert pair2["cases"][0]["task"]["status"] == "PENDING_MANUAL"
assert len(pair2["cases"][0]["clarifications"]) == 3
assert pair2["cases"][1]["plans"][0]["riskLevel"] == "LOW"
assert pair2["restore"]["fixtureExact"] and pair2["restore"]["rule"]["enabled"]
assert follow["rule"]["enabled"] and follow["rule"]["ruleVersion"] == "V1.0"
assert len(follow["audit"]) >= 6
assert all(r["operationResult"] == "SUCCESS" and '"before"' in r["detail"]
           and '"after"' in r["detail"] for r in follow["audit"][:6])
assert all(follow["tasks"][str(i)]["status"] in {"COMPLETED", "MANUAL_TERMINATED"}
           for i in range(72, 78))
assert len(follow["agents"]) == 6 and all(a["onlineStatus"] == "ONLINE" and
                                            a["workStatus"] == "IDLE" and
                                            a["currentTaskId"] is None
                                            for a in follow["agents"])

base = "acceptance/stage3/evidence/"
refs = ";".join(base + file.name for file in
                (first_file, pair1_file, pair2_file, follow_file))
steps_file = stage / "steps.csv"
with steps_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["stepId"] == "TC-043.S2")
assert row["status"] == "NOT_RUN"
row.update(status="F", observedAt=datetime.now().strftime("%Y-%m-%d"),
           actual="启用资源临界规则时任务72自主候选约束校验失败；停用后独立任务73/77三类校验PASS且监督判LOW，未直接完成同一候选的高低风险成对对照。两次受控成对尝试中任务74/75停在目标补充，任务76三轮后转人工。启停前后规则版本均V1.0，尽管操作审计含操作者、时间与变更前后摘要，后续判定无法指向递增的启停版本；阶段3既有DEF-S3-043仍成立。",
           evidence=refs + ";acceptance/stage3/evidence/TC-039-plan-six-fields-20261026T042249Z.json",
           issue="DEF-S3-043;NT-S3-027")
with steps_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

rules_file = stage / "rules.csv"
with rules_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rules = reader.fieldnames, list(reader)
row = next(r for r in rules if r["ruleId"] == "SRS_F002.R05")
assert row["status"] == "NOT_RUN"
row.update(status="F", verifiedBy="TC-043.S2", evidence=refs, issue="DEF-S3-043;NT-S3-027")
row = next(r for r in rules if r["ruleId"] == "SRS_F014.R05")
assert row["status"] == "F" and "DEF-S3-043" in row["issue"]
row["verifiedBy"] += ";TC-043.S2"
row["evidence"] += ";" + refs
with rules_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rules)

issues_file = stage / "issues.csv"
with issues_file.open(encoding="utf-8-sig", newline="") as stream:
    assert "NT-S3-027" not in {r["编号"] for r in csv.DictReader(stream)}
with issues_file.open("a", encoding="utf-8", newline="") as stream:
    csv.writer(stream, lineterminator="\n").writerow([
        "NT-S3-027", "前置缺口", "待定", "TC-043.S2;TC-044.S1", "SRS_F002.R05;SRS_F014.R05",
        "待补同候选风险对照", "任务55在规则启用时为HIGH/RULE_RESOURCE_CRITICAL、任务73/77在该规则停用时为LOW，但未形成同一候选计划的启停成对成功对照。受控候选任务74/75目标理解停在补充，任务76三轮后转人工，无法把这些样本的风险差异单独归因于规则启停。",
        refs + ";acceptance/stage3/evidence/TC-039-plan-six-fields-20261026T042249Z.json",
        "构造目标理解稳定且三类校验PASS的固定候选，分别在规则启用/停用下运行监督，保留候选内容、上下文、规则版本、原因码、审计及恢复状态。"])

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
assert "原 200 步：P 42、F 60、NT 19、未执行 79" in body
assert "281 条需求规则为 P 92、F 43、NT 11、未执行 135" in body
body = body.replace("原 200 步：P 42、F 60、NT 19、未执行 79",
                    "原 200 步：P 42、F 61、NT 19、未执行 78", 1)
body = body.replace("281 条需求规则为 P 92、F 43、NT 11、未执行 135",
                    "281 条需求规则为 P 92、F 44、NT 11、未执行 134", 1)
heading = "## 已执行\n\n"
assert heading in body
note = ("- TC-043.S2规则启停后续判定：当前规则启用/停用两次对照、固定候选两轮尝试共任务72～77。"
        "停用资源临界规则后任务73/77三类校验PASS并由监督判LOW；启用时任务72先约束FAIL，"
        "任务74/75停在目标补充，任务76三轮后转人工，无法作同候选的高低风险因果对照，记"
        "`NT-S3-027`。资源规则每次启停都有前后摘要审计，但版本始终V1.0，"
        "复用`DEF-S3-043`，整步与`SRS_F002.R05`判F，`SRS_F014.R05`补证。"
        "规则、规划夹具及六代理已恢复，任务74～76人工终止，其他三任务完成。"
        "原始证据见`evidence/TC-043-risk-rule-*`。\n")
body = body.replace(heading, heading + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 09:35（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded TC-043.S2 F, F002.R05 F, NT-S3-027")
