"""Record TC-035.S1 and F011 rules from four live context snapshots."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
evidence = stage / "evidence"
exclusion = json.loads((evidence / "TC-035-context-exclusions.json").read_text(encoding="utf-8"))
capability = json.loads((evidence / "TC-035-context-capability-status.json").read_text(encoding="utf-8"))
archived = json.loads((evidence / "TC-035-context-archived-agent-retry.json").read_text(encoding="utf-8"))
busy = json.loads((evidence / "TC-035-context-busy-availability.json").read_text(encoding="utf-8"))
assert exclusion["injections"]["displayAgent"] == "OFFLINE"
assert exclusion["injections"]["robotBAgent"] == "DISABLED"
assert {a["deviceCode"] for a in exclusion["snapshot"]["agents"]}.isdisjoint(
    {"SIM_F2_DISPLAY", "SIM_F2_ROBOT_B"})
assert all("CAP_INFO_DISPLAY" not in a["capabilities"] for a in exclusion["snapshot"]["agents"]
           if a["deviceCode"] == "SIM_F2_FLIGHT")
assert len(exclusion["snapshot"]["agents"]) == 4 and exclusion["restore"]["allSixOnlineIdle"]
for device in capability["injectedStates"]:
    assert "CAP_INFO_DISPLAY" not in next(a["capabilities"] for a in capability["snapshot"]["agents"]
                                              if a["deviceCode"] == device)
assert len(capability["snapshot"]["agents"]) == 6
assert capability["restore"]["allOriginalStatuses"] and capability["restore"]["allSixOnlineIdle"]
assert archived["injectedState"] == "ARCHIVED|OFFLINE"
assert len(archived["snapshot"]["agents"]) == 5
assert "SIM_F2_ROBOT_B" not in {a["deviceCode"] for a in archived["snapshot"]["agents"]}
assert archived["restore"]["allSixOnlineIdle"]
display = next(a for a in busy["snapshot"]["agents"] if a["deviceCode"] == "SIM_F2_DISPLAY")
assert busy["dryRun"]["agentAtSnapshot"]["workStatus"] == "BUSY"
assert display["workload"] == "BUSY" and display["availableUntil"] is None
assert busy["restore"]["allSixOnlineIdle"] and busy["restore"]["delayMs"] == 1000
assert busy["restore"]["templateStatus"] == "DISABLED"
assert all(c["generatedAt"] for c in exclusion["snapshot"]["raw"] +
           capability["snapshot"]["raw"] + archived["snapshot"]["raw"] + busy["snapshot"]["raw"])
day = datetime.now().astimezone().date().isoformat()
refs = ";".join("acceptance/stage3/evidence/" + name for name in [
    "TC-035-context-exclusions.json", "TC-035-context-capability-status.json",
    "TC-035-context-archived-agent.json", "TC-035-context-archived-agent-retry.json",
    "TC-035-context-busy-availability.json"])

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
    "TC-035.S1": {"status": "F", "observedAt": day,
        "actual": "任务38/39/41上下文正确排除离线/停用/归档代理及UNTESTED/TESTED_FAILED/DISABLED能力，含位置/负载/生成时间并持久化；任务43期间航显代理真实BUSY但availableUntil为null",
        "evidence": refs, "issue": "DEF-S3-031"},
})
update("rules.csv", "ruleId", {
    "SRS_F011.R01": {"status": "F", "verifiedBy": "TC-035.S1", "evidence": refs, "issue": "DEF-S3-031"},
    "SRS_F011.R02": {"status": "P", "verifiedBy": "TC-035.S1", "evidence": refs, "issue": ""},
    "SRS_F011.R03": {"status": "P", "verifiedBy": "TC-035.S1", "evidence": refs, "issue": ""},
    "SRS_F011.R04": {"status": "P", "verifiedBy": "TC-035.S1", "evidence": refs, "issue": ""},
})
issues = stage / "issues.csv"
with issues.open(encoding="utf-8-sig", newline="") as handle:
    reader = csv.DictReader(handle)
    assert "DEF-S3-031" not in {row["编号"] for row in reader}
with issues.open("a", encoding="utf-8", newline="") as handle:
    writer = csv.writer(handle, lineterminator="\n")
    writer.writerow(["DEF-S3-031", "缺陷", "中", "TC-035.S1", "SRS_F011.R01", "待修复",
        "任务42试运行真实占用SIM_F2_DISPLAY，任务43上下文快照中该代理workload=BUSY但availableUntil仍为null，缺可用时间",
        "acceptance/stage3/evidence/TC-035-context-busy-availability.json",
        "上下文为忙碌代理提供可用时间或明确可计算预测值，补测忙碌/空闲及超时边界；复核模型候选事实"])
print("recorded TC-035.S1, four F011 rules and DEF-S3-031")
