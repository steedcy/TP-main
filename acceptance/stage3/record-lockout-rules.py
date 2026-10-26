"""Classify F001.R07-R09 from actual lockout, UI, and persisted audit."""
import csv
import json
from pathlib import Path

stage = Path(__file__).resolve().parent
prior = json.loads((stage / "evidence/TC-002-lockout.json").read_text(encoding="utf-8"))
ui = json.loads((stage / "evidence/TC-002-login-ui.json").read_text(encoding="utf-8"))
runs = list((stage / "evidence").glob("TC-002-lockout-audit-followup-*.json"))
assert len(runs) == 1
audit = json.loads(runs[0].read_text(encoding="utf-8"))
checks = prior["checks"]
assert [row["state"]["failedLoginAttempts"] for row in checks["aFailures"]] == [1, 2, 3]
assert [row["state"]["status"] for row in checks["aFailures"]] == [
    "ACTIVE", "ACTIVE", "LOCKED"]
assert checks["lockedCorrectPassword"]["sessionCreated"] is False
assert ui["pass"] and all(row["unifiedPrompt"] and row["noSessionToken"]
                          for row in ui["attempts"])
assert checks["afterUnlock"] == {"status": "ACTIVE", "failedLoginAttempts": 0}
assert checks["correctAfterTwoFailures"]["sessionCreated"]
assert checks["afterCorrect"]["failedLoginAttempts"] == 0
assert checks["afterOneMoreWrong"]["failedLoginAttempts"] == 1
rows = audit["rows"]
assert len([r for r in rows if r["operationType"] == "LOGIN"
            and r["result"] == "FAILED"]) >= 3
assert any(r["operationType"] == "MANUAL_HANDLING"
           and r["operationTarget"] == audit["account"] for r in rows)
assert not any("LOCK" in r["operationType"] or "LOCK" in r["detail"].upper()
               for r in rows)
assert all(r["createdAt"] and r["sourceIp"] for r in rows)
assert not checks["audit"]["containsPassword"]

path = stage / "rules.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rules = reader.fieldnames, list(reader)
for rid, status, issue, refs in [
    ("SRS_F001.R07", "P", "", ["TC-002-lockout.json", "TC-002-login-ui.json"]),
    ("SRS_F001.R08", "P", "", ["TC-002-lockout.json"]),
    ("SRS_F001.R09", "F", "DEF-S3-056", ["TC-002-lockout.json", runs[0].name])]:
    row = next(r for r in rules if r["ruleId"] == rid)
    assert row["status"] == "NOT_RUN"
    row.update(status=status, verifiedBy="TC-002.S2;TC-002.S3",
               evidence=";".join("acceptance/stage3/evidence/" + name for name in refs),
               issue=issue)
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rules)

issues = stage / "issues.csv"
with issues.open(encoding="utf-8-sig", newline="") as stream:
    assert "DEF-S3-056" not in {r["编号"] for r in csv.DictReader(stream)}
with issues.open("a", encoding="utf-8", newline="") as stream:
    csv.writer(stream, lineterminator="\n").writerow([
        "DEF-S3-056", "缺陷", "中", "TC-002.S3", "SRS_F001.R09", "待修复",
        "本轮临时账号连续第三次错密后状态变LOCKED；持久化操作日志仅有LOGIN/FAILED，没有独立的账号锁定操作类型或包含锁定结果的详情，无法从操作记录识别哪次失败导致锁定。管理员解锁有MANUAL_HANDLING及目标账号，失败记录无密码原值。",
        "acceptance/stage3/evidence/TC-002-lockout.json;acceptance/stage3/evidence/" + runs[0].name,
        "为达到阈值的账号锁定写明确的账号锁定操作记录或结构化状态详情；复测失败、锁定、管理员解锁的账号时间IP和脱敏"])
print("recorded SRS_F001.R07/R08 P, R09 F, DEF-S3-056")
