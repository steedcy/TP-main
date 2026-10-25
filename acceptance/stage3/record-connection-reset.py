"""Record TC-009.S3 from live isolated endpoint reset and restoration."""
import csv
import json
from pathlib import Path

here = Path(__file__).resolve().parent
ev = json.loads((here / "evidence/TC-009-connection-reset.json").read_text(encoding="utf-8"))
assert ev["beforeConnectionStatus"] == "PASSED"
assert ev["afterEndpointChangeStatus"] == "UNTESTED"
assert ev["agentCreateWhileUntestedHttpStatus"] == 400
assert ev["failedTestResult"] == "FAILED"
assert ev["afterRestoreBeforeTestStatus"] == "UNTESTED"
assert ev["restoredEndpointMatches"] and ev["retestResult"] == ev["finalConnectionStatus"] == "PASSED"
assert ev["credentialMaskedAfterEdit"] and ev["finalCredentialMasked"]


def update(name, key, target, fields):
    path = here / name
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        if row[key] == target:
            assert row["status"] == "NOT_RUN"
            row.update(fields)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


evidence = "acceptance/stage3/evidence/TC-009-connection-reset.json"
update("steps.csv", "stepId", "TC-009.S3", {
    "status": "P", "observedAt": "2026-10-25",
    "actual": "已通过仿真体修改接入地址后变未测试，代理创建400；坏地址测试失败；恢复原地址后仍未测试，重测通过，凭据始终掩码且原地址恢复",
    "evidence": evidence,
})
update("rules.csv", "ruleId", "SRS_F003.R08", {
    "status": "P", "verifiedBy": "TC-009.S3", "evidence": evidence,
})
