"""Record the isolated 20-object access limit and fixture cleanup."""
import csv
import json
from pathlib import Path

here = Path(__file__).resolve().parent
ev = json.loads((here / "evidence/TC-008-limit.json").read_text(encoding="utf-8"))
assert ev["beforeCount"] + ev["temporaryCreated"] == 20 == ev["atLimitCount"]
assert ev["httpStatus"] == 409 and ev["responseCode"] == 4208
assert "20" in ev["responseMessage"] and not ev["newCodePresentAfter"]
assert ev["postCleanupCount"] == ev["beforeCount"] and not ev["cleanupErrors"]


def read(name):
    with (here / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(name, rows):
    with (here / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


steps = read("steps.csv")
for row in steps:
    if row["stepId"] == "TC-008.S3":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", observedAt="2026-10-25",
                   actual="隔离库活动对象6个，临时创建14个达20；第21个合法对象返回409及上限20提示，数量仍20；清理14个后恢复6个",
                   evidence="acceptance/stage3/evidence/TC-008-limit.json")
write("steps.csv", steps)

rules = read("rules.csv")
for row in rules:
    if row["ruleId"] == "SRS_F003.R05":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", verifiedBy="TC-008.S3",
                   evidence="acceptance/stage3/evidence/TC-008-limit.json")
write("rules.csv", rules)
