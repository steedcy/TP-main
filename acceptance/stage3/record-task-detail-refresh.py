"""Record F020.R09 from three executing-task detail GET responses."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
ev = stage / "evidence"
ui_file = ev / "SRS_F020-R09-refresh-task67.json"
live_file = ev / "SRS_F020-R09-refresh-live-20261026T214810Z.json"
ui = json.loads(ui_file.read_text(encoding="utf-8"))
live = json.loads(live_file.read_text(encoding="utf-8"))
assert ui["runtimeInput"] == live["runtimeInput"] == "V1.5"
assert ui["taskId"] == live["started"]["taskId"] == 67
assert ui["route"] == "/tasks/67"
assert ui["initialStatusText"] == ui["finalStatusText"] == "执行中"
assert live["taskBeforeBrowser"] == live["taskAfterBrowser"] == "EXECUTING"
assert live["agentAtBusy"]["currentTaskId"] == 67
responses = ui["taskGetResponses"]
assert len(responses) >= 3 and all(row["httpStatus"] == 200 and
    row["taskStatus"] == "EXECUTING" for row in responses)
intervals = [(datetime.fromisoformat(current["at"].replace("Z", "+00:00")) -
              datetime.fromisoformat(previous["at"].replace("Z", "+00:00"))).total_seconds()
             for previous, current in zip(responses, responses[1:])]
assert len(intervals) >= 2 and all(0 < interval <= 15 for interval in intervals), intervals
assert live["restore"]["cancel"]["result"] == "CANCELLED"
assert live["restore"]["templateStatus"] == "DISABLED"
assert live["restore"]["delayMs"] == 1000 and live["restore"]["allSixOnlineIdle"]
assert (ev / ui["screenshot"]).is_file()

refs = ";".join("acceptance/stage3/evidence/" + path.name for path in
                (ui_file, live_file, ev / ui["screenshot"]))
path = stage / "rules.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["ruleId"] == "SRS_F020.R09")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-063.S2", evidence=refs, issue="")
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
body = body.replace("P 84、F 39、NT 9、未执行 149", "P 85、F 39、NT 9、未执行 148", 1)
heading = "## 已执行\n\n"
assert heading in body
note = ("- `SRS_F020.R09`：真实试运行任务67持续执行期间，Chrome运行操作员任务详情连续三次GET读取状态均为EXECUTING，"
        "相邻响应间隔分别约10.000与9.996秒，符合≤15秒刷新周期。任务完成此分支后由配置管理员取消试运行，"
        "模板停用、仿真延时恢复1000ms、六代理在线空闲。规则判P；TC-063.S2仍有详情字段、重规划"
        "及完整页面分支未覆，整步不提前判P。浏览器网络采样、截图与API清理证据见`evidence/SRS_F020-R09-*`。\n")
body = body.replace(heading, heading + note, 1)
body = body.replace("2026-10-27 04:48（Asia/Shanghai）", "2026-10-27 05:49（Asia/Shanghai）", 1)
progress.write_text(body, encoding="utf-8")
print("recorded SRS_F020.R09 P; intervals", intervals)
