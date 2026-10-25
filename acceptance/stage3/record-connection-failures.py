"""Record TC-009.S2 failure isolation and non-specific reason defect."""
import csv
import json
from pathlib import Path

here = Path(__file__).resolve().parent
ev = json.loads((here / "evidence/TC-009-connection-failures.json").read_text(encoding="utf-8"))
cases = ev["cases"]
assert set(cases) == {"UNREACHABLE", "INVALID_JSON", "TIMEOUT"}
assert all(case["testResult"] == case["savedStatus"] == "FAILED" for case in cases.values())
assert all(case["agentCreateHttpStatus"] == 400 for case in cases.values())
assert cases["UNREACHABLE"]["failureReason"] == cases["TIMEOUT"]["failureReason"]
assert ev["restoredEndpointMatches"] and ev["restoreRetestResult"] == ev["finalConnectionStatus"] == "PASSED"

path = here / "steps.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    rows = list(csv.DictReader(stream))
for row in rows:
    if row["stepId"] == "TC-009.S2":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", observedAt="2026-10-25", issue="DEF-S3-014",
                   actual="不可达、超时、非法JSON均保存FAILED且禁止创建代理；不可达与超时返回相同ResourceAccessException，未保存可区分的具体原因。原地址重测恢复PASSED",
                   evidence="acceptance/stage3/evidence/TC-009-connection-failures.json")
with path.open("w", encoding="utf-8-sig", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

path = here / "issues.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    issues = list(csv.DictReader(stream))
assert "DEF-S3-014" not in {row["编号"] for row in issues}
issues.append(dict(zip(issues[0].keys(), [
    "DEF-S3-014", "缺陷", "中", "TC-009.S2", "SRS_F003", "待修复",
    "连接测试把不可达和读超时均保存为ResourceAccessException，非法响应仅为RestClientException；不能区分各自原因",
    "acceptance/stage3/evidence/TC-009-connection-failures.json",
    "按连接拒绝、读取超时、响应格式/字段错误归因并显示；复测三分支及代理保护",
])))
with path.open("w", encoding="utf-8-sig", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=issues[0].keys())
    writer.writeheader()
    writer.writerows(issues)
