"""Record TC-070.S2 from its preserved Stage 3 evidence."""
import csv
from pathlib import Path

p = Path(__file__).resolve().parent
names = (
    "TC-070-situation-live-20261026T080747Z.json",
    "TC-070-situation-busy.json", "TC-070-situation-busy.png",
    "TC-070-situation-task.png", "TC-070-situation-idle.json",
    "TC-070-situation-idle.png",
)
refs = ";".join("acceptance/stage3/evidence/" + name for name in names)
assert all((p / "evidence" / name).exists() for name in names)

for filename, key, updates in (
    ("steps.csv", "stepId", {"TC-070.S2": {
        "status": "P", "observedAt": "2026-10-26",
        "actual": "任务60忙碌标记、能力摘要/任务链接/末次上报可见；筛选后真实点击并跳转任务60；5秒响应间隔4.885/4.996秒，最近更新时间变化；取消后在线空闲且无当前任务",
        "evidence": refs, "issue": ""}}),
    ("rules.csv", "ruleId", {
        "SRS_F023.R03": {"status": "P", "verifiedBy": "TC-070.S2", "evidence": refs, "issue": ""},
        "SRS_F023.R04": {"status": "P", "verifiedBy": "TC-070.S2", "evidence": refs, "issue": ""},
    }),
):
    file = p / filename
    with file.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    for row in rows:
        if row[key] in updates:
            assert row["status"] == "NOT_RUN", (row[key], row["status"])
            row.update(updates[row[key]])
    with file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

report = p / "阶段3-复测进度.md"
body = report.read_text(encoding="utf-8")
body = body.replace("2026-10-26 16:03（Asia/Shanghai）", "2026-10-26 16:08（Asia/Shanghai）", 1)
body = body.replace(
    "原 200 步：P 37、F 50、NT 18、未执行 95；27 项 AC 为 F 5、NT 1、未执行 21；281 条需求规则为 P 60、F 29、NT 8、未执行 184。",
    "原 200 步：P 38、F 50、NT 18、未执行 94；27 项 AC 为 F 5、NT 1、未执行 21；281 条需求规则为 P 62、F 29、NT 8、未执行 182。", 1)
anchor = "- TC-070.S1/S3："
addition = (
    "- TC-070.S2：隔离试运行任务60使航显代理真实进入忙碌，Chrome运行操作员态势显示橙色忙碌标记、能力摘要、当前任务60和最后上报；"
    "只筛选航显后真实鼠标点击浮窗并跳转任务60详情。态势响应连续3次200，间隔4.885和4.996秒，最近更新时间变化；"
    "取消试运行后标记恢复在线空闲且浮窗不再有当前任务，六代理均在线空闲，模板停用、模拟器延迟恢复。"
    "步骤与`SRS_F023.R03/R04`判P；默认图标重叠的`SRS_F023.R02`仍为F。"
    "原始API/浏览器响应/截图见`evidence/TC-070-situation-live-20261026T080747Z.json`、"
    "`evidence/TC-070-situation-{busy,idle}.json`及三张截图。\n"
)
assert anchor in body
body = body.replace(anchor, addition + anchor, 1)
body = body.replace("继续剩余 100 个原步骤、21 项未执行 AC 和 193 条未执行规则",
                    "继续剩余 94 个原步骤、21 项未执行 AC 和 182 条未执行规则")
report.write_text(body, encoding="utf-8")
