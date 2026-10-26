"""Record TC-036.S1 only after real and instrumented all-required-gap runs."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
names = ["TC-036-capability-gap-20261026T033200Z.json",
         "TC-036-capability-gap-20261026T033358Z.json"]
actual, fixture = [json.loads((stage / "evidence" / name).read_text(encoding="utf-8"))
                   for name in names]
required = {"CAP_BAGGAGE_MEASURE", "CAP_OVERSIZE_ALERT", "CAP_NAVIGATION", "CAP_NOTIFICATION"}
for run in [actual, fixture]:
    assert run["schema"] == "tip_stage2_v14"
    assert set(run["snapshot"]["coverage"]["missing"]) == required
    assert run["snapshot"]["coverage"]["available"] == []
    assert any(e["reasonCode"] == "ERR_CAPABILITY_GAP_ALL_MISSING"
               for e in run["task"]["events"])
    assert run["task"]["final"]["status"] == "PENDING_MANUAL"
    assert all(v["source"] != "AUTONOMOUS" for v in run["task"]["planVersions"])
    assert run["restore"]["exact"] and run["restore"]["allSixOnlineIdle"]
assert [r["phase"] for r in fixture["modelFixture"]["newRequests"]] == ["goal"]
refs = ";".join("acceptance/stage3/evidence/" + name for name in names)
day = datetime.now().astimezone().date().isoformat()

def update(name, key, changes):
    path = stage / name
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    for row in rows:
        if row[key] in changes:
            assert row["status"] == "NOT_RUN", row[key]
            row.update(changes[row[key]])
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

update("steps.csv", "stepId", {"TC-036.S1": {
    "status": "P", "observedAt": day,
    "actual": "任务44/45全部四类必需能力缺失，初始上下文记录完整缺口并产生ERR_CAPABILITY_GAP_ALL_MISSING；无自主计划/设备指令，基线校验失败转PENDING_MANUAL；受控模型日志仅1次目标理解请求、0次规划请求；状态均恢复",
    "evidence": refs, "issue": ""}})
update("rules.csv", "ruleId", {"SRS_F011.R07": {
    "status": "P", "verifiedBy": "TC-036.S1", "evidence": refs, "issue": ""}})
print("recorded TC-036.S1 and SRS_F011.R07")
