"""Record TC-092.S1 and its one-environment scope rule from live evidence."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
file = stage / "evidence/TC-092-single-environment-20261027T040146Z.json"
ev = json.loads(file.read_text(encoding="utf-8"))
assert ev["runtimeInput"] == "V1.5"
assert ev["backendHealth"] == {"httpStatus": 200, "body": {"status": "UP"}}
assert ev["frontend"]["httpStatus"] == 200 and ev["frontend"]["htmlShell"]
assert ev["database"].startswith("airport_ai|public|")
assert ev["coreTask"]["id"] == 73 and ev["coreTask"]["status"] == "COMPLETED"
assert ev["coreTask"]["taskFamily"] == "FLIGHT_CHANGE_RESPONSE"
assert len(ev["assignments"]) == 4 and all(a["stepStatus"] == "COMPLETED" for a in ev["assignments"])
assert any(p["source"] == "AUTONOMOUS" and all(p[k] == "PASS" for k in
           ("structureCheckResult", "capabilityCheckResult", "constraintCheckResult"))
           for p in ev["planVersions"])
assert len(ev["events"]) >= 20
assert "backend" in ev["startupRecords"] and "frontend" in ev["startupRecords"]
ref = "acceptance/stage3/evidence/" + file.name

for filename, key, value in (("steps.csv", "stepId", "TC-092.S1"),
                             ("rules.csv", "ruleId", "SRS_NF013.R01")):
    target = stage / filename
    with target.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    row = next(r for r in rows if r[key] == value)
    assert row["status"] == "NOT_RUN"
    row["status"] = "P"
    row["evidence"] = ref
    if filename == "steps.csv":
        row["observedAt"] = datetime.now().strftime("%Y-%m-%d")
        row["actual"] = ("当前单台Windows开发验证主机上，阶段3启动记录含前端与后端；本轮前端HTTP200、"
                         "后端健康UP、隔离库可查询。此环境内任务73航班变更四步均完成，三类校验PASS，"
                         "27条事件可查。不将此范围验证解释为高可用、容灾或八小时稳定性通过。")
    else:
        row["verifiedBy"] = "TC-092.S1"
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
assert "原 200 步：P 42、F 62、NT 19、未执行 77" in body
assert "281 条需求规则为 P 92、F 44、NT 11、未执行 134" in body
body = body.replace("原 200 步：P 42、F 62、NT 19、未执行 77",
                    "原 200 步：P 43、F 62、NT 19、未执行 76", 1)
body = body.replace("281 条需求规则为 P 92、F 44、NT 11、未执行 134",
                    "281 条需求规则为 P 93、F 44、NT 11、未执行 133", 1)
note = ("- TC-092.S1与`SRS_NF013.R01`：单台Windows开发验证主机的本轮启动记录、前后端健康、"
        "隔离数据库连通均可复核；同一环境内航班变更任务73的四步全完成、三类校验PASS、27条事件可查。"
        "该项仅验证单套环境可以运行并完成一条核心任务，判P；不扩展为高可用、容灾、负载或八小时稳定性结论。"
        "见`evidence/TC-092-single-environment-20261027T040146Z.json`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 12:00（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded TC-092.S1 P and SRS_NF013.R01 P")
