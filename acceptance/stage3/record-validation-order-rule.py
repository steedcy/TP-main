"""Score SRS_F013.R05 from distinct V1.5 capability and constraint failures."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
names = ("TC-041-capability-validation-unknown-capability-20261027T062908Z.json",
         "TC-041-capability-validation-invalid-param-20261028T012808Z.json",
         "TC-041-plan-ui-task90-20261028T013509Z.json")
cap, constraint, ui = [json.loads((stage / "evidence" / name).read_text(encoding="utf-8"))
                       for name in names]
assert cap["runtimeInput"] == constraint["runtimeInput"] == ui["runtimeInput"] == "V1.5"
assert cap["submitted"]["id"] == 90 and constraint["submitted"]["id"] == 93
first = cap["finished"]["plans"][0]
assert [first[k] for k in ("structureCheckResult", "capabilityCheckResult",
                          "constraintCheckResult")] == ["PASS", "FAIL", "FAIL"]
assert {"CAPABILITY", "CONSTRAINT"}.issubset({x["errorType"] for x in first["validationErrors"]})
assert first["frozenAt"] is None
assert "能力校验\t不通过" in ui["candidateDetail"]
assert "约束校验\t不通过" in ui["candidateDetail"]
assert "ERR_CAPABILITY_GAP" in ui["candidateDetail"]
second = constraint["finished"]["plans"][0]
assert [second[k] for k in ("structureCheckResult", "capabilityCheckResult",
                           "constraintCheckResult")] == ["PASS", "PASS", "FAIL"]
assert any(x["reasonCode"] == "ERR_CAPABILITY_PARAMETER_INVALID"
           for x in second["validationErrors"])
assert second["frozenAt"] is None
refs = ";".join("acceptance/stage3/evidence/" + name for name in names)
target = stage / "rules.csv"
with target.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
item = next(x for x in rows if x["ruleId"] == "SRS_F013.R05")
assert item["status"] == "NOT_RUN"
item.update(status="P", verifiedBy="TC-041.S1;TC-041.S2", evidence=refs)
with target.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
assert "281 条需求规则为 P 107、F 51、NT 11、未执行 112" in body
body = body.replace("281 条需求规则为 P 107、F 51、NT 11、未执行 112",
                    "281 条需求规则为 P 108、F 51、NT 11、未执行 111", 1)
note = ("- `SRS_F013.R05`：受控任务90的同一自主版本结构PASS、能力FAIL、约束FAIL，"
        "两类错误在Chrome清单显示，版本未冻结；任务93结构/能力PASS、约束FAIL且未冻结。"
        "三类独立结果与失败后继续收集错误的规则在这些样本下判P；"
        "TC-040.S1所要求的超五步、循环和动态代码等结构错误仍需逐项执行。"
        "见`evidence/TC-041-capability-validation-*`及`evidence/TC-041-plan-ui-task90-*`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-28 09:38（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded SRS_F013.R05 P")
