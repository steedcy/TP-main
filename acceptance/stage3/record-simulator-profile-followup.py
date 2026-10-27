"""Record two simulator-profile rule failures from fresh V1.5 API evidence."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
name = "TC-017-simulator-profile-followup-20261027T062616Z.json"
ev = json.loads((stage / "evidence" / name).read_text(encoding="utf-8"))
assert ev["runtimeInput"] == "V1.5" and ev["isolatedSchema"] == "tip_stage2_v14"
assert len(ev["matrix"]) == 5 and "CAP_SIM_STATUS" in ev["matrix"]["SIMULATOR"]
assert len(ev["samples"]) == 6
assert all(x["deviceTypeCode"] == "SIMULATOR" and x["simulatedDeviceType"] in ev["matrix"]
           for x in ev["samples"])
assert all(x["agentStatus"] == "ENABLED" and x["onlineStatus"] == "ONLINE"
           for x in ev["samples"])
assert all(x["missingTypes"] == ["CAP_SIM_STATUS"] and not x["outOfBoundaryTypes"]
           for x in ev["samples"])
ref = "acceptance/stage3/evidence/" + name
rules = stage / "rules.csv"
with rules.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
for identifier in ("SRS_F003.R04", "SRS_F006.R03"):
    row = next(x for x in rows if x["ruleId"] == identifier)
    assert row["status"] == "NOT_RUN"
    row.update(status="F", verifiedBy="TC-017.S3;TC-093.S1", evidence=ref,
               issue="DEF-S3-020")
with rules.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

issues = stage / "issues.csv"
with issues.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    issue_fields, issue_rows = reader.fieldnames, list(reader)
item = next(x for x in issue_rows if x["编号"] == "DEF-S3-020")
assert "SRS_F006A.R04" in item["关联需求规则"]
item["关联需求规则"] += ";SRS_F003.R04;SRS_F006.R03"
item["证据"] += ";" + ref
item["事实"] += " 本轮六个在线仿真体再次逐一比对五类矩阵，仍均缺必需的CAP_SIM_STATUS。"
with issues.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=issue_fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(issue_rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
assert "281 条需求规则为 P 106、F 49、NT 11、未执行 115" in body
body = body.replace("281 条需求规则为 P 106、F 49、NT 11、未执行 115",
                    "281 条需求规则为 P 106、F 51、NT 11、未执行 113", 1)
note = ("- `SRS_F003.R04/SRS_F006.R03`：本轮重新读取V1.5五类×能力矩阵与六个在线仿真代理，"
        "六台均已指定所模拟类型且业务能力没有越界，但按矩阵均缺少仿真体专属CAP_SIM_STATUS，"
        "所以两条包含完整能力画像要求的规则判F，复用`DEF-S3-020`。"
        "这不改变TC-017.S3已因Excel导出和继承缺口判F，也不将本轮TC-093同类设备业务调用否定。"
        "见`evidence/TC-017-simulator-profile-followup-*`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 14:23（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded SRS_F003.R04 and SRS_F006.R03 F")
