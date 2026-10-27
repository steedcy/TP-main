"""Record the live resolved/pending exception follow-up without clearing TC-058.S2."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
api_name = "TC-058-exception-list-api-20261027T043044Z.json"
ui_name = "TC-058-exception-list-ui-20261027T043315Z.json"
api = json.loads((stage / "evidence" / api_name).read_text(encoding="utf-8"))
ui = json.loads((stage / "evidence" / ui_name).read_text(encoding="utf-8"))
assert len(api["all"]) == 5
assert sum(x["exceptionStatus"] == "PENDING" for x in api["all"]) == 2
assert sum(x["exceptionStatus"] == "RESOLVED" and x["resolvedBy"] == "SYSTEM" for x in api["all"]) == 3
assert api["pendingCounterMatches"] and api["allFiltersMatch"]
assert ui["overview"]["pendingMetric"] == "未处置异常数\n2"
assert ui["overview"]["pendingLink"].endswith("/task-exceptions?exceptionStatus=PENDING")
assert len(ui["filters"]["pending"]) == 2 and len(ui["filters"]["resolved"]) == 3
assert len(ui["defaultRows"]) == 5 and ui["historyControl"] == 0
assert not ui["reasonCodeVisible"] and "步骤" in ui["headers"]
assert ui["navigation"]["href"] == "/tasks/83"
refs = ";".join("acceptance/stage3/evidence/" + name for name in (
    api_name, ui_name, ui["overviewScreenshot"], ui["defaultScreenshot"], ui["resolvedScreenshot"]))


def update_csv(name, key, value, update):
    path = stage / name
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    row = next(r for r in rows if r[key] == value)
    update(row)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def update_step(row):
    assert row["status"] == "F" and row["issue"] == "DEF-S3-064"
    row["actual"] += (" 续测任务83三条系统已处置与任务58/79两条待处置并存；Chrome已处置筛选3条、待处置筛选2条，"
                      "总览未处置异常数显示2且点击跳转待处置筛选。已处置记录仍混在默认列表，页面无历史异常列表入口；"
                      "原因码与步骤链接缺失仍在，整步维持F。")
    row["evidence"] += ";" + refs


def update_rule(row):
    assert row["status"] == "NOT_RUN"
    row.update(status="F", verifiedBy="TC-058.S2", evidence=refs)


def update_issue(row):
    assert row["状态"] == "待修复"
    row["事实"] += (" 续测任务83三条RESOLVED记录由SYSTEM置为已处置，却仍与两条PENDING记录混在异常列表默认页；"
                    "可按已处置筛选但无独立历史异常列表/归档入口。总览未处置数2和跳转筛选正常。")
    row["证据"] += ";" + refs
    row["阶段4动作"] = "增加原因码显示、关联步骤入口与已处置历史归档列表；回归五类异常、各状态及总览计数。"


update_csv("steps.csv", "stepId", "TC-058.S2", update_step)
update_csv("rules.csv", "ruleId", "SRS_F018.R10", update_rule)
update_csv("issues.csv", "编号", "DEF-S3-064", update_issue)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
old = "281 条需求规则为 P 101、F 46、NT 11、未执行 123"
assert old in body
body = body.replace(old, "281 条需求规则为 P 101、F 47、NT 11、未执行 122", 1)
note = ("- `SRS_F018.R10`与TC-058.S2续测：V1.5任务83系统自动置RESOLVED三条、任务58/79 PENDING两条。"
        "Chrome运行总览未处置数为2，点击进入待处置筛选；异常页已处置筛选得3条，但这些记录仍与待处置记录混在默认列表，"
        "没有历史异常列表/归档入口。该规则按独立历史列表要求判F，归入`DEF-S3-064`；TC-058.S2原有原因码和步骤链接缺陷仍在，维持F。"
        "早期页面过快读取曾显示`--`，已等待指标装载后重新取证；原始证据保留。见`evidence/TC-058-exception-list-*`与`evidence/TC-058-overview-pending-*`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 12:28（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded SRS_F018.R10 F; TC-058.S2 remains F")
