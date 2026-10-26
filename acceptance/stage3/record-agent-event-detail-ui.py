"""Record the TC-023.S2 agent detail and event timeline defect."""
import csv
import json
from pathlib import Path

p = Path(__file__).resolve().parent
names = ("TC-023-agent-event-detail-ui.json", "TC-023-agent-list.png",
         "TC-023-agent-detail-route.png", "TC-011-busy-agent-ui.json",
         "TC-011-busy-agent-list.png")
refs = ";".join("acceptance/stage3/evidence/" + name for name in names)
assert all((p / "evidence" / name).exists() for name in names)
ev = json.loads((p / "evidence" / names[0]).read_text(encoding="utf-8"))
assert ev["agentDetailLinks"] == 0
assert ev["eventTimelineEntries"] == 0
assert ev["detailButtons"] == 0

file = p / "steps.csv"
with file.open(encoding="utf-8-sig", newline="") as handle:
    reader = csv.DictReader(handle)
    fields = reader.fieldnames
    rows = list(reader)
for row in rows:
    if row["stepId"] == "TC-023.S2":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", observedAt="2026-10-26",
            actual="运行操作员代理列表只有状态/任务/停用，代理行无详情或事件入口，页面无消息时间线；直达代理子路由为空白。成功/失败/超时归一化及指令关联仍须单独复测",
            evidence=refs, issue="DEF-S3-044")
with file.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

file = p / "issues.csv"
with file.open(encoding="utf-8-sig", newline="") as handle:
    reader = csv.DictReader(handle)
    fields = reader.fieldnames
    rows = list(reader)
for row in rows:
    if row["编号"] == "DEF-S3-044":
        row["关联用例步骤"] += ";TC-023.S2"
        row["事实"] += "；运行操作员代理列表也没有消息事件时间线和详情入口，直达代理子路由为空白"
        row["证据"] += ";" + ";".join("acceptance/stage3/evidence/" + name for name in names[:3])
        row["阶段4动作"] += "；提供按代理查看消息类型、时间、指令号、请求响应摘要及结果的事件详情，并独立验证成功/失败/超时反馈映射"
with file.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

report = p / "阶段3-复测进度.md"
body = report.read_text(encoding="utf-8")
body = body.replace("2026-10-26 19:55（Asia/Shanghai）", "2026-10-26 19:58（Asia/Shanghai）", 1)
body = body.replace(
    "原 200 步：P 39、F 50、NT 19、未执行 92；27 项 AC 为 F 5、NT 1、未执行 21；281 条需求规则为 P 62、F 29、NT 9、未执行 181。",
    "原 200 步：P 39、F 51、NT 19、未执行 91；27 项 AC 为 F 5、NT 1、未执行 21；281 条需求规则为 P 62、F 29、NT 9、未执行 181。", 1)
anchor = "- TC-071.S1："
addition = (
    "- TC-023.S2：运行操作员Chrome代理列表显示六标准代理状态，但航显代理行没有详情链接/事件按钮，页面没有消息时间线；"
    "直达代理子路由为空白。与本轮TC-011忙碌代理证据互证，步骤因缺代理详情与事件展示判F并扩充`DEF-S3-044`。"
    "成功/失败/超时反馈归一、唯一指令与落库事件需按`SRS_F007`其他规则另测，未以此步推断通过。"
    "原始DOM与两张截图在`evidence/TC-023-agent-event-detail-ui.json`及`evidence/TC-023-agent-*.png`。\n"
)
assert anchor in body
body = body.replace(anchor, addition + anchor, 1)
body = body.replace("继续剩余 92 个原步骤、21 项未执行 AC 和 181 条未执行规则",
                    "继续剩余 91 个原步骤、21 项未执行 AC 和 181 条未执行规则")
report.write_text(body, encoding="utf-8")
