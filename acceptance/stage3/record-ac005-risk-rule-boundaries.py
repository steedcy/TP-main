"""Classify AC-005 using the preserved V1.5 risk-rule CRUD evidence."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
ev = stage / "evidence"
crud_file = ev / "TC-043-risk-rule-crud-20261026T071245Z.json"
audit_file = ev / "TC-043-risk-rule-audit-followup-20261026T071344Z.json"
crud = json.loads(crud_file.read_text(encoding="utf-8"))
audit = json.loads(audit_file.read_text(encoding="utf-8"))
assert crud["runtimeInput"] == audit["runtimeInput"] == "V1.5"
assert crud["isolatedSchema"] == "tip_stage2_v14"
assert crud["boundary"]["emptyCode"]["httpStatus"] == 200
assert crud["boundary"]["emptyContent"]["httpStatus"] == 200
assert crud["boundary"]["missingCode"]["httpStatus"] == 500
assert crud["boundary"]["missingContent"]["httpStatus"] == 500
assert crud["duplicate"]["httpStatus"] == 409
assert ([crud[name]["ruleVersion"] for name in
         ("created", "afterContentUpdate", "afterEnable", "afterDisable")]
        == ["V1.0", "V1.1", "V1.1", "V1.1"])
assert len(audit["changeLogs"]) == 4
assert all(log["operationType"] == "RISK_RULE_CHANGE" and log["detail"]
           for log in audit["changeLogs"])
assert crud["cleanup"]["temporaryCodesRemaining"] == []
assert set(audit["remainingCodes"]) == set(audit["beforeCodes"])

file = stage / "ac.csv"
with file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["acId"] == "AC-005")
assert row["status"] == "NOT_RUN"
row.update(status="F", observedAt=datetime.now().strftime("%Y-%m-%d"),
           actual="本轮V1.5隔离规则API接受空编号/空内容并持久化，缺字段返回500；重复编号409。内容修改V1.0→V1.1，但启用/停用版本均停在V1.1。四条变更审计含前后摘要，临时规则已清理。后续计划使用启用规则版本的正向判定仍待TC-043.S2执行。",
           evidence="acceptance/stage3/evidence/" + crud_file.name + ";acceptance/stage3/evidence/" + audit_file.name,
           issue="DEF-S3-041;DEF-S3-043")
with file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
assert "27 项 AC 为 F 5、NT 1、未执行 21" in body
body = body.replace("27 项 AC 为 F 5、NT 1、未执行 21",
                    "27 项 AC 为 F 6、NT 1、未执行 20", 1)
heading = "## 已执行\n\n"
assert heading in body
note = ("- AC-005依阶段3同一V1.5运行输入的原始规则CRUD/API/审计证据补登F：空编号和"
        "空内容被HTTP200保存、缺字段HTTP500，重复编号409；内容更新V1.0→V1.1，"
        "启停均未递增版本；四条变更审计详情含前后摘要，临时规则清理后恢复三条。"
        "复用既有`DEF-S3-041/043`，不把TC-043.S2后续风险判定当作已执行。"
        "证据见`evidence/TC-043-risk-rule-crud-20261026T071245Z.json`及"
        "`evidence/TC-043-risk-rule-audit-followup-20261026T071344Z.json`。\n")
body = body.replace(heading, heading + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 09:29（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded AC-005 F from preserved V1.5 evidence")
