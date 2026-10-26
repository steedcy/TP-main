"""Complete TC-085.S2 and F028.R06 with full audit masking/role coverage."""
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

stage = Path(__file__).resolve().parent
ev = stage / "evidence"
initial = ev / "SRS_F028-audit-masking-20261026T234315Z.json"
mask_file = ev / "SRS_F028-audit-masking-20261026T234329Z.json"
ui_file = ev / "SRS_F028-R06-audit-masking-device.json"
empty_file = ev / "TC-085-S2-empty-audit-query.json"
admin_file = ev / "TC-085-S2-admin-audit-pages-20261026T234438Z.json"
roles_file = ev / "SRS_F028-audit-roles-20261026T224546Z.json"
immutable_file = ev / "SRS_F028-audit-immutability-20261026T224625Z.json"
initial_data = json.loads(initial.read_text(encoding="utf-8"))
mask = json.loads(mask_file.read_text(encoding="utf-8"))
ui = json.loads(ui_file.read_text(encoding="utf-8"))
empty = json.loads(empty_file.read_text(encoding="utf-8"))
admin = json.loads(admin_file.read_text(encoding="utf-8"))
roles = json.loads(roles_file.read_text(encoding="utf-8"))
immutable = json.loads(immutable_file.read_text(encoding="utf-8"))
assert all(data["runtimeInput"] == "V1.5" for data in
           (initial_data, mask, ui, empty, admin, roles, immutable))
assert len(mask["sensitiveDetailRows"]) == 57 and mask["rowsWithDetail"] == 64
assert not mask["unparsedDetailIds"] and not mask["knownCredentialRawFound"]
assert mask["knownCredentialSampleCount"] >= 9
assert all(set(row["sensitiveFields"]) == {"accessCredentialRef"} and
           row["sensitiveFields"]["accessCredentialRef"]["masked"]
           for row in mask["sensitiveDetailRows"])
assert ui["route"] == "/operation-logs"
assert "S3_TC014_ALT_DISPLAY_B" in ui["rowText"]
assert "accessCredentialRef" in ui["detailText"] and "****" in ui["detailText"]
assert ui["editDeleteControls"] == 0 and (ev / ui["screenshot"]).is_file()
assert empty["route"] == "/operation-logs" and empty["rowCount"] == 0
assert "No data" in empty["emptyText"] and (ev / empty["screenshot"]).is_file()
assert admin["first"]["returned"] == 1000 and admin["second"]["returned"] > 0
assert admin["allUniqueIds"] and admin["first"]["returned"] + admin["second"]["returned"] == admin["second"]["totalElements"]
names = roles["usernameByRole"]
for role in ("配置管理员", "运行操作员"):
    assert roles["unfiltered"][role]["usernames"] == [names[role]]
    assert roles["crossUserFilter"][role]["usernames"] == [names[role]]
    assert roles["unfiltered"][role]["returned"] == roles["unfiltered"][role]["totalElements"]
assert immutable["before"] == {key: immutable["after"][key] for key in
                               ("sha256", "createdAt", "operationResult")}
assert all(not attempt["accepted"] for attempt in immutable["attempts"])

refs = ";".join("acceptance/stage3/evidence/" + path.name for path in
                (initial, mask_file, ui_file, ev / ui["screenshot"], empty_file,
                 ev / empty["screenshot"], admin_file, roles_file, immutable_file))
today = datetime.now().astimezone().date().isoformat()
path = stage / "steps.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["stepId"] == "TC-085.S2")
assert row["status"] == "NT" and row["issue"] == "NT-S3-008"
row.update(status="P", observedAt=today,
           actual="本轮系统管理员分页读全量1055条审计记录；配置管理员698条、运行操作员202条均只见自身，指定管理员账号筛选仍不能越权。扫描当前1052条记录中64条有详情，57条凭据引用均为掩码，已知九项测试凭据原值未出现；Chrome设备新增审计详情显示掩码且无原值入口。真实操作记录PUT/DELETE均拒绝、哈希不变，页面无编辑删除；空账号查询0行并显示空态。此前仅抽样导致的NT前置已补齐。",
           evidence=refs, issue="")
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

path = stage / "rules.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["ruleId"] == "SRS_F028.R06")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-085.S2", evidence=refs, issue="")
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

path = stage / "issues.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["编号"] == "NT-S3-008")
assert row["状态"] == "待补样本"
row["状态"] = "已补证"
row["证据"] = row["证据"] + ";" + refs
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
body = body.replace("P 41、F 59、NT 20、未执行 80", "P 42、F 59、NT 19、未执行 80", 1)
body = body.replace("P 89、F 39、NT 10、未执行 143", "P 90、F 39、NT 10、未执行 142", 1)
heading = "## 已执行\n\n"
assert heading in body
note = ("- TC-085.S2及`SRS_F028.R06`：系统管理员两页枚举全量1055条审计；配置管理员和操作员"
        "各自完整记录只见自身，传管理员账号筛选仍无法越权。当前1052条审计中64条有详情，57条"
        "凭据引用均掩码，九项已知测试凭据原值未出现；Chrome详情显示掩码且无原值入口。"
        "真实记录PUT/DELETE未接受且哈希不变，页面无编辑删除；无命中查询显示空态。"
        "原NT前置`NT-S3-008`标为已补证，步骤与R06判P。初次扫描将`credentialChanged`布尔元数据"
        "误归为凭据值的原始采样保留，修正分类后的全量采样及浏览器证据见`evidence/SRS_F028-*`"
        "和`evidence/TC-085-S2-*`。写入路径HTTP500另由`DEF-S3-061`跟踪。\n")
body = body.replace(heading, heading + note, 1)
now_bj = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")
body = body.replace("2026-10-27 06:46（Asia/Shanghai）", now_bj + "（Asia/Shanghai）", 1)
progress.write_text(body, encoding="utf-8")
print("recorded TC-085.S2 P, SRS_F028.R06 P, NT-S3-008 resolved")
