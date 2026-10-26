"""Record Stage 3 unified-message and command-ID defects from raw evidence."""
import csv
import json
from pathlib import Path

p = Path(__file__).resolve().parent
command_name = "TC-023-command-identity-20261026T120620Z.json"
message_name = "TC-023-internal-messages-20261026T120718Z.json"
commands = json.loads((p / "evidence" / command_name).read_text(encoding="utf-8"))
messages = json.loads((p / "evidence" / message_name).read_text(encoding="utf-8"))
assert len(commands["multiTypeCommandIdsInTasks38To60"]) == 49
assert len({r["commandType"] for r in commands["commands"] if r["taskId"] == 60}) == 3
assert len({r["commandId"] for r in commands["commands"] if r["taskId"] == 60}) == 1
assert len(messages["uniqueCommandIdProbes"]) == 6
assert all(not r["accepted"] and "400" in r["error"] for r in messages["uniqueCommandIdProbes"])
assert all(r["accepted"] for r in messages["literalIdControls"])
command_ref = "acceptance/stage3/evidence/" + command_name
message_ref = "acceptance/stage3/evidence/" + message_name

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
    if row["stepId"] == "TC-023.S1":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", observedAt="2026-10-26",
            actual="六种统一消息使用真实唯一指令号均HTTP400，被错误的消息类型正则拦截；将类型字面量作为指令号时能力/状态查询成功。拒绝/反馈/取消语义因入口失败未判通过",
            evidence=message_ref, issue="DEF-S3-050")
save(file, fields, rows)

file, fields, rows = load("rules.csv")
for row in rows:
    if row["ruleId"] == "SRS_F007.R01":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", verifiedBy="TC-023.S1", evidence=message_ref, issue="DEF-S3-050")
    if row["ruleId"] == "SRS_F007.R02":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", verifiedBy="TC-023.S2", evidence=command_ref + ";" + message_ref,
                   issue="DEF-S3-049")
save(file, fields, rows)

file, fields, rows = load("issues.csv")
assert not any(r["编号"] in ("DEF-S3-049", "DEF-S3-050") for r in rows)
rows.extend([
    {"编号": "DEF-S3-049", "类型": "缺陷", "级别": "中", "关联用例步骤": "TC-023.S2",
     "关联需求规则": "SRS_F007.R02", "状态": "待修复",
     "事实": "真实任务59的TASK_ACCEPT与EXECUTE_CAPABILITY复用同一commandId；任务60的TASK_CANCEL也复用该编号。隔离库任务38至60有49个编号跨消息类型重复，唯一索引还包含command_type，未实现逐条下发消息唯一编号",
     "证据": command_ref,
     "阶段4动作": "为每条不同下发消息生成独立指令号，并保留重试时同一逻辑消息的幂等编号；调整唯一约束及回执关联，复测接受/执行/取消和重试"},
    {"编号": "DEF-S3-050", "类型": "缺陷", "级别": "高", "关联用例步骤": "TC-023.S1",
     "关联需求规则": "SRS_F007.R01", "状态": "待修复",
     "事实": "系统管理员对六类统一消息使用各自真实唯一指令号均HTTP400，提示指令号须匹配六个消息类型字面量；把消息类型字面量填入commandId后能力/状态查询均成功，验证正则校验应用到错误字段",
     "证据": message_ref,
     "阶段4动作": "将六类枚举校验施加到messageType，对commandId校验非空及唯一编号格式；复测六消息路径、拒绝原因、取消语义和反馈归一"},
])
save(file, fields, rows)

report = p / "阶段3-复测进度.md"
body = report.read_text(encoding="utf-8")
body = body.replace("2026-10-26 19:58（Asia/Shanghai）", "2026-10-26 20:08（Asia/Shanghai）", 1)
body = body.replace(
    "原 200 步：P 39、F 51、NT 19、未执行 91；27 项 AC 为 F 5、NT 1、未执行 21；281 条需求规则为 P 62、F 29、NT 9、未执行 181。",
    "原 200 步：P 39、F 52、NT 19、未执行 90；27 项 AC 为 F 5、NT 1、未执行 21；281 条需求规则为 P 62、F 31、NT 9、未执行 179。", 1)
anchor = "- TC-023.S2："
addition = (
    "- TC-023.S1与`SRS_F007.R01/R02`：真实隔离任务59的接受/执行、任务60的接受/执行/取消分别复用同一指令号；"
    "任务38～60累计49个指令号跨消息类型重复，唯一索引以消息类型作联合键，`R02`判F（`DEF-S3-049`）。"
    "系统管理员对六种内部统一消息各用不同真实指令号均HTTP400，错误提示要求指令号匹配六个消息类型字面量；"
    "将类型字面量作为指令号时，能力/状态查询反而成功，故步骤和`R01`判F（`DEF-S3-050`）。"
    "这是V1.5实时接口与库内记录；没有把失败请求当成拒绝/反馈/取消语义通过。"
    "原始证据见`evidence/TC-023-command-identity-20261026T120620Z.json`和"
    "`evidence/TC-023-internal-messages-20261026T120718Z.json`。\n"
)
assert anchor in body
body = body.replace(anchor, addition + anchor, 1)
body = body.replace("继续剩余 91 个原步骤、21 项未执行 AC 和 181 条未执行规则",
                    "继续剩余 90 个原步骤、21 项未执行 AC 和 179 条未执行规则")
report.write_text(body, encoding="utf-8")
