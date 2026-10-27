"""Classify SRS_F015.R06 from task 19's live API and Stage3 timeline."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
api_name = "TC-048-downgrade-detail-api-20261027T054628Z.json"
ui_name = "TC-048-downgrade-detail-ui-20261027T054601Z.json"
detail_name = "TC-063-task-detail-fields-task19.json"
api = json.loads((stage / "evidence" / api_name).read_text(encoding="utf-8"))
ui = json.loads((stage / "evidence" / ui_name).read_text(encoding="utf-8"))
detail = json.loads((stage / "evidence" / detail_name).read_text(encoding="utf-8"))
assert api["runtimeInput"] == ui["runtimeInput"] == detail["runtimeInput"] == "V1.5"
task = api["tasks"][0]
assert task["taskId"] == ui["tasks"][0]["taskId"] == detail["taskId"] == 19
assert task["task"]["downgradeReason"] in ui["tasks"][0]["header"]
original, baseline = task["plans"]
assert (original["versionNo"], original["source"]) == (1, "AUTONOMOUS")
assert (baseline["versionNo"], baseline["source"]) == (2, "BASELINE_TEMPLATE")
assert baseline["baselineTemplateId"] == task["baselineTemplate"]["id"] == 1
assert task["baselineTemplate"]["templateVersion"] == "V1.3"
timeline = detail["cards"][-1]["text"]
assert "BASELINE_DOWNGRADED" in timeline
assert task["baselineTemplate"]["templateName"] in timeline
assert task["baselineTemplate"]["templateVersion"] in timeline
assert task["task"]["downgradeReason"] in timeline
assert ui["tasks"][0]["tabs"] == ["版本1（自主规划）", "版本2（基线模板）"]
refs = ";".join("acceptance/stage3/evidence/" + name for name in
                (api_name, ui_name, detail_name))

rules_file = stage / "rules.csv"
with rules_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(item for item in rows if item["ruleId"] == "SRS_F015.R06")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-048.S2", evidence=refs)
with rules_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
old = "281 条需求规则为 P 101、F 48、NT 11、未执行 121"
assert old in body
body = body.replace(old, "281 条需求规则为 P 102、F 48、NT 11、未执行 120", 1)
note = ("- `SRS_F015.R06`：任务19同一V1.5降级实例保存自主原计划版本1、基线版本2与模板1的V1.3版本；"
        "任务降级原因与BASELINE_DOWNGRADED事件中的模板名/版本及原因一致，规则的记录要求判P。"
        "TC-048.S2仍因页面缺模板详情链接与匹配依据判F；数据记录通过不代替该页面要求。"
        "证据见`evidence/TC-048-downgrade-detail-*`与`evidence/TC-063-task-detail-fields-task19.json`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 13:49（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded SRS_F015.R06 P")
