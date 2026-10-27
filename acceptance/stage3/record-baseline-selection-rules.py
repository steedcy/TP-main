"""Map task 83's selected, validated baseline to three narrow SRS_F015 rules."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
first = stage / "evidence/TC-050-baseline-failure-20261027T042130Z.json"
follow = stage / "evidence/TC-050-baseline-selection-followup-20261027T042534Z.json"
run = json.loads(first.read_text(encoding="utf-8"))
ev = json.loads(follow.read_text(encoding="utf-8"))
assert ev["originalRequestGoal"] == ev["taskGoalAfterCleanup"] == run["request"]["taskGoal"]
assert ev["taskId"] == 83 and len(ev["downgradeEvents"]) == 1
assert len(ev["enabledBaggageTemplates"]) == 1
template = ev["enabledBaggageTemplates"][0]
assert template["templateVersion"] == "V1.3" and template["templateStatus"] == "ENABLED"
assert template["templateIntent"] == "OVERSIZE_BAGGAGE_HANDLING"
assert template["templateName"] in ev["downgradeEvents"][0]["detailSummary"]
baseline = next(p for p in ev["plans"] if p["source"] == "BASELINE_TEMPLATE")
assert len(baseline["planSteps"]) == 4
assert all(baseline[k] == "PASS" for k in
           ("structureCheckResult", "capabilityCheckResult", "constraintCheckResult"))
assert run["events"][3]["eventType"] == "PLAN_GENERATED"
assert run["events"][4]["eventType"] == "BASELINE_DOWNGRADED"
refs = ";".join("acceptance/stage3/evidence/" + p.name for p in (first, follow))
target = stage / "rules.csv"
with target.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
for rule_id in ("SRS_F015.R02", "SRS_F015.R03", "SRS_F015.R04"):
    row = next(r for r in rows if r["ruleId"] == rule_id)
    assert row["status"] == "NOT_RUN"
    row.update(status="P", verifiedBy="TC-050.S1", evidence=refs, issue="")
with target.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
assert "281 条需求规则为 P 97、F 45、NT 11、未执行 128" in body
body = body.replace("281 条需求规则为 P 97、F 45、NT 11、未执行 128",
                    "281 条需求规则为 P 100、F 45、NT 11、未执行 125", 1)
note = ("- `SRS_F015.R02/R03/R04`：任务83在受控模型故障后无需人工选择，自动采用已启用的"
        "超规行李基线模板V1.3；四步计划的结构、能力、约束校验均PASS，任务原始目标在失败/清理后"
        "与提交值逐字一致。三条独立规则判P；TC-047/048仍需分别完成多模板排序、详情页、冻结版本等步骤。"
        "见`evidence/TC-050-baseline-selection-followup-20261027T042534Z.json`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 12:24（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded SRS_F015.R02/R03/R04 P; TC-047/048 unchanged")
