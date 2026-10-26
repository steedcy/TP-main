"""Record TC-034 goal-understanding timeout with observed downgrade failure."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
names = ["TC-034-goal-timeout-20261026T040203Z.json",
         "TC-034-goal-timeout-cleanup-20261026T040349Z.json"]
timeout, cleanup = [json.loads((stage / "evidence" / n).read_text(encoding="utf-8"))
                    for n in names]
assert timeout["schema"] == cleanup["schema"] == "tip_stage2_v14"
assert timeout["afterMaxTaskId"] == 47 == timeout["beforeMaxTaskId"] + 1
assert timeout["submitError"].startswith("HTTP 503:")
assert 59 <= timeout["submitElapsedSeconds"] <= 65
assert timeout["fixtureModeDuring"]["goal"] == "timeout"
assert timeout["fixtureModeRestored"]
assert [r["phase"] for r in timeout["modelRequests"]] == ["goal"]
assert any(e["reasonCode"] == "ERR_GOAL_UNDERSTANDING_TIMEOUT"
           for e in timeout["events"])
assert timeout["task"]["status"] == "PLANNING"
assert timeout["contexts"] == [] and timeout["plans"] == []
assert all(timeout["concurrentReads"][key]["ok"] for key in ["dashboard", "devices", "task"])
assert cleanup["taskBeforeCleanup"]["status"] == "PLANNING"
assert cleanup["taskBeforeCleanup"]["taskGoal"] == timeout["request"]["taskGoal"]
assert cleanup["deviceCommandCount"] == cleanup["assignmentCount"] == 0
assert any(t["templateIntent"] == "OVERSIZE_BAGGAGE_HANDLING" and
           t["templateStatus"] == "ENABLED" for t in cleanup["baselines"])
assert cleanup["taskAfterCleanup"]["status"] == "MANUAL_TERMINATED"
assert len(cleanup["agentsAfter"]) == 6 and all(
    a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE" and
    a["workStatus"] == "IDLE" for a in cleanup["agentsAfter"])
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
    "TC-034.S1": {"status": "F", "observedAt": day,
        "actual": "受控目标理解服务延迟65秒，任务47约60.22秒返回503并记录ERR_GOAL_UNDERSTANDING_TIMEOUT，设备指令0；但任务仍PLANNING，未自动判断已启用基线降级",
        "evidence": refs, "issue": "DEF-S3-033"},
    "TC-034.S2": {"status": "F", "observedAt": day,
        "actual": "超规基线模板当时为ENABLED，任务47超时后仍PLANNING且快照/计划均0，未用基线执行原目标；故障期间总览、设备、已有任务详情可访问，原始目标保留；不可用基线分支尚未独立执行",
        "evidence": refs, "issue": "DEF-S3-033"},
})
update("rules.csv", "ruleId", {"SRS_F010.R07": {
    "status": "P", "verifiedBy": "TC-034.S1", "evidence": refs, "issue": ""}})
issues = stage / "issues.csv"
with issues.open(encoding="utf-8-sig", newline="") as stream:
    assert "DEF-S3-033" not in {row["编号"] for row in csv.DictReader(stream)}
with issues.open("a", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["DEF-S3-033", "缺陷", "高", "TC-034.S1;TC-034.S2", "", "待修复",
                     "任务47目标理解受控延迟65秒，约60.22秒超时并产生ERR_GOAL_UNDERSTANDING_TIMEOUT；超规基线当时已启用，任务仍停留PLANNING、无快照与计划，未自动降级，需人工取消清场",
                     refs,
                     "阶段4目标理解超时/异常后记录原因并进入基线可用性与校验流程；不可用转PENDING_MANUAL；保留原目标与禁止未经校验指令，补测两分支"])
print("recorded TC-034.S1/S2, SRS_F010.R07 and DEF-S3-033")
