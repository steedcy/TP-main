"""Record TC-038 after five independent live controlled model responses."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
names = ["TC-038-planning-faults-20261026T041140Z.json",
         "TC-038-planning-boundary-followup-20261026T041347Z.json"]
first, follow = [json.loads((stage / "evidence" / n).read_text(encoding="utf-8"))
                 for n in names]
assert first["schema"] == follow["schema"] == "tip_stage2_v14"
assert first["fixtureModeRestored"] and follow["fixtureModeRestored"]
cases = {c.get("mode") or c.get("label"): c for c in first["cases"] + follow["cases"]}
assert set(cases) == {"too_many_steps", "malformed", "timeout", "missing_field", "timeout_probe"}
for run in [first, follow]:
    assert len(run["agentsAfter"]) == 6 and all(
        a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE" and
        a["workStatus"] == "IDLE" for a in run["agentsAfter"])
    for case in run["cases"]:
        assert case["afterMaxTaskId"] == case["beforeMaxTaskId"] + 1
        assert case["task"]["status"] == "COMPLETED"
        assert case["task"]["taskGoal"] == run["request"]["taskGoal"]
        assert [r["phase"] for r in case["modelRequests"]] == ["goal", "planning"]
        assert len(case["contexts"]) == 2
        assert case["plans"][-1]["source"] == "BASELINE_TEMPLATE"
        assert all(case["plans"][-1][field] == "PASS" for field in
                   ["structureCheckResult", "capabilityCheckResult", "constraintCheckResult"])
        assert case["plans"][-1]["frozenAt"]
        assert all(p["source"] != "AUTONOMOUS" or not p["frozenAt"] for p in case["plans"])
        assert len(case["deviceCommands"].splitlines()) == 8
assert "ERR_STEP_LIMIT_EXCEEDED" in [e["reasonCode"] for e in cases["too_many_steps"]["events"]]
assert len(cases["too_many_steps"]["plans"]) == 1
assert "ERR_PLANNING_MODEL_FAILED" in [e["reasonCode"] for e in cases["malformed"]["events"]]
assert "ERR_PLANNING_MODEL_FAILED" in [e["reasonCode"] for e in cases["timeout"]["events"]]
assert "ERR_VALIDATION_FAILED" in [e["reasonCode"] for e in cases["missing_field"]["events"]]
autonomous = cases["missing_field"]["plans"][0]
assert autonomous["source"] == "AUTONOMOUS" and autonomous["structureCheckResult"] == "FAIL"
assert not autonomous["frozenAt"] and any(
    e["reasonCode"] == "ERR_STEP_FIELD_MISSING" for e in autonomous["validationErrors"])
for name in ["timeout", "timeout_probe"]:
    assert 59 <= cases[name]["elapsedSeconds"] <= 65
    assert "ERR_PLANNING_MODEL_FAILED" in [e["reasonCode"] for e in cases[name]["events"]]
assert all(r["ok"] for r in cases["timeout_probe"]["concurrentReads"].values())
refs = ";".join("acceptance/stage3/evidence/" + n for n in names)
day = datetime.now().astimezone().date().isoformat()

def update(name, key, changes):
    path = stage / name
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    for row in rows:
        if row[key] in changes:
            assert row["status"] == "NOT_RUN", row[key]
            row.update(changes[row[key]])
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

update("steps.csv", "stepId", {
    "TC-038.S1": {"status": "P", "observedAt": day,
        "actual": "任务48六步候选直接ERR_STEP_LIMIT_EXCEEDED且未截断；任务49无法解析JSON转模型失败；任务51缺stepGoal被结构校验拒绝且自主版本未冻结；三任务仅校验通过的四步基线下发并完成",
        "evidence": refs, "issue": ""},
    "TC-038.S2": {"status": "P", "observedAt": day,
        "actual": "任务50/52规划模型受控延迟65秒，调用约60.16/60.11秒超时，原候选未下发；转已校验四步基线完成，目标原文不变；任务52等待期间总览、设备、已有任务详情可访问",
        "evidence": refs, "issue": ""},
})
update("rules.csv", "ruleId", {
    "SRS_F012.R07": {"status": "P", "verifiedBy": "TC-038.S1;TC-038.S2",
                     "evidence": refs, "issue": ""},
    "SRS_F012.R09": {"status": "P", "verifiedBy": "TC-038.S1",
                     "evidence": refs, "issue": ""},
})
print("recorded TC-038.S1/S2 and two F012 rules")
