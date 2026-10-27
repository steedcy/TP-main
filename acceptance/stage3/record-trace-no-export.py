"""Record the V1.5 trace page's out-of-scope export/report check."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
file = stage / "evidence/SRS_F027-R07-no-export-task19.json"
data = json.loads(file.read_text(encoding="utf-8"))
assert data["runtimeInput"] == "V1.5" and data["browser"] == "Chrome"
assert data["route"] == "/task-trace" and data["traceEventCount"] == 27
assert data["exportOrReportControls"] == 0
assert all(not any(label in text for label in ("导出", "评测报告", "生成报告"))
           for text in data["buttonsBefore"] + data["buttonsAfter"] +
           data["anchorTextsAfter"])
rules_file = stage / "rules.csv"
with rules_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["ruleId"] == "SRS_F027.R07")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-084.S2",
           evidence="acceptance/stage3/evidence/" + file.name +
           ";acceptance/stage3/evidence/SRS_F027-R07-no-export-task19.png", issue="")
with rules_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
assert "281 条需求规则为 P 91、F 42、NT 11、未执行 137" in body
body = body.replace("281 条需求规则为 P 91、F 42、NT 11、未执行 137",
                    "281 条需求规则为 P 92、F 42、NT 11、未执行 136", 1)
heading = "## 已执行\n\n"
assert heading in body
note = ("- `SRS_F027.R07`：Chrome运行操作员进入过程追溯并展开任务19的27条事件，"
        "页面和侧边菜单没有研究记录导出或评测报告入口；本期排除功能规则判P。"
        "这不代替TC-084.S2其他隐私、原因码与完整追溯分支。截图与DOM证据见"
        "`evidence/SRS_F027-R07-no-export-task19.json`及同名PNG。\n")
body = body.replace(heading, heading + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 09:32（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded SRS_F027.R07 P")
