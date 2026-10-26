"""Record F028.R07 from full own-log enumeration and cross-user filter tests."""
import csv
import json
from pathlib import Path

stage = Path(__file__).resolve().parent
evidence = stage / "evidence/SRS_F028-audit-roles-20261026T224546Z.json"
data = json.loads(evidence.read_text(encoding="utf-8"))
assert data["runtimeInput"] == "V1.5" and data["isolatedSchema"] == "tip_stage2_v14"
names = data["usernameByRole"]
samples = data["unfiltered"]
assert samples["系统管理员"]["totalElements"] > 1000
assert {names["系统管理员"], names["配置管理员"], names["运行操作员"]}.issubset(
    samples["系统管理员"]["usernames"])
for role in ("配置管理员", "运行操作员"):
    own = samples[role]
    attack = data["crossUserFilter"][role]
    assert own["totalElements"] == own["returned"] > 0
    assert attack["totalElements"] == attack["returned"] > 0
    assert own["usernames"] == attack["usernames"] == [names[role]]

rule_path = stage / "rules.csv"
with rule_path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["ruleId"] == "SRS_F028.R07")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-085.S2",
           evidence="acceptance/stage3/evidence/" + evidence.name, issue="")
with rule_path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
body = body.replace("P 87、F 39、NT 10、未执行 145", "P 88、F 39、NT 10、未执行 144", 1)
heading = "## 已执行\n\n"
assert heading in body
note = ("- `SRS_F028.R07`：系统管理员操作记录查询返回多账号及SYSTEM记录；配置管理员与运行操作员"
        "分别完整枚举其698/202条当时可见记录，仅见自身账号，显式传入管理员账号筛选仍只能得到自身"
        "记录。角色范围规则判P。调用本身会增加登录审计，因此连续请求的总数不同；保存的是每次请求独立"
        "快照，不以数量相等为条件。TC-085.S2其他敏感字段与不可改删分支仍未穷尽，整步NT不变。"
        "证据见`evidence/SRS_F028-audit-roles-20261026T224546Z.json`。\n")
body = body.replace(heading, heading + note, 1)
progress.write_text(body, encoding="utf-8")
print("recorded SRS_F028.R07 P; TC-085.S2 unchanged")
