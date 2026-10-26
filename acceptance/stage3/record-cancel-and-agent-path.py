"""Record business cancel semantics and the blocked agent query path."""
import csv
import json
from pathlib import Path

p = Path(__file__).resolve().parent
cancel_name = "TC-023-cancel-semantics-20261026T121015Z.json"
message_name = "TC-023-internal-messages-20261026T120718Z.json"
creation_name = "TC-012-agent-audit-20261026T065255Z.json"
cancel = json.loads((p / "evidence" / cancel_name).read_text(encoding="utf-8"))
messages = json.loads((p / "evidence" / message_name).read_text(encoding="utf-8"))
assert cancel["cancelCommand"]["payload"]["commandType"] == "TASK_CANCEL"
assert cancel["cancelCommand"]["payload"]["inputParams"] == {}
assert cancel["cancelCommand"]["status"] == "TIMED_OUT"
assert "TASK_CANCEL_REQUESTED" in cancel["taskEventTypes"]
assert all(not row["accepted"] for row in messages["uniqueCommandIdProbes"][:2])
refs = ";".join("acceptance/stage3/evidence/" + name for name in
                (message_name, creation_name, cancel_name))
cancel_ref = "acceptance/stage3/evidence/" + cancel_name

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
    if row["stepId"] == "TC-011.S3":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", observedAt="2026-10-26",
            actual="代理创建操作与设备事件存在、真实任务走代理；但能力/状态查询带唯一指令号均被内部消息入口错误正则以400拒绝，无法完成统一查询路径。未据此判私有协议/安全字段分支通过",
            evidence=refs, issue="DEF-S3-050")
save(file, fields, rows)

file, fields, rows = load("rules.csv")
for row in rows:
    if row["ruleId"] == "SRS_F007.R04":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", verifiedBy="TC-023.S1", evidence=cancel_ref, issue="")
save(file, fields, rows)

file, fields, rows = load("issues.csv")
for row in rows:
    if row["编号"] == "DEF-S3-050":
        row["关联用例步骤"] += ";TC-011.S3"
        row["事实"] += "；TC-011.S3要求的能力/状态统一查询因此也不能使用真实唯一指令号完成"
        row["证据"] += ";acceptance/stage3/evidence/" + creation_name
save(file, fields, rows)

report = p / "阶段3-复测进度.md"
body = report.read_text(encoding="utf-8")
body = body.replace("2026-10-26 20:08（Asia/Shanghai）", "2026-10-26 20:10（Asia/Shanghai）", 1)
body = body.replace(
    "原 200 步：P 39、F 52、NT 19、未执行 90；27 项 AC 为 F 5、NT 1、未执行 21；281 条需求规则为 P 62、F 31、NT 9、未执行 179。",
    "原 200 步：P 39、F 53、NT 19、未执行 89；27 项 AC 为 F 5、NT 1、未执行 21；281 条需求规则为 P 63、F 31、NT 9、未执行 178。", 1)
anchor = "- TC-023.S1与"
addition = (
    "- TC-011.S3及`SRS_F007.R04`：本轮临时代理创建确有操作记录及`AGENT_CREATED`设备事件，真实任务指令走代理；"
    "但唯一编号的能力/状态查询均在内部统一消息入口被400拒绝，步骤沿`DEF-S3-050`判F。"
    "本轮任务60的实际取消消息类型是`TASK_CANCEL`，含任务号、空业务参数且无急停/运动控制字段，时间线记录`TASK_CANCEL_REQUESTED`，"
    "因此仅业务取消语义规则`R04`判P；该取消最终确认超时，不把它记为取消成功。"
    "证据见`evidence/TC-012-agent-audit-20261026T065255Z.json`、"
    "`evidence/TC-023-internal-messages-20261026T120718Z.json`、"
    "`evidence/TC-023-cancel-semantics-20261026T121015Z.json`。\n"
)
assert anchor in body
body = body.replace(anchor, addition + anchor, 1)
body = body.replace("继续剩余 90 个原步骤、21 项未执行 AC 和 179 条未执行规则",
                    "继续剩余 89 个原步骤、21 项未执行 AC 和 178 条未执行规则")
report.write_text(body, encoding="utf-8")
