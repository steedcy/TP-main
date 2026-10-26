"""Record TC-024.S2 and SRS_F007.R03 from signed adapter evidence."""
import csv
import json
from pathlib import Path

p = Path(__file__).resolve().parent
name = "TC-024-motion-adapter-20261026T123208Z.json"
ev = json.loads((p / "evidence" / name).read_text(encoding="utf-8"))
results = {next(iter(row["addedFields"])): row["response"]["result"] for row in ev["cases"]}
assert ev["baseline"]["response"]["result"] == "SUCCESS"
assert {name for name, result in results.items() if result == "SUCCESS"} == {
    "attitude", "pathPoints", "lostConnectionParking"}
assert len(results) == 8
assert ev["agentBefore"]["workStatus"] == ev["agentAfter"]["workStatus"] == "IDLE"
assert ev["agentAfter"]["currentTaskId"] is None
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
    if row["stepId"] == "TC-024.S2":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", observedAt="2026-10-26",
            actual="签名航显仿真适配器能力测试中正常展示成功；八类安全字段逐一加入，speed/acceleration/obstacleAvoidance/emergencyStop/speedLimit拒绝，但attitude/pathPoints/lostConnectionParking仍SUCCESS。此为适配器路径，平台拦截日志及其余正常意图待单测",
            evidence=ref, issue="DEF-S3-052")
save(file, fields, rows)

file, fields, rows = load("rules.csv")
for row in rows:
    if row["ruleId"] == "SRS_F007.R03":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", verifiedBy="TC-024.S2", evidence=ref, issue="DEF-S3-052")
save(file, fields, rows)

file, fields, rows = load("issues.csv")
assert not any(row["编号"] == "DEF-S3-052" for row in rows)
rows.append({"编号": "DEF-S3-052", "类型": "缺陷", "级别": "高",
    "关联用例步骤": "TC-024.S2", "关联需求规则": "SRS_F007.R03", "状态": "待修复",
    "事实": "签名仿真适配器在正常CAP_INFO_DISPLAY输入之外加入attitude、pathPoints、lostConnectionParking各自仍返回SUCCESS；另五项安全字段返回FAILED。适配器没有完整拒绝姿态、路径点、失联停靠别名，与模板层DEF-S3-026相互独立",
    "证据": ref,
    "阶段4动作": "补齐统一发送端与仿真适配器的中英文/驼峰安全字段矩阵，记录平台拦截事件；端到端重测八类拒绝和正常业务意图"})
save(file, fields, rows)

report = p / "阶段3-复测进度.md"
body = report.read_text(encoding="utf-8")
body = body.replace("2026-10-26 20:28（Asia/Shanghai）", "2026-10-26 20:32（Asia/Shanghai）", 1)
body = body.replace(
    "原 200 步：P 39、F 54、NT 19、未执行 88；27 项 AC 为 F 5、NT 1、未执行 21；281 条需求规则为 P 63、F 31、NT 9、未执行 178。",
    "原 200 步：P 39、F 55、NT 19、未执行 87；27 项 AC 为 F 5、NT 1、未执行 21；281 条需求规则为 P 63、F 32、NT 9、未执行 177。", 1)
anchor = "- TC-024.S1："
addition = (
    "- TC-024.S2与`SRS_F007.R03`：使用真实设备令牌经航显仿真适配器能力测试接口送八个单独安全字段。"
    "正常展示与五个阻断字段按预期返回；`attitude`、`pathPoints`、`lostConnectionParking`含在待调用参数里仍返回SUCCESS，"
    "步骤与规则判F，新增适配器层`DEF-S3-052`（与模板层`DEF-S3-026`区分）。"
    "本次只验证签名适配器路径，平台统一发送端的拦截事件及五类正常业务意图仍须单测；设备代理前后在线空闲。"
    "原始逐字段响应在`evidence/TC-024-motion-adapter-20261026T123208Z.json`。\n"
)
assert anchor in body
body = body.replace(anchor, addition + anchor, 1)
body = body.replace("继续剩余 88 个原步骤、21 项未执行 AC 和 178 条未执行规则",
                    "继续剩余 87 个原步骤、21 项未执行 AC 和 177 条未执行规则")
report.write_text(body, encoding="utf-8")
