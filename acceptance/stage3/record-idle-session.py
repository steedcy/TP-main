"""Record the real 31-minute idle-session and reauthentication result."""
import csv
import json
from pathlib import Path

here = Path(__file__).resolve().parent
ev = json.loads((here / "evidence/TC-087-idle-session.json").read_text(encoding="utf-8"))
assert ev["status"] == "PASS" and ev["idleElapsedMs"] >= 31 * 60 * 1000
assert ev["apiRequestsDuringIdle"] == 0 and ev["expiredHttpStatus"] == 401
assert ev["redirectedToLogin"] and ev["expiryPromptShown"]
assert ev["oldTokenAfterExpiryStatus"] == 401 and ev["oldTokenStillInvalid"]
assert ev["reauthenticated"] and ev["newTokenWorks"]


def update(name, key, targets):
    path = here / name
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        if row[key] in targets:
            assert row["status"] == "NOT_RUN", row[key]
            row.update(targets[row[key]])
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


file = "acceptance/stage3/evidence/TC-087-idle-session.json"
update("steps.csv", "stepId", {
    "TC-087.S1": {"status": "P", "observedAt": "2026-10-25",
                  "actual": "Chrome页面无API活动空闲31分钟；再次查询返回401，跳转登录并提示重新登录，旧令牌仍401",
                  "evidence": file + ";acceptance/stage3/evidence/TC-087-expired.png"},
    "TC-087.S2": {"status": "P", "observedAt": "2026-10-25",
                  "actual": "重新认证后新令牌可执行授权操作，旧令牌仍401",
                  "evidence": file + ";acceptance/stage3/evidence/TC-087-after-relogin.png"},
})
update("rules.csv", "ruleId", {
    "SRS_F001.R02": {"status": "P", "verifiedBy": "TC-087.S1", "evidence": file},
    "SRS_NF002.R01": {"status": "P", "verifiedBy": "TC-087.S1", "evidence": file},
})
