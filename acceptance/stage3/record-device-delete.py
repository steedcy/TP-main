"""Record TC-010.S3 from the successful browser retry and audit evidence."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
evidence = stage / "evidence"
files = sorted(evidence.glob("TC-010-device-delete-20*.json"))
assert len(files) == 2, files  # Preserve the first browser-selector failure.
first = json.loads(files[0].read_text(encoding="utf-8"))
ev = json.loads(files[1].read_text(encoding="utf-8"))
ui = json.loads((evidence / "TC-010-device-delete-ui.json").read_text(encoding="utf-8"))
assert first["browserExitCode"] != 0 and first["cleanup"]["deviceStatus"] == "DELETED"
assert first["deviceCode"] != ev["deviceCode"]
assert ev["browserExitCode"] == 0 and ev["taskIdBeforeDelete"] is None
assert ev["connectionTest"]["result"] == "PASSED"
assert ev["afterDisable"] == {"deviceStatus": "INACTIVE", "agentStatus": "DISABLED"}
assert ev["afterEnable"]["deviceStatus"] == "ACTIVE"
assert ev["afterConfirmDevice"]["deviceStatus"] == "DELETED"
assert ev["afterConfirmAgent"]["agentStatus"] == "ARCHIVED"
assert not ev["activeListContainsDevice"]
assert ev["cleanup"]["deviceStatus"] == "DELETED" and ev["cleanup"]["simulatorStopped"]
assert ui["deviceCode"] == ev["deviceCode"]
assert ui["presentAfterCancel"] and ui["deleteRequestsAfterCancel"] == 0
assert ui["deleteRequestsAfterConfirm"] == 1
assert ui["deleteHttpStatus"] == 200 and not ui["presentAfterConfirm"]
types = [row["operationType"] for row in ev["operationLogs"]]
assert all(types.count(name) >= count for name, count in {
    "DEVICE_CREATE": 1, "DEVICE_UPDATE": 1, "DEVICE_STATUS_CHANGE": 2,
    "DEVICE_DELETE": 1}.items())
refs = ";".join("acceptance/stage3/evidence/" + name for name in [
    files[0].name, files[1].name, "TC-010-device-delete-ui.json",
    "TC-010-delete-before.png", "TC-010-delete-cancel.png",
    "TC-010-delete-confirmed.png"])
today = datetime.now().astimezone().date().isoformat()


def update(name, key, target, values):
    path = stage / name
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    row = next(row for row in rows if row[key] == target)
    assert row["status"] == "NOT_RUN"
    row.update(values)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


update("steps.csv", "stepId", "TC-010.S3", {
    "status": "P", "observedAt": today,
    "actual": "无占用临时设备在Chrome先取消删除，列表保留且无DELETE请求；再次确认后DELETE 200并退出活动列表，设备软删除、代理归档且可查历史；新增、修改、停用、启用、删除各有操作记录。首次浏览器定位失败已保留并清理，与产品结果区分",
    "evidence": refs})
update("rules.csv", "ruleId", "SRS_F003.R07", {
    "status": "P", "verifiedBy": "TC-010.S3", "evidence": refs})
print("recorded TC-010.S3 and SRS_F003.R07")
