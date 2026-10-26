"""Record TC-032.S1 from browser answer and completed task 37 evidence."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
start = json.loads((stage / "evidence/TC-032-complete-start.json").read_text(encoding="utf-8"))
ui = json.loads((stage / "evidence/TC-032-complete-ui.json").read_text(encoding="utf-8"))
result = json.loads((stage / "evidence/TC-032-complete-result.json").read_text(encoding="utf-8"))
assert start["observations"]["task"]["status"] == "PLANNING"
assert start["observations"]["task"]["missingInfoQuestions"]
assert start["observations"]["task"]["goalParsingResult"]["origin"] is None
assert ui["observations"]["questionInputCount"] == len(start["observations"]["task"]["missingInfoQuestions"])
assert ui["observations"]["initialSubmitDisabled"] and ui["observations"]["filledSubmitEnabled"]
assert ui["observations"]["clarifyHttp"] == 200
assert "F2_BAGGAGE_POINT" in ui["observations"]["clarifyRequestBody"]["answers"].values()
assert result["final"]["status"] == "COMPLETED" and result["final"]["missingInfoQuestions"] is None
assert result["final"]["taskGoal"] == start["request"]["taskGoal"]
assert result["contexts"] and result["plans"] and result["assignments"]
assert any(e["eventType"] == "GOAL_CLARIFIED" and e["trigger"] == "OPERATOR" for e in result["events"])
assert any(e["eventType"] == "CONTEXT_SNAPSHOT_GENERATED" for e in result["events"])
refs = ";".join("acceptance/stage3/evidence/" + name for name in [
    "TC-032-complete-start.json", "TC-032-complete-ui.json", "TC-032-complete-result.json",
    "TC-032-complete-clarify-before.png", "TC-032-complete-clarify-after.png"])

def update(name, key, changes):
    path = stage / name
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields, rows = reader.fieldnames, list(reader)
    for row in rows:
        if row[key] in changes:
            assert row["status"] == "NOT_RUN"
            row.update(changes[row[key]])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

update("steps.csv", "stepId", {
    "TC-032.S1": {"status": "P", "observedAt": datetime.now().astimezone().date().isoformat(),
        "actual": "任务37先缺行李位置而待规划，浏览器逐题输入前提交禁用；填F2_BAGGAGE_POINT后重新理解，生成上下文和计划并完成4步，原目标不变",
        "evidence": refs, "issue": ""},
})
update("rules.csv", "ruleId", {
    "SRS_F010.R03": {"status": "P", "verifiedBy": "TC-032.S1", "evidence": refs, "issue": ""},
})
print("recorded TC-032.S1 and SRS_F010.R03")
