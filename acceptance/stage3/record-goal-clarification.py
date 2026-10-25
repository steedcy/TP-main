"""Record TC-031.S3 and TC-032.S2 only after this run's API evidence checks."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
goal = json.loads((stage / "evidence/TC-031-goal-clarify-cancel.json").read_text(encoding="utf-8"))
history = json.loads((stage / "evidence/TC-031-goal-history-check.json").read_text(encoding="utf-8"))
limit = json.loads((stage / "evidence/TC-032-three-clarifications.json").read_text(encoding="utf-8"))
g = goal["observations"]
l = limit["observations"]
assert g["afterSubmit"]["status"] == "PLANNING" and g["afterClarify"]["status"] == "PLANNING"
assert g["finalTask"]["status"] == "MANUAL_TERMINATED" and g["planVersionCount"] == 0
assert g["finalTask"]["taskGoal"] == goal["submitRequest"]["taskGoal"]
assert {("GOAL_SUBMITTED", "OPERATOR"), ("GOAL_CLARIFIED", "OPERATOR"),
        ("MANUAL_TERMINATED", "OPERATOR")} <= {(e["eventType"], e["trigger"]) for e in g["events"]}
assert history["tasks"]["19"]["originalGoalUnchanged"]
assert "BASELINE_TEMPLATE" in [p["source"] for p in history["tasks"]["19"]["plans"]]
assert len(l["rounds"]) == 3
assert [r["afterStatus"] for r in l["rounds"]] == ["PLANNING", "PLANNING", "PENDING_MANUAL"]
assert l["finalTask"]["status"] == "PENDING_MANUAL" and not l["planVersions"]
assert len(l["finalTask"]["sceneParams"]["clarificationAnswers"]) == 3
assert l["finalTask"]["missingInfoQuestions"]
day = datetime.now().astimezone().date().isoformat()
cancel_ev = "acceptance/stage3/evidence/TC-031-goal-clarify-cancel.json;acceptance/stage3/evidence/TC-031-goal-history-check.json"
limit_ev = "acceptance/stage3/evidence/TC-032-three-clarifications.json"

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
    "TC-031.S3": {"status": "P", "observedAt": day,
        "actual": "新任务34提交、一次人工补充后仍待规划，未生成计划；取消转人工终止，原因和三类操作事件齐全；任务19降级前后原目标原文一致",
        "evidence": cancel_ev, "issue": ""},
    "TC-032.S2": {"status": "P", "observedAt": day,
        "actual": "任务35连续三次提交非空但仍缺关键字段的补充；前两轮待规划、第三轮转待人工处理，保留三轮问答和未补问题，计划版本0",
        "evidence": limit_ev, "issue": ""},
})
update("rules.csv", "ruleId", {
    "SRS_F010.R04": {"status": "P", "verifiedBy": "TC-031.S3;TC-032.S2", "evidence": cancel_ev + ";" + limit_ev, "issue": ""},
    "SRS_F010.R05": {"status": "P", "verifiedBy": "TC-031.S3", "evidence": cancel_ev, "issue": ""},
    "SRS_F010.R08": {"status": "P", "verifiedBy": "TC-031.S3", "evidence": cancel_ev, "issue": ""},
    "SRS_F010.R09": {"status": "P", "verifiedBy": "TC-032.S2", "evidence": limit_ev, "issue": ""},
    "SRS_F010.R10": {"status": "P", "verifiedBy": "TC-032.S2", "evidence": limit_ev, "issue": ""},
})
print("recorded TC-031.S3, TC-032.S2 and five rules")
