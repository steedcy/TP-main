"""Record SRS_F007.R07 missing event persistence for successful queries."""
import csv
import json
from pathlib import Path

p = Path(__file__).resolve().parent
name = "TC-023-message-event-coverage-20261026T123647Z.json"
ev = json.loads((p / "evidence" / name).read_text(encoding="utf-8"))
assert [m["messageType"] for m in ev["messages"]] == ["CAPABILITY_QUERY", "STATUS_QUERY"]
assert all(m["apiCode"] == 200 for m in ev["messages"])
assert ev["before"] == ev["after"]
assert ev["agentAfter"]["workStatus"] == "IDLE"
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
    if row["ruleId"] == "SRS_F007.R07":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", verifiedBy="TC-023.S2", evidence=ref, issue="DEF-S3-054")
save(file, fields, rows)

file, fields, rows = load("steps.csv")
for row in rows:
    if row["stepId"] == "TC-023.S2":
        assert row["status"] == "F"
        row["actual"] += "；两种成功代理查询未写任务/设备事件"
        row["evidence"] += ";" + ref
        row["issue"] += ";DEF-S3-054"
save(file, fields, rows)

file, fields, rows = load("issues.csv")
assert not any(row["编号"] == "DEF-S3-054" for row in rows)
rows.append({"编号": "DEF-S3-054", "类型": "缺陷", "级别": "中",
    "关联用例步骤": "TC-023.S2", "关联需求规则": "SRS_F007.R07", "状态": "待修复",
    "事实": "系统管理员以当前接口可接受的消息类型字面量作指令号，CAPABILITY_QUERY及STATUS_QUERY均返回成功；调用前后该代理设备事件39、全库任务事件886及代理命令86均不变，成功查询交互未写任务/设备事件",
    "证据": ref,
    "阶段4动作": "为成功的代理查询及其他六类消息统一写入可追溯事件，关联指令号、请求响应摘要及结果；复测事件唯一性和重试幂等"})
save(file, fields, rows)

report = p / "阶段3-复测进度.md"
body = report.read_text(encoding="utf-8")
body = body.replace("2026-10-26 20:35（Asia/Shanghai）", "2026-10-26 20:37（Asia/Shanghai）", 1)
body = body.replace(
    "原 200 步：P 39、F 55、NT 19、未执行 87；27 项 AC 为 F 5、NT 1、未执行 21；281 条需求规则为 P 63、F 33、NT 9、未执行 176。",
    "原 200 步：P 39、F 55、NT 19、未执行 87；27 项 AC 为 F 5、NT 1、未执行 21；281 条需求规则为 P 63、F 34、NT 9、未执行 175。", 1)
anchor = "- `SRS_F007.R06`："
addition = (
    "- `SRS_F007.R07`：系统管理员在V1.5当前可接受的指令号字面量下实际完成能力查询及状态查询，"
    "两次均200；调用前后该代理设备事件39、任务事件886、代理命令86均未增加。"
    "规则要求所有消息交互进时间线或设备事件，故判F（`DEF-S3-054`），并补入TC-023.S2原F步骤。"
    "这也不代表唯一指令号缺陷已修复；原始调用及计数见"
    "`evidence/TC-023-message-event-coverage-20261026T123647Z.json`。\n"
)
assert anchor in body
body = body.replace(anchor, addition + anchor, 1)
body = body.replace("继续剩余 87 个原步骤、21 项未执行 AC 和 176 条未执行规则",
                    "继续剩余 87 个原步骤、21 项未执行 AC 和 175 条未执行规则")
report.write_text(body, encoding="utf-8")
