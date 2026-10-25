"""Record TC-086 partial sensitive-data retest and hash exposure finding."""
import csv
import json
from pathlib import Path

here = Path(__file__).resolve().parent
ev = json.loads((here / "evidence/TC-086-sensitive.json").read_text(encoding="utf-8"))
assert ev["passwordHashesAllBcrypt"] and not ev["userPlainPasswordsInDatabaseHashColumn"]
assert ev["userListExposesPasswordHash"] and ev["operationLogCountChecked"] >= 100
assert not ev["plainUserPasswordsInLogDetail"] and not ev["plainDeviceTokensInLogDetail"]


def read(path):
    with (here / path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(path, rows):
    with (here / path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


steps = read("steps.csv")
for row in steps:
    if row["stepId"] == "TC-086.S1":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", observedAt="2026-10-25", issue="DEF-S3-010",
                   actual="隔离库15个账号为bcrypt摘要；六台设备令牌持久化为哈希与密文，145条审计详情未见原始凭据；但管理员账号列表响应暴露passwordHash字段",
                   evidence="acceptance/stage3/evidence/TC-086-sensitive.json")
    elif row["stepId"] == "TC-086.S2":
        assert row["status"] == "NOT_RUN"
        row.update(status="NT", observedAt="2026-10-25", issue="NT-S3-009",
                   actual="登录、设备配置及审计的数据库/API凭据抽查完成；尚未覆盖所有失败、变更与追溯页面分支",
                   evidence="acceptance/stage3/evidence/TC-086-sensitive.json")
write("steps.csv", steps)

rules = read("rules.csv")
for row in rules:
    if row["ruleId"] == "SRS_NF001.R01":
        assert row["status"] == "NOT_RUN"
        row.update(status="NT", verifiedBy="TC-086.S1", issue="NT-S3-009",
                   evidence="acceptance/stage3/evidence/TC-086-sensitive.json")
write("rules.csv", rules)

issues = read("issues.csv")
for ident, kind, level, step, rule, status, fact, action in [
    ("DEF-S3-010", "缺陷", "中", "TC-086.S1", "SRS_NF001", "待修复",
     "管理员GET /users响应包含passwordHash；虽未暴露原始密码，密码摘要不应发给前端", "用户列表和创建响应改为无凭据视图；复测授权与页面显示"),
    ("NT-S3-009", "前置缺口", "待定", "TC-086.S2", "SRS_NF001.R01", "待补分支",
     "本轮仅检查隔离库字段、用户/设备列表和145条审计详情；失败、配置变更与追溯页面分支未穷尽", "补异常与变更分支及页面敏感信息检查"),
]:
    assert ident not in {row["编号"] for row in issues}
    issues.append(dict(zip(issues[0].keys(), [ident, kind, level, step, rule, status, fact,
                                             "acceptance/stage3/evidence/TC-086-sensitive.json", action])))
write("issues.csv", issues)
