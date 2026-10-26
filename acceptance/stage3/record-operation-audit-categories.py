"""Record F028.R01/R04 from fresh operation-log category samples."""
import csv
import json
from pathlib import Path

stage = Path(__file__).resolve().parent
evidence = stage / "evidence/SRS_F028-audit-categories-20261026T224509Z.json"
data = json.loads(evidence.read_text(encoding="utf-8"))
s = data["samples"]
assert data["runtimeInput"] == "V1.5" and data["isolatedSchema"] == "tip_stage2_v14"
assert s["loginSuccess"]["operationType"] == "LOGIN" and s["loginSuccess"]["operationResult"] == "SUCCESS"
assert s["loginFailure"]["operationType"] == "LOGIN" and s["loginFailure"]["operationResult"] == "FAILED"
assert s["deviceConfig"]["operationType"] == "DEVICE_CREATE"
assert s["capabilityEnable"]["operationType"] == s["capabilityDisable"]["operationType"] == "DEVICE_CAPABILITY_STATUS_CHANGE"
assert s["capabilityEnable"]["operationTarget"].endswith(" -> ENABLED")
assert s["capabilityDisable"]["operationTarget"].endswith(" -> DISABLED")
assert s["templateEnable"]["operationType"] == "BASELINE_TEMPLATE_ENABLE"
assert s["templateDisable"]["operationType"] == "BASELINE_TEMPLATE_DISABLE"
assert s["manualTerminate"]["operationType"] == "TASK_TERMINATE"
assert s["manualTerminate"]["operationTarget"] == "TASK-20261027-0064"
assert s["accessDenied"]["operationType"] == "ACCESS_DENIED"
assert s["accessDenied"]["operationResult"] == "FAILED"
assert s["accessDenied"]["operationTarget"] == "/api/v1/tasks/19/events"
assert all(row["createdAt"] >= "2026-10-25" for row in s.values())
assert all(row["id"] > 0 for row in s.values())

rule_path = stage / "rules.csv"
with rule_path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
for key in ("SRS_F028.R01", "SRS_F028.R04"):
    row = next(r for r in rows if r["ruleId"] == key)
    assert row["status"] == "NOT_RUN"
    row.update(status="P", verifiedBy="TC-085.S1",
               evidence="acceptance/stage3/evidence/" + evidence.name, issue="")
with rule_path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
body = body.replace("P 85、F 39、NT 10、未执行 147", "P 87、F 39、NT 10、未执行 145", 1)
heading = "## 已执行\n\n"
assert heading in body
note = ("- `SRS_F028.R01/R04`：本轮系统管理员操作记录API重新读取阶段3产生的登录成功/失败、设备新增、"
        "能力启停、模板启停及任务64人工终止记录，各类都有持久化记录；配置管理员越权访问任务19事件"
        "也有`ACCESS_DENIED/FAILED`记录。因此两条规则判P。任务定义、风险规则及待人工处置的组合审计"
        "尚未依`R02`完整复核；TC-085.S1原有变更摘要缺失的F不变。原始采样见"
        "`evidence/SRS_F028-audit-categories-20261026T224509Z.json`。\n")
body = body.replace(heading, heading + note, 1)
body = body.replace("2026-10-27 06:43（Asia/Shanghai）", "2026-10-27 06:45（Asia/Shanghai）", 1)
progress.write_text(body, encoding="utf-8")
print("recorded SRS_F028.R01/R04 P; TC-085.S1 unchanged")
