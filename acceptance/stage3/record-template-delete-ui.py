"""Close TC-019.S3 after browser cancel/confirm, API removal, and audit."""
import csv
import json
from pathlib import Path

here = Path(__file__).resolve().parent
ev = json.loads((here / "evidence/TC-019-unused-delete.json").read_text(encoding="utf-8"))
assert ev["createdUsageCount"] == 0 and ev["rowVisibleBefore"]
assert ev["confirmPromptVisible"] and ev["rowVisibleAfterCancel"]
assert ev["rowAbsentAfterConfirm"] and ev["apiAbsentAfter"] and ev["deleteAuditPresent"]
assert ev["confirmButtonLabels"] == ["Cancel", "OK"]


def read(name):
    with (here / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(name, rows):
    with (here / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


files = ("acceptance/stage3/evidence/TC-019-unused-delete.json;"
         "acceptance/stage3/evidence/TC-019-unused-after-cancel.png;"
         "acceptance/stage3/evidence/TC-019-unused-after-delete.png")
steps = read("steps.csv")
for row in steps:
    if row["stepId"] == "TC-019.S3":
        assert row["status"] == "NT" and row["issue"] == "NT-S3-012"
        row.update(status="P", observedAt="2026-10-26", issue="",
                   actual="未使用模板usageCount=0；浏览器取消删除仍在列表，确认后消失；API不再返回该编码且有成功删除操作审计",
                   evidence=row["evidence"] + ";" + files)
write("steps.csv", steps)

issues = read("issues.csv")
for row in issues:
    if row["编号"] == "NT-S3-012":
        row["状态"] = "已补证"
        row["事实"] = "TC-019.S3浏览器取消/确认、API删除及操作审计均已补证，步骤改判P"
        row["证据"] += ";" + files
write("issues.csv", issues)
