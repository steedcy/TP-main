"""Record TC-012.S3 from the fresh agent lifecycle audit."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
files = sorted((stage / "evidence").glob("TC-012-agent-audit-20*.json"))
assert len(files) == 1, files
ev = json.loads(files[0].read_text(encoding="utf-8"))
assert ev["connectionTest"]["result"] == "PASSED"
assert ev["createdAgent"]["agentStatus"] == "ENABLED"
assert ev["afterDisable"]["agentStatus"] == "DISABLED"
assert ev["reenabledAgent"]["agentStatus"] == "ENABLED"
assert ev["createdAgent"]["agentId"] == ev["reenabledAgent"]["agentId"]
assert ev["afterDeleteDevice"] == "DELETED"
assert ev["afterArchive"]["agentStatus"] == "ARCHIVED"
assert ev["archiveReenableRejected"] and ev["afterRejectedReenable"] == "ARCHIVED"
assert ev["cleanup"] == {"deviceStatus": "DELETED", "simulatorStopped": True}
logs = [row["operationType"] for row in ev["agentOperationLogs"]]
events = ev["deviceEventTypes"]
assert "DEVICE_AGENT_CREATE" in logs and "DEVICE_AGENT_DISABLE" in logs
assert not any("ENABLE" in name or "ARCHIVE" in name for name in logs)
assert all(name in events for name in ["AGENT_CREATED", "AGENT_DISABLED", "AGENT_ARCHIVED"])
assert "AGENT_ENABLED" not in events
assert any(row["operationType"] == "DEVICE_DELETE" for row in ev["deviceOperationLogs"])
ref = "acceptance/stage3/evidence/" + files[0].name
today = datetime.now().astimezone().date().isoformat()


def update(name, key, target, change):
    path = stage / name
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    row = next(row for row in rows if row[key] == target)
    change(row)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def step012s2(row):
    assert row["status"] == "F" and row["issue"] == "DEF-S3-021"
    row["actual"] += "；后续独立临时代理随设备删除被归档且归档后重新启用被拒，删除分支已补证"
    row["evidence"] += ";" + ref


def step012s3(row):
    assert row["status"] == "NOT_RUN"
    row.update(status="F", observedAt=today,
               actual="同一临时代理创建、显式停用、重新启用、设备删除归档均实测；代理操作日志只有创建与停用，重新启用与归档无代理操作类型。设备事件有创建/停用/归档及运行时绑定，无明确启用事件",
               evidence=ref, issue="DEF-S3-040")


update("steps.csv", "stepId", "TC-012.S2", step012s2)
update("steps.csv", "stepId", "TC-012.S3", step012s3)


def rule(row):
    assert row["status"] == "NOT_RUN"
    row.update(status="F", verifiedBy="TC-012.S3", evidence=ref, issue="DEF-S3-040")


update("rules.csv", "ruleId", "SRS_F004.R08", rule)
issues = stage / "issues.csv"
with issues.open(encoding="utf-8-sig", newline="") as stream:
    assert "DEF-S3-040" not in {row["编号"] for row in csv.DictReader(stream)}
with issues.open("a", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["DEF-S3-040", "缺陷", "中", "TC-012.S3", "SRS_F004.R08", "待修复",
                     "代理创建、停用有代理操作日志和设备事件；同一代理重新启用没有启用操作日志/明确启用事件，随设备删除归档只有设备删除操作日志和代理归档事件，无代理归档操作日志",
                     ref, "补齐代理重新启用与归档的专属操作日志和设备事件，复测四种状态变化及历史追溯"])
print("recorded TC-012.S3, updated S2, and DEF-S3-040")
