"""Close SRS_F005.R04 from explicit rejection and an eligible online dispatch."""
import csv
import json
from pathlib import Path

stage = Path(__file__).resolve().parent
evidence = stage / "evidence"
flight = json.loads((evidence / "TC-014-offline-assignment-20261026T075146Z.json").read_text(encoding="utf-8"))
initial = json.loads((evidence / "TC-014-offline-assignment-alt-20261026T075420Z.json").read_text(encoding="utf-8"))
run = json.loads((evidence / "TC-014-offline-assignment-alt-20261026T075511Z.json").read_text(encoding="utf-8"))
assert flight["offlineSelection"]["httpStatus"] == 400
assert flight["taskCountAfterOfflineSelection"] == flight["beforeTaskCount"]
assert flight["alternativeSelection"]["httpStatus"] == 200
assert flight["taskStatus"] == "FAILED" and flight["commandRows"] == []
assert flight["restore"]["displayAgent"]["onlineStatus"] == "ONLINE"
assert initial["restore"]["alternativeDeviceStatus"] == "DELETED"
assert initial["restore"]["alternativeSimulatorStopped"]
assert initial["restore"]["originalAgent"]["onlineStatus"] == "ONLINE"
assert run["connectionTest"]["result"] == "PASSED"
assert run["alternativeCapabilityCreated"] == "UNTESTED"
assert run["alternativeCapabilityTest"]["capabilityStatus"] == "TESTED_PASSED"
assert run["alternativeCapabilityEnabled"] == "ENABLED"
assert run["offlineAgentAtSelection"]["onlineStatus"] == "OFFLINE"
assert run["alternativeAgentAtSelection"]["onlineStatus"] == "ONLINE"
assert run["offlineSelection"]["httpStatus"] == 400
assert run["taskCountAfterOfflineReject"] == run["beforeTaskCount"]
assert run["alternativeSelection"]["httpStatus"] == 200
assert run["afterTaskCount"] == run["beforeTaskCount"] + 1
assert run["taskStatus"] == "COMPLETED" and run["dryRunResult"]["result"] == "SUCCESS"
assert run["selectionRows"] == [run["alternativeAgentCode"] + "|1"]
assert run["commandRows"] == [run["alternativeAgentCode"] + "|TASK_ACCEPT|ACCEPTED",
                               run["alternativeAgentCode"] + "|EXECUTE_CAPABILITY|SUCCEEDED"]
assert run["afterOfflineCommandCount"] == run["beforeOfflineCommandCount"]
assert run["restore"]["templateStatus"] == "DISABLED"
assert run["restore"]["alternativeDeviceStatus"] == "DELETED"
assert run["restore"]["alternativeSimulatorStopped"]
assert run["restore"]["originalAgent"]["onlineStatus"] == "ONLINE"
refs = ";".join("acceptance/stage3/evidence/" + name for name in [
    "TC-014-offline-assignment-20261026T075146Z.json",
    "TC-014-offline-assignment-alt-20261026T075420Z.json",
    "TC-014-offline-assignment-alt-20261026T075511Z.json"])

path = stage / "rules.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(row for row in rows if row["ruleId"] == "SRS_F005.R04")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-014.S2", evidence=refs)
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

path = stage / "steps.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(row for row in rows if row["stepId"] == "TC-014.S2")
assert row["status"] == "F" and "NT-S3-010" in row["issue"]
row["actual"] = row["actual"].replace("新任务分配拒绝分支尚未实测",
    "新任务分配保护已补证：离线航显强制选择400且不建任务；同类型在线备用航显执行任务59完成，两条指令均发给备用代理，离线代理指令数未增加")
row["issue"] = "DEF-S3-047;DEF-S3-048"
row["evidence"] += ";" + refs
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

path = stage / "issues.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(row for row in rows if row["编号"] == "NT-S3-010")
assert row["状态"] == "待补分支"
row.update(状态="已补证", 事实="离线航显强制分配被400拒绝且不建任务；同类型在线备用航显完成任务59，两条指令均属备用代理，离线代理无新增指令",
           证据=row["证据"] + ";" + refs)
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print("recorded SRS_F005.R04 P, NT-S3-010 closed; TC-014.S2 remains F")
