"""Record TC-071.S2 from the preserved browser fault-injection evidence."""
import csv
import json
from pathlib import Path

p = Path(__file__).resolve().parent
names = ("TC-071-situation-failures.json", "TC-071-map-missing.png",
         "TC-071-refresh-failed.png")
refs = ";".join("acceptance/stage3/evidence/" + name for name in names)
assert all((p / "evidence" / name).exists() for name in names)
ev = json.loads((p / "evidence" / names[0]).read_text(encoding="utf-8"))
assert ev["mapImageNaturalWidth"] == 0
assert "底图加载失败" in ev["mapErrorText"]
assert "保留上次成功获取的数据" in ev["refreshWarning"]
assert ev["tableTextBefore"] == ev["tableTextAfter"]
assert ev["generatedAtBefore"] == ev["generatedAtAfter"]
assert [r["status"] for r in ev["responses"]] == [200, 503]

file = p / "steps.csv"
with file.open(encoding="utf-8-sig", newline="") as handle:
    reader = csv.DictReader(handle)
    fields = reader.fieldnames
    rows = list(reader)
for row in rows:
    if row["stepId"] == "TC-071.S2":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", observedAt="2026-10-26",
            actual="Chrome路由故障注入使F2.jpg加载失败，显示灰色占位和错误提示，六设备仍在列表；首次态势200后注入503，页面提示失败时间并保留原六设备和最近成功更新时间",
            evidence=refs, issue="")
with file.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

report = p / "阶段3-复测进度.md"
body = report.read_text(encoding="utf-8")
body = body.replace("2026-10-26 16:08（Asia/Shanghai）", "2026-10-26 19:52（Asia/Shanghai）", 1)
body = body.replace(
    "原 200 步：P 38、F 50、NT 18、未执行 94；27 项 AC 为 F 5、NT 1、未执行 21；281 条需求规则为 P 62、F 29、NT 8、未执行 182。",
    "原 200 步：P 39、F 50、NT 18、未执行 93；27 项 AC 为 F 5、NT 1、未执行 21；281 条需求规则为 P 62、F 29、NT 8、未执行 182。", 1)
anchor = "- TC-070.S2："
addition = (
    "- TC-071.S2：Chrome路由级故障注入让底图F2.jpg加载失败，真实图片宽度0；灰色占位与不可用提示出现，六台设备仍在下方列表。"
    "态势初次200后将下一次刷新注入503，警告含失败时间，六标记/列表内容和最近成功更新时间均保持原值，判P。"
    "这验证页面对故障响应的处理，没有声称真实静态资源或后端服务故障。原始响应、DOM和全页截图见"
    "`evidence/TC-071-situation-failures.json`、`evidence/TC-071-{map-missing,refresh-failed}.png`。"
    "此前本地8080/5173/8091～8096进程停止，未将连接失败计为用例结果；已按隔离schema重启V1.5 JAR并恢复六代理在线空闲，"
    "Flyway日志确认tip_stage2_v14版本16，恢复证据为`evidence/stage3-services-recovered-20261026T115123Z.json`。\n"
)
assert anchor in body
body = body.replace(anchor, addition + anchor, 1)
body = body.replace("继续剩余 94 个原步骤、21 项未执行 AC 和 182 条未执行规则",
                    "继续剩余 93 个原步骤、21 项未执行 AC 和 182 条未执行规则")
report.write_text(body, encoding="utf-8")
