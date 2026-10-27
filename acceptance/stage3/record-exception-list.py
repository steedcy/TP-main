"""Record the observed TC-058.S2 defect without treating empty filters as covered."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
api_file = stage / "evidence/TC-058-exception-list-api-20261027T035719Z.json"
ui_file = stage / "evidence/TC-058-exception-list-ui-20261027T035739Z.json"
api = json.loads(api_file.read_text(encoding="utf-8"))
ui = json.loads(ui_file.read_text(encoding="utf-8"))
assert api["allFiltersMatch"] and api["pendingCounterMatches"]
assert len(api["all"]) == 1 and api["all"][0]["exceptionType"] == "CAPABILITY_GAP"
assert api["all"][0]["reasonCode"] and api["all"][0]["exceptionStatus"] == "PENDING"
assert "原因码" not in ui["headers"] and "步骤" in ui["headers"]
assert ui["navigation"]["href"] == "/tasks/58" and ui["navigation"]["landed"].endswith("/tasks/58")
assert set(ui["filters"]) == {"设备离线", "能力缺口", "执行超时", "步骤失败", "重新规划失败"}
refs = ";".join("acceptance/stage3/evidence/" + p.name for p in (api_file, ui_file))
refs += ";acceptance/stage3/evidence/TC-058-exception-list-default.png"

steps_file = stage / "steps.csv"
with steps_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["stepId"] == "TC-058.S2")
assert row["status"] == "NOT_RUN"
row.update(status="F", observedAt=datetime.now().strftime("%Y-%m-%d"),
           actual="运行操作员异常列表默认显示任务58能力缺口待处置记录，类型/状态筛选API匹配且待处置计数为1；任务链接到详情正确。API有原因码，但页面表头及行未显示原因码，步骤列也不是关联步骤链接。其他四类与已处置筛选当前均为空，本轮不声称这些分支或历史归档通过。",
           evidence=refs, issue="DEF-S3-064")
with steps_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

issues_file = stage / "issues.csv"
with issues_file.open(encoding="utf-8-sig", newline="") as stream:
    assert "DEF-S3-064" not in {r["编号"] for r in csv.DictReader(stream)}
with issues_file.open("a", encoding="utf-8", newline="") as stream:
    csv.writer(stream, lineterminator="\n").writerow([
        "DEF-S3-064", "缺陷", "中", "TC-058.S2", "SRS_F018.R09;SRS_F018.R10", "待修复",
        "运行操作员异常列表中任务58的CAPABILITY_GAP记录，API返回非空reasonCode；Chrome异常列表表头没有原因码列、行不显示该值。步骤1仅是纯文本，无法打开关联步骤，任务链接本身正常。",
        refs,
        "增加原因码显示与关联步骤入口；补齐五类异常、已处置归档和总览计数的真实数据后回归TC-058.S2及邻接流程。"])

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
assert "原 200 步：P 42、F 61、NT 19、未执行 78" in body
body = body.replace("原 200 步：P 42、F 61、NT 19、未执行 78",
                    "原 200 步：P 42、F 62、NT 19、未执行 77", 1)
note = ("- TC-058.S2异常列表：本轮Chrome和API显示任务58能力缺口待处置，五种类型和四种状态筛选请求可发出，"
        "非空结果匹配，待处置计数为1，任务链接可达。但API已有的原因码页面不显示，步骤列无关联入口，"
        "记`DEF-S3-064`并判F。其他四类及已处置样本为空，历史归档及`SRS_F018.R10`保持未执行。"
        "见`evidence/TC-058-exception-list-*`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 11:51（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded TC-058.S2 F; DEF-S3-064")
