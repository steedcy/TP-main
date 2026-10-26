"""Record F028.R05 P and the unsupported write-route HTTP 500 defect."""
import csv
import json
from pathlib import Path

stage = Path(__file__).resolve().parent
ev = stage / "evidence"
file = ev / "SRS_F028-audit-immutability-20261026T224625Z.json"
data = json.loads(file.read_text(encoding="utf-8"))
ui = json.loads((ev / "TC-085-operation-log.json").read_text(encoding="utf-8"))
assert data["runtimeInput"] == ui["runtimeInput"] == "V1.5"
assert data["target"] == "TASK-20261027-0064" and data["operationType"] == "TASK_TERMINATE"
assert data["before"] == {key: data["after"][key] for key in
                           ("sha256", "createdAt", "operationResult")}
assert data["after"]["injectedTextAbsent"]
assert len(data["attempts"]) == 2
assert {row["method"] for row in data["attempts"]} == {"PUT", "DELETE"}
assert all(not row["accepted"] and "HTTP 500" in row["error"] for row in data["attempts"])
assert ui["browser"]["editDeleteControls"] == 0
refs = "acceptance/stage3/evidence/" + file.name + ";acceptance/stage3/evidence/TC-085-operation-log.json"

rule_path = stage / "rules.csv"
with rule_path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["ruleId"] == "SRS_F028.R05")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-085.S2", evidence=refs, issue="")
with rule_path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

issues = stage / "issues.csv"
with issues.open(encoding="utf-8-sig", newline="") as stream:
    assert "DEF-S3-061" not in {r["编号"] for r in csv.DictReader(stream)}
with issues.open("a", encoding="utf-8", newline="") as stream:
    csv.writer(stream, lineterminator="\n").writerow([
        "DEF-S3-061", "缺陷", "低", "TC-085.S2", "", "待修复",
        "系统管理员对真实TASK_TERMINATE操作记录976尝试PUT和DELETE均未修改记录，前后哈希一致；但不支持的/operation-logs/{id}写路径返回HTTP500系统繁忙而非明确404/405，误报内部故障。",
        "acceptance/stage3/evidence/" + file.name,
        "不支持的操作记录写路径返回明确404/405且保持记录不可变；复测API响应和记录哈希。"])

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
body = body.replace("P 88、F 39、NT 10、未执行 144", "P 89、F 39、NT 10、未执行 143", 1)
heading = "## 已执行\n\n"
assert heading in body
note = ("- `SRS_F028.R05`：真实任务64的TASK_TERMINATE操作记录976经系统管理员PUT/DELETE挑战，"
        "均未接受且记录内容SHA256前后一致；Chrome记录页也无编辑删除按钮，规则判P。两个不支持的写路径"
        "返回HTTP500而非404/405，另记低优先级`DEF-S3-061`。TC-085.S2的敏感字段检查仍未穷尽，整步NT不变。"
        "证据见`evidence/SRS_F028-audit-immutability-20261026T224625Z.json`。\n")
body = body.replace(heading, heading + note, 1)
body = body.replace("2026-10-27 06:43（Asia/Shanghai）", "2026-10-27 06:46（Asia/Shanghai）", 1)
progress.write_text(body, encoding="utf-8")
print("recorded SRS_F028.R05 P and DEF-S3-061")
