"""Record TC-024.S1 failure with preserved timeout and malformed-feedback evidence."""
import csv
import json
from pathlib import Path

p = Path(__file__).resolve().parent
name = "TC-024-feedback-normalization-20261026T122824Z.json"
ev = json.loads((p / "evidence" / name).read_text(encoding="utf-8"))
timeout = ev["phases"]["timeout"]
invalid = ev["phases"]["invalid"]
assert timeout["dryRun"]["result"] == "FAILED"
assert any("SIMULATED_TIMEOUT" in row for row in timeout["events"])
assert any(row.startswith("EXECUTE_CAPABILITY|TIMED_OUT|") for row in timeout["commands"])
assert not invalid["httpAccepted"] and "400" in invalid["httpError"]
assert invalid["eventRowsBefore"] == invalid["eventRowsAfter"]
assert invalid["dryRunAfter"]["result"] == "RUNNING"
assert ev["restore"]["templateStatus"] == "DISABLED" and ev["restore"]["allSixOnlineIdle"]
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

file, fields, rows = load("steps.csv")
for row in rows:
    if row["stepId"] == "TC-024.S1":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", observedAt="2026-10-26",
            actual="任务61真实TIMEOUT反馈归一为TIMED_OUT，事件含SIMULATED_TIMEOUT并失败处置；任务62在执行中送签名UNRECOGNIZED反馈仅400，未生成异常事件、任务仍RUNNING，未归一失败。已取消并恢复仿真状态",
            evidence=ref, issue="DEF-S3-051")
save(file, fields, rows)

file, fields, rows = load("issues.csv")
assert not any(row["编号"] == "DEF-S3-051" for row in rows)
rows.append({"编号": "DEF-S3-051", "类型": "缺陷", "级别": "中",
    "关联用例步骤": "TC-024.S1", "关联需求规则": "", "状态": "待修复",
    "事实": "真实TIMEOUT反馈可归一并记录原因码；任务62执行期间收到签名但executionResult=UNRECOGNIZED的反馈仅400，任务仍RUNNING且任务事件未新增异常或失败处置，未满足非法/无法归一响应的归一与记录要求",
    "证据": ref,
    "阶段4动作": "明确非法反馈的失败归一与异常事件/任务处置策略，保持原始无效响应审计；重测超时、未知结果、缺字段和恢复路径"})
save(file, fields, rows)

report = p / "阶段3-复测进度.md"
body = report.read_text(encoding="utf-8")
body = body.replace("2026-10-26 20:10（Asia/Shanghai）", "2026-10-26 20:28（Asia/Shanghai）", 1)
body = body.replace(
    "原 200 步：P 39、F 53、NT 19、未执行 89；27 项 AC 为 F 5、NT 1、未执行 21；281 条需求规则为 P 63、F 31、NT 9、未执行 178。",
    "原 200 步：P 39、F 54、NT 19、未执行 88；27 项 AC 为 F 5、NT 1、未执行 21；281 条需求规则为 P 63、F 31、NT 9、未执行 178。", 1)
anchor = "- TC-011.S3及"
addition = (
    "- TC-024.S1：隔离任务61用航显仿真体实际返回TIMEOUT，执行命令变TIMED_OUT，任务事件记录SIMULATED_TIMEOUT并转失败处置；"
    "任务62在执行中收到签名但无法归一的UNRECOGNIZED反馈，只返回400、事件无新增且任务继续RUNNING。"
    "完整步骤因非法响应未归一/未记录判F（`DEF-S3-051`），不否定有效TIMEOUT分支。"
    "任务62已取消，模板停用、模拟器场景及延迟恢复，六代理在线空闲。"
    "原始请求、命令、任务事件和恢复见`evidence/TC-024-feedback-normalization-20261026T122824Z.json`。\n"
)
assert anchor in body
body = body.replace(anchor, addition + anchor, 1)
body = body.replace("继续剩余 89 个原步骤、21 项未执行 AC 和 178 条未执行规则",
                    "继续剩余 88 个原步骤、21 项未执行 AC 和 178 条未执行规则")
report.write_text(body, encoding="utf-8")
