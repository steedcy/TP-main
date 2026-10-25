"""Record TC-069 conclusions supported by live API and browser evidence."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
evidence = stage / "evidence"
api = json.loads((evidence / "TC-069-preset-definitions.json").read_text(encoding="utf-8"))
restore = json.loads((evidence / "TC-069-preset-exact-restore.json").read_text(encoding="utf-8"))
ui = json.loads((evidence / "TC-069-preset-ui.json").read_text(encoding="utf-8"))
assert all("error" in attempt for attempt in api["deletionAttempts"])
assert all(item["deleteButtonDisabled"] for item in ui["presets"])
assert api["edit"]["detailDuringEdit"]["sceneParams"][-1]["name"] == "stage3OptionalProbe"
assert restore["configurationMatchesOriginal"]
assert all("error" in api["validation"][k] for k in
           ["duplicateName", "emptyParams", "emptyCapabilities", "unknownCapability"])
assert api["validation"]["blankConstraint"]["http"] == 200
assert api["validation"]["blankConstraint"]["deletedAfterProbe"]
day = datetime.now().astimezone().date().isoformat()
refs = ";".join("acceptance/stage3/evidence/" + filename for filename in [
    "TC-069-preset-definitions.json", "TC-069-preset-exact-restore.json",
    "TC-069-preset-ui.json", "TC-069-preset-list.png", "TC-069-preset-editor.png"])

def update(name, key, changes):
    path = stage / name
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields, rows = reader.fieldnames, list(reader)
    for row in rows:
        if row[key] in changes:
            assert row["status"] == "NOT_RUN"
            row.update(changes[row[key]])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

update("steps.csv", "stepId", {
    "TC-069.S1": {"status": "P", "observedAt": day,
        "actual": "三预置族均显示预置标识、删除按钮禁用且API删除拒绝；行李族场景参数及约束可编辑，复原后与原配置逐字段一致",
        "evidence": refs, "issue": ""},
    "TC-069.S2": {"status": "F", "observedAt": day,
        "actual": "重复名、空参数、空能力和未知能力均拒绝；空约束仍200创建定义，已删除；未启用能力实例分支仍待单测",
        "evidence": refs, "issue": "DEF-S3-030"},
})
update("rules.csv", "ruleId", {
    "SRS_F022.R01": {"status": "P", "verifiedBy": "TC-069.S1", "evidence": refs, "issue": ""},
})
path = stage / "issues.csv"
with path.open(encoding="utf-8-sig", newline="") as handle:
    reader = csv.DictReader(handle)
    fields, rows = reader.fieldnames, list(reader)
issue = next(row for row in rows if row["编号"] == "DEF-S3-030")
issue["关联用例步骤"] += ";TC-069.S2"
issue["证据"] += ";acceptance/stage3/evidence/TC-069-preset-definitions.json"
with path.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print("recorded TC-069.S1/S2, SRS_F022.R01 and linked DEF-S3-030")
