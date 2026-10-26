"""Record the missing success reason code under SRS_F007.R06."""
import csv
import json
from pathlib import Path

p = Path(__file__).resolve().parent
name = "TC-023-feedback-reason-codes-20261026T123442Z.json"
ev = json.loads((p / "evidence" / name).read_text(encoding="utf-8"))
rows_by_result = {row["response"]["executionResult"]: row for row in ev["commandFeedback"]}
assert set(rows_by_result) == {"SUCCESS", "FAILED", "TIMEOUT"}
assert rows_by_result["FAILED"]["response"]["reasonCode"] == "SIMULATED_DEVICE_ERROR"
assert rows_by_result["TIMEOUT"]["response"]["reasonCode"] == "SIMULATED_TIMEOUT"
assert rows_by_result["SUCCESS"]["response"].get("reasonCode") is None
assert ev["feedbackEvents"][-1]["reasonCode"] is None
ref = "acceptance/stage3/evidence/" + name

def load(filename):
    file = p / filename
    with file.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return file, reader.fieldnames, list(reader)

def save(file, fields, rows):
    with file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

file, fields, rows = load("rules.csv")
for row in rows:
    if row["ruleId"] == "SRS_F007.R06":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", verifiedBy="TC-023.S2", evidence=ref, issue="DEF-S3-053")
save(file, fields, rows)

file, fields, rows = load("steps.csv")
for row in rows:
    if row["stepId"] == "TC-023.S2":
        assert row["status"] == "F"
        row["actual"] = row["actual"].replace("成功/失败/超时归一化及指令关联仍须单独复测", "指令关联仍须单独复测")
        row["actual"] += "；三类回执映射均在隔离任务中观察，成功回执/事件原因码为空"
        row["evidence"] += ";" + ref
        row["issue"] += ";DEF-S3-053"
save(file, fields, rows)

file, fields, rows = load("issues.csv")
assert not any(row["编号"] == "DEF-S3-053" for row in rows)
rows.append({"编号": "DEF-S3-053", "类型": "缺陷", "级别": "低",
    "关联用例步骤": "TC-023.S2", "关联需求规则": "SRS_F007.R06", "状态": "待修复",
    "事实": "隔离任务30/31/59的FAILED、TIMEOUT、SUCCESS均映射为相应命令状态；前两类反馈和事件有原因码，SUCCESS反馈及EXECUTION_FEEDBACK_RECEIVED事件的reasonCode为null，未满足规则未列例外的携带原因码要求",
    "证据": ref,
    "阶段4动作": "按需求原文为成功反馈及追溯事件提供明确成功原因码；若需求裁决允许成功无原因码，则先固化例外并重测三类映射"})
save(file, fields, rows)

report = p / "阶段3-复测进度.md"
body = report.read_text(encoding="utf-8")
body = body.replace("2026-10-26 20:32（Asia/Shanghai）", "2026-10-26 20:35（Asia/Shanghai）", 1)
body = body.replace(
    "原 200 步：P 39、F 55、NT 19、未执行 87；27 项 AC 为 F 5、NT 1、未执行 21；281 条需求规则为 P 63、F 32、NT 9、未执行 177。",
    "原 200 步：P 39、F 55、NT 19、未执行 87；27 项 AC 为 F 5、NT 1、未执行 21；281 条需求规则为 P 63、F 33、NT 9、未执行 176。", 1)
anchor = "- TC-024.S2与"
addition = (
    "- `SRS_F007.R06`：从本轮隔离任务30/31/59独立读取失败、超时、成功三类真实执行回执及对应事件，"
    "命令状态均映射正确，失败/超时有原因码；成功回执和事件原因码均为null。"
    "需求原文无成功例外，故规则判F（`DEF-S3-053`），并补充TC-023.S2原F步骤证据；"
    "若阶段4规格裁决允许成功无原因码，需明确例外后复测。"
    "原始对照在`evidence/TC-023-feedback-reason-codes-20261026T123442Z.json`。\n"
)
assert anchor in body
body = body.replace(anchor, addition + anchor, 1)
body = body.replace("继续剩余 87 个原步骤、21 项未执行 AC 和 177 条未执行规则",
                    "继续剩余 87 个原步骤、21 项未执行 AC 和 176 条未执行规则")
report.write_text(body, encoding="utf-8")
