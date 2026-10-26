"""Record completed-prefix preservation and no post-termination dispatch."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
def only(pattern):
    files = list((stage / "evidence").glob(pattern))
    assert len(files) == 1
    return files[0], json.loads(files[0].read_text(encoding="utf-8"))
run_file, run = only("TC-066-terminate-prefix-20*.json")
follow_file, follow = only("TC-066-terminate-prefix-followup-20*.json")
assert run["started"]["taskId"] == follow["taskId"] == 65
assert run["prefixReached"] and run["taskBeforeTerminate"]["status"] == "EXECUTING"
before = {a["stepSeq"]: a for a in run["assignmentsBeforeTerminate"]}
after = {a["stepSeq"]: a for a in run["assignmentsAfterTerminate"]}
final = {a["stepSeq"]: a for a in follow["assignments"]}
assert before[1]["stepStatus"] == "COMPLETED" and before[1]["outputParams"]
assert before[2]["stepStatus"] == "EXECUTING"
assert after[1]["stepStatus"] == final[1]["stepStatus"] == "COMPLETED"
assert after[1]["outputParams"] == final[1]["outputParams"] == before[1]["outputParams"]
assert after[2]["stepStatus"] == final[2]["stepStatus"] == "FROZEN"
assert follow["status"] == "MANUAL_TERMINATED"
assert [c["type"] for c in follow["commands"]] == [
    "TASK_ACCEPT", "EXECUTE_CAPABILITY", "TASK_ACCEPT", "EXECUTE_CAPABILITY", "TASK_CANCEL"]
assert follow["commands"][-1]["status"] == "CONFIRMED_IDLE"
assert follow["eventTypes"][-1] == "TASK_CANCEL_CONFIRMED_IDLE"
assert follow["agent"]["workStatus"] == "IDLE" and follow["agent"]["currentTaskId"] is None
assert run["restore"]["sameTemplateSteps"] and run["restore"]["allSixOnlineIdle"]
assert run["restore"]["delayMs"] == 1000 and run["restore"]["template"]["templateStatus"] == "DISABLED"
refs = ";".join("acceptance/stage3/evidence/" + p.name for p in (run_file, follow_file))

def update(path, key, changes):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    for target, change in changes.items():
        row = next(r for r in rows if r[key] == target)
        assert row["status"] == "NOT_RUN"
        row.update(change)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

update(stage / "steps.csv", "stepId", {
    "TC-066.S2": dict(status="P", observedAt=datetime.now().astimezone().date().isoformat(),
        actual="任务65两步试运行：第一步COMPLETED且输出已保存，第二步EXECUTING时人工终止；第二步冻结，无后续业务指令，向占用代理下发TASK_CANCEL并最终CONFIRMED_IDLE；第一步输出前后相同，代理恢复在线空闲，任务保持不可恢复的MANUAL_TERMINATED。模板恢复原单步并停用，仿真延时恢复1000ms。",
        evidence=refs, issue="")})
update(stage / "rules.csv", "ruleId", {
    "SRS_F021.R02": dict(status="P", verifiedBy="TC-066.S2", evidence=refs, issue=""),
    "SRS_F021.R06": dict(status="P", verifiedBy="TC-066.S2", evidence=refs, issue="")})
print("recorded TC-066.S2, SRS_F021.R02/R06 P")
