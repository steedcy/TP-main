"""Record TC-064.S1 and F020.R04 from this run's browser evidence."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
ev = stage / "evidence"
ui_file = ev / "TC-064-pending-manual-ui.json"
normal_file = ev / "TC-064-normal-executing-66.json"
live_file = ev / "TC-064-normal-executing-live-20261026T185057Z.json"
ui = json.loads(ui_file.read_text(encoding="utf-8"))
normal = json.loads(normal_file.read_text(encoding="utf-8"))
live = json.loads(live_file.read_text(encoding="utf-8"))

assert ui["runtimeInput"] == normal["runtimeInput"] == live["runtimeInput"] == "V1.5"
assert ui["overview"]["pendingCardText"] == "待人工任务数\n15"
pending, completed = ui["pendingList"], ui["completedList"]
assert "待人工处理" in pending["rowText"] and "已完成" in completed["rowText"]
for field in ("rowClass", "rowBackground", "tagClass", "tagColor", "tagBackground"):
    assert pending[field] == completed[field], field
assert ui["pendingDetail"]["manualCardCount"] == 1
assert all(count == 1 for count in ui["pendingDetail"]["actions"].values())
assert all(count == 0 for count in ui["completedDetail"]["actions"].values())
assert normal["taskId"] == 66 and normal["statusText"] == "执行中"
assert normal["manualActionCardCount"] == normal["confirmationButtonCount"] == 0
assert [normal["actions"][name] for name in ("转基线执行", "重试规划", "置为失败")] == [0, 0, 0]
assert normal["actions"]["终止任务"] == 1
assert live["taskBeforeBrowser"] == live["taskAfterBrowser"] == "EXECUTING"
assert live["browserExitCode"] == 0 and live["agentAtBusy"]["currentTaskId"] == 66
assert live["restore"]["templateStatus"] == "DISABLED"
assert live["restore"]["allSixOnlineIdle"] and live["restore"]["delayMs"] == 1000
screens = [ev / name for name in (
    "TC-064-pending-overview.png", "TC-064-pending-list.png",
    "TC-064-pending-detail.png", "TC-064-normal-executing-66.png")]
assert all(path.is_file() for path in screens)

refs = ";".join("acceptance/stage3/evidence/" + p.name for p in
                [ui_file, normal_file, live_file, *screens])
today = datetime.now().astimezone().date().isoformat()

def update(path, key, target, changes):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    row = next(r for r in rows if r[key] == target)
    assert row["status"] == "NOT_RUN", (target, row["status"])
    row.update(changes)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

update(stage / "steps.csv", "stepId", "TC-064.S1", dict(
    status="F", observedAt=today,
    actual="运行总览对待人工15项有橙色强调；任务列表中待人工任务20与已完成任务59的行类名、透明背景、标签类名和灰色样式完全相同，截图也无待人工高亮。待人工详情四项处置可见，已完成详情均不可见；真实执行中任务66仅有业务终止，无人工确认。",
    evidence=refs, issue="DEF-S3-060"))
update(stage / "rules.csv", "ruleId", "SRS_F020.R04", dict(
    status="F", verifiedBy="TC-064.S1", evidence=refs, issue="DEF-S3-060"))

with (stage / "issues.csv").open(encoding="utf-8-sig", newline="") as stream:
    assert "DEF-S3-060" not in {r["编号"] for r in csv.DictReader(stream)}
with (stage / "issues.csv").open("a", encoding="utf-8", newline="") as stream:
    csv.writer(stream, lineterminator="\n").writerow([
        "DEF-S3-060", "缺陷", "中", "TC-064.S1", "SRS_F020.R04", "待修复",
        "Chrome中运行总览对待人工任务数15有橙色强调，但任务列表的待人工任务20与已完成任务59同为白色行和灰色标签，无待人工高亮；详情处置按钮按状态显示正确。",
        refs,
        "为任务列表待人工状态行或标签设置清晰且可访问的强调样式；复测待人工、执行中和已完成状态以及总览。"])

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
body = body.replace("P 41、F 57、NT 19、未执行 83", "P 41、F 58、NT 19、未执行 82", 1)
body = body.replace("P 82、F 38、NT 9、未执行 152", "P 82、F 39、NT 9、未执行 151", 1)
heading = "## 已执行\n\n"
assert heading in body
note = ("- TC-064.S1及`SRS_F020.R04`：Chrome实际查看待人工任务20、已完成任务19/59、真实执行中任务66。"
        "运行总览待人工15项有橙色强调，但任务列表中待人工任务20和已完成任务59行及标签样式相同、无高亮，"
        "S1与R04判F（`DEF-S3-060`）。待人工详情四项处置可见，已完成详情均无，执行中仅有业务终止且无人工确认；"
        "其他功能不据此扩展判定。首次总览指标未加载的浏览器采样与截图以`*-attempt1`保留，"
        "最终浏览器、运行中任务、清理证据见`evidence/TC-064-*`。模板停用、六代理在线空闲、延时恢复1000ms。\n")
body = body.replace(heading, heading + note, 1)
progress.write_text(body, encoding="utf-8")
print("recorded TC-064.S1 F, SRS_F020.R04 F, DEF-S3-060")
