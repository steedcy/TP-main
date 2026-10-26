"""Record event immutability and unsupported-route error response."""
import csv
import json
from pathlib import Path

stage = Path(__file__).resolve().parent
runs = list((stage / "evidence").glob("TC-084-trace-immutability-*.json"))
assert len(runs) == 1
ev = json.loads(runs[0].read_text(encoding="utf-8"))
assert {a["method"] for a in ev["attempts"]} == {"PUT", "DELETE"}
assert all(not a["accepted"] and "HTTP 500" in a["error"] for a in ev["attempts"])
assert ev["before"]["count"] == ev["after"]["count"] == 27
assert ev["before"]["sha256"] == ev["after"]["sha256"]
assert ev["after"]["eventStillPresent"] and ev["after"]["injectedTextAbsent"]
ref = "acceptance/stage3/evidence/" + runs[0].name
path = stage / "rules.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["ruleId"] == "SRS_F027.R03")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-084.S2", evidence=ref)
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
issues = stage / "issues.csv"
with issues.open(encoding="utf-8-sig", newline="") as stream:
    assert "DEF-S3-058" not in {r["编号"] for r in csv.DictReader(stream)}
with issues.open("a", encoding="utf-8", newline="") as stream:
    csv.writer(stream, lineterminator="\n").writerow([
        "DEF-S3-058", "缺陷", "低", "TC-084.S2", "", "待修复",
        "运行操作员对任务19真实事件PUT和DELETE均未修改记录，27条事件内容哈希前后一致；但不支持的/events/{eventId}写路径返回HTTP500系统繁忙，而非明确的404或405，误报服务内部故障。",
        ref, "不支持的事件写路径返回明确404/405且保持事件不可变；复测API响应与原事件哈希"])
print("recorded SRS_F027.R03 P and DEF-S3-058")
