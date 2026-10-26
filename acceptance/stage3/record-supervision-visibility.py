"""Record F020.R02 from operator browser and matching task API evidence."""
import csv
import json
from pathlib import Path

stage = Path(__file__).resolve().parent
ev = stage / "evidence"
ui_file = ev / "SRS_F020-R02-supervision-task55.json"
api_file = ev / "SRS_F020-R02-supervision-task55-api.json"
ui = json.loads(ui_file.read_text(encoding="utf-8"))
api = json.loads(api_file.read_text(encoding="utf-8"))
assert ui["runtimeInput"] == api["runtimeInput"] == "V1.5"
assert ui["taskId"] == api["taskId"] == 55 and ui["route"] == "/tasks/55"
assert ui["taskCodeVisible"] == 1
assert "监督判定高风险: RULE_RESOURCE_CRITICAL" in ui["taskHeader"]
assert len(ui["planViews"]) == 2 and ui["tabs"] == ["版本1（自主规划）", "版本2（基线模板）"]
first, second = ui["planViews"]
assert "风险等级\tHIGH" in first["text"]
assert "风险原因\tRULE_RESOURCE_CRITICAL" in first["text"]
assert "判定依据\t可用备用候选设备数量(0)低于配置阈值(1)" in first["text"]
assert second["tab"] == "版本2（基线模板）" and "结构校验\t通过" in second["text"]
assert api["task"]["status"] == "COMPLETED" and api["task"]["downgradeReason"]
assert [(v["versionNo"], v["source"]) for v in api["versions"]] == [
    (1, "AUTONOMOUS"), (2, "BASELINE_TEMPLATE")]
assert api["versions"][0]["riskLevel"] == "HIGH"
assert api["versions"][0]["riskReasonCode"] == "RULE_RESOURCE_CRITICAL"
assert api["task"]["currentPlanVersionId"] == api["versions"][1]["id"]
assert [item["eventType"] for item in api["decisionEvents"]] == [
    "SUPERVISION_JUDGED", "BASELINE_DOWNGRADED"]
assert (ev / ui["screenshot"]).is_file()

refs = ";".join("acceptance/stage3/evidence/" + path.name for path in
                (ui_file, api_file, ev / ui["screenshot"]))
path = stage / "rules.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["ruleId"] == "SRS_F020.R02")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-064.S1", evidence=refs, issue="")
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
body = body.replace("P 83、F 39、NT 9、未执行 150", "P 84、F 39、NT 9、未执行 149", 1)
heading = "## 已执行\n\n"
assert heading in body
note = ("- `SRS_F020.R02`：运行操作员Chrome打开本轮真实任务55，任务详情显示监督判定高风险及降级原因；"
        "自主规划版本1标签显示风险等级HIGH、原因码`RULE_RESOURCE_CRITICAL`和判定依据，"
        "基线模板版本2可切换查看。同期API确认版本2是当前计划，时间线含监督判定与基线降级事件，"
        "因此该可见性规则判P。TC-064.S1的任务列表缺高亮仍为F；此条规则不改变整步状态。"
        "浏览器与API原始证据见`evidence/SRS_F020-R02-*`。\n")
body = body.replace(heading, heading + note, 1)
body = body.replace("2026-10-27 03:43（Asia/Shanghai）", "2026-10-27 03:46（Asia/Shanghai）", 1)
progress.write_text(body, encoding="utf-8")
print("recorded SRS_F020.R02 P; TC-064.S1 unchanged")
