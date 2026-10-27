"""Record SRS_F002A.R01 from current isolated runtime and seed fixture."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
file = stage / "evidence/SRS_F002A-standard-dataset-coverage-20261027T013207Z.json"
data = json.loads(file.read_text(encoding="utf-8"))
expected = {"OVERSIZE_BAGGAGE_HANDLING", "SPECIAL_PASSENGER_SERVICE", "FLIGHT_CHANGE_RESPONSE"}
assert data["runtimeInput"] == "V1.5" and data["isolatedSchema"] == "tip_stage2_v14"
assert set(data["seedFamilies"]) == expected
assert {r["definitionCode"] for r in data["presetDefinitions"]} == expected
assert all(r["isPreset"] and r["definitionStatus"] == "ENABLED"
           for r in data["presetDefinitions"])
assert len(data["presetTemplates"]) == 3
assert all(r["isPreset"] and r["templateStatus"] == "ENABLED" and
           r["stepCount"] > 0 for r in data["presetTemplates"])
assert len(data["simulatorAgents"]) == 6

rules_file = stage / "rules.csv"
with rules_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rules = reader.fieldnames, list(reader)
row = next(r for r in rules if r["ruleId"] == "SRS_F002A.R01")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-006.S2",
           evidence="acceptance/stage3/evidence/" + file.name, issue="")
with rules_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rules)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
assert "281 条需求规则为 P 90、F 42、NT 11、未执行 138" in body
body = body.replace("281 条需求规则为 P 90、F 42、NT 11、未执行 138",
                    "281 条需求规则为 P 91、F 42、NT 11、未执行 137", 1)
heading = "## 已执行\n\n"
assert heading in body
note = ("- `SRS_F002A.R01`：当前V1.5隔离库中三类核心场景均有启用的预置任务定义，"
        "种子基线夹具也逐一覆盖三族；运行时有三条已启用预置基线模板及六台仿真代理。"
        "因此仅对标准数据集场景覆盖规则判P。TC-006.S2的多次复位后版本/摘要一致性与"
        "失败回滚仍未执行，整步保持NOT_RUN。证据见"
        "`evidence/SRS_F002A-standard-dataset-coverage-20261027T013207Z.json`。\n")
body = body.replace(heading, heading + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 09:31（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded SRS_F002A.R01 P")
