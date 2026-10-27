"""Record SRS_F010.R06 from the preserved synthetic identity canary task."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
file = stage / "evidence/TC-031-identity-canary-20261026T035059Z.json"
data = json.loads(file.read_text(encoding="utf-8"))
assert data["runtimeInput"] == "V1.5" and data["schema"] == "tip_stage2_v14"
assert data["task"]["status"] == "COMPLETED"
for key, value in data["canaries"].items():
    assert key in ("passengerName", "identityDocumentNumber")
    assert data["request"]["sceneParams"][key] == value
    assert data["task"]["sceneParams"][key] == value
    assert value not in data["task"]["taskGoal"]

rules_file = stage / "rules.csv"
with rules_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["ruleId"] == "SRS_F010.R06")
assert row["status"] == "NOT_RUN"
row.update(status="F", verifiedBy="TC-031.S2",
           evidence="acceptance/stage3/evidence/" + file.name, issue="DEF-S3-032")
with rules_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
assert "281 条需求规则为 P 92、F 42、NT 11、未执行 136" in body
body = body.replace("281 条需求规则为 P 92、F 42、NT 11、未执行 136",
                    "281 条需求规则为 P 92、F 43、NT 11、未执行 135", 1)
heading = "## 已执行\n\n"
assert heading in body
note = ("- `SRS_F010.R06`：复核本轮V1.5任务46的虚构身份字段金丝雀。"
        "操作员提交时`passengerName`和`identityDocumentNumber`只在`sceneParams`中，"
        "不在原始目标；任务完成后两字段仍原样保存在任务详情，违反不保存身份信息的要求。"
        "规则判F，复用`DEF-S3-032`。这项测试使用纯虚构标记，不涉及真实旅客。"
        "上下文和事件中未见两标记，不由本证据扩展判定脱敏/追溯规则。"
        "见`evidence/TC-031-identity-canary-20261026T035059Z.json`。\n")
body = body.replace(heading, heading + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 09:34（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded SRS_F010.R06 F")
