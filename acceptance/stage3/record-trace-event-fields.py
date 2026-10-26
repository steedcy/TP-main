"""Record missing reason codes across a complete task timeline."""
import csv
import json
from pathlib import Path

stage = Path(__file__).resolve().parent
runs = list((stage / "evidence").glob("TC-084-trace-event-fields-*.json"))
assert len(runs) == 1
ev = json.loads(runs[0].read_text(encoding="utf-8"))
assert ev["taskStatus"] == "COMPLETED"
assert ev["summary"] == {"count": 27, "missingReasonCode": 26,
                         "completeOtherFields": True}
assert all(e["taskId"] == 19 for e in ev["events"])
ref = "acceptance/stage3/evidence/" + runs[0].name
path = stage / "rules.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["ruleId"] == "SRS_F027.R02")
assert row["status"] == "NOT_RUN"
row.update(status="F", verifiedBy="TC-084.S2", evidence=ref,
           issue="DEF-S3-057")
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
issues = stage / "issues.csv"
with issues.open(encoding="utf-8-sig", newline="") as stream:
    assert "DEF-S3-057" not in {r["编号"] for r in csv.DictReader(stream)}
with issues.open("a", encoding="utf-8", newline="") as stream:
    csv.writer(stream, lineterminator="\n").writerow([
        "DEF-S3-057", "缺陷", "中", "TC-084.S2", "SRS_F027.R02", "待修复",
        "隔离任务19已完成且保存27条完整时间线；事件均有类型、发生时间、触发方和摘要，但26条reasonCode为空，包括目标提交、规划、分配、派发、步骤完成与任务完成。未满足逐条携带原因码的规则；成功反馈缺码还见DEF-S3-053。",
        ref, "为追溯事件定义并写入原因码，或先由需求裁决明确无需原因码的事件类型例外，再逐类重测完整时间线"])
print("recorded SRS_F027.R02 F and DEF-S3-057")
