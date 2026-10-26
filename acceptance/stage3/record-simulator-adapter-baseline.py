"""Record the Stage 3 simulated adapter baseline independently of interface defects."""
import csv
import json
from pathlib import Path

p = Path(__file__).resolve().parent
name = "TC-023-simulator-adapter-baseline-20261026T123924Z.json"
ev = json.loads((p / "evidence" / name).read_text(encoding="utf-8"))
assert ev["device"]["isSimulator"] is True
assert ev["simulatorHealth"]["protocolVersion"] == "1.0"
assert ev["simulatorHealth"]["deviceCode"] == ev["device"]["deviceCode"]
assert any(row["commandType"] == "EXECUTE_CAPABILITY" and row["status"] == "SUCCEEDED"
           for row in ev["taskCommands"])
assert "EXECUTION_FEEDBACK_RECEIVED" in ev["taskEventTypes"]
ref = "acceptance/stage3/evidence/" + name
file = p / "rules.csv"
with file.open(encoding="utf-8-sig", newline="") as handle:
    reader = csv.DictReader(handle)
    fields = reader.fieldnames
    rows = list(reader)
for row in rows:
    if row["ruleId"] == "SRS_F007.R08":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", verifiedBy="TC-023.S1", evidence=ref, issue="")
with file.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

report = p / "阶段3-复测进度.md"
body = report.read_text(encoding="utf-8")
body = body.replace("2026-10-26 20:37（Asia/Shanghai）", "2026-10-26 20:39（Asia/Shanghai）", 1)
body = body.replace(
    "原 200 步：P 39、F 55、NT 19、未执行 87；27 项 AC 为 F 5、NT 1、未执行 21；281 条需求规则为 P 63、F 34、NT 9、未执行 175。",
    "原 200 步：P 39、F 55、NT 19、未执行 87；27 项 AC 为 F 5、NT 1、未执行 21；281 条需求规则为 P 64、F 34、NT 9、未执行 174。", 1)
anchor = "- `SRS_F007.R07`："
addition = (
    "- `SRS_F007.R08`：现用航显档案标记为仿真体，带令牌健康握手返回协议1.0与SMART_DISPLAY身份；"
    "本轮隔离任务56对其代理的TASK_ACCEPT为ACCEPTED、EXECUTE_CAPABILITY为SUCCEEDED，"
    "任务时间线有执行反馈，因此首期模拟适配器基线判P。"
    "此项不覆盖统一消息接口校验及安全字段缺陷，原始快照在"
    "`evidence/TC-023-simulator-adapter-baseline-20261026T123924Z.json`。\n"
)
assert anchor in body
body = body.replace(anchor, addition + anchor, 1)
body = body.replace("继续剩余 87 个原步骤、21 项未执行 AC 和 175 条未执行规则",
                    "继续剩余 87 个原步骤、21 项未执行 AC 和 174 条未执行规则")
report.write_text(body, encoding="utf-8")
