"""Record only independently checked V1.5 stage-3 results in the ledger."""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EV = HERE / "evidence"


def read(name):
    return json.loads((EV / name).read_text(encoding="utf-8"))


auth = read("TC-001-auth.json")
lock = read("TC-002-lockout.json")["checks"]
ui = read("TC-002-login-ui.json")
roles = read("TC-003-role-menus.json")
denials = read("TC-003-valid-denials.json")
audit = read("TC-003-audit-scope.json")
assert all(auth["results"].values())
assert ui["pass"] and len(ui["attempts"]) == 7
assert lock["initialStates"]["A"] == {"status": "ACTIVE", "failedLoginAttempts": 0}
assert lock["accountAAfterS1"]["failedLoginAttempts"] == 0
assert [item["state"]["failedLoginAttempts"] for item in lock["aFailures"]] == [1, 2, 3]
assert [item["state"]["status"] for item in lock["aFailures"]] == ["ACTIVE", "ACTIVE", "LOCKED"]
assert lock["lockedCorrectPassword"]["sessionCreated"] is False
assert lock["afterUnlock"] == {"status": "ACTIVE", "failedLoginAttempts": 0}
assert lock["correctAfterTwoFailures"]["sessionCreated"] is True
assert lock["afterCorrect"] == {"status": "ACTIVE", "failedLoginAttempts": 0}
assert lock["afterOneMoreWrong"] == {"status": "ACTIVE", "failedLoginAttempts": 1}
assert lock["audit"]["rowCount"] >= 6 and lock["audit"]["hasTimeIpResult"]
assert not lock["audit"]["containsPassword"]
assert roles["pass"] and denials["pass"] and audit["pass"]

updates = {
    "TC-001.S1": ("P", "空值提示、边界、密文且无明文切换；非法表单不发认证请求", "TC-001-auth.json;TC-001-S1-empty.png;TC-001-S1-boundaries.png", ""),
    "TC-001.S2": ("P", "三角色登录进入总览；退出后旧令牌401且受保护页跳转登录", "TC-001-auth.json;TC-001-S2-admin.png;TC-001-S2-oprator.png;TC-001-S2-set.png", ""),
    "TC-001.S3": ("P", "本轮登录/退出审计有账号、时间、IP、结果，未含口令原值", "TC-001-auth.json", ""),
    "TC-002.S1": ("P", "不存在、停用、B错密均统一提示且无会话；A计数仍0；失败留痕", "TC-002-lockout.json;TC-002-login-ui.json;TC-002-unknown.png;TC-002-inactive.png;TC-002-b-wrong.png", ""),
    "TC-002.S2": ("P", "A第1/2次未锁、第3次锁；锁后正确口令仍拒绝，页面统一提示", "TC-002-lockout.json;TC-002-login-ui.json;TC-002-a-wrong-1.png;TC-002-a-wrong-2.png;TC-002-a-wrong-3.png;TC-002-a-locked-correct.png", ""),
    "TC-002.S3": ("P", "管理员解锁清零；两次错密后正确登录清零；再错一次不锁；审计无原口令", "TC-002-lockout.json", ""),
    "TC-002.S4": ("NT", "认证服务及数据库故障未实施隔离注入；共享PostgreSQL不可直接停机，需独立故障夹具与恢复证据", "", "NT-S3-001"),
    "TC-003.S1": ("P", "三角色菜单与授权页实测；管理员建账号、配置员连接测试、操作员任务提交均获授权", "TC-003-role-menus.json;TC-002-lockout.json;TC-003-permissions.json", ""),
    "TC-003.S2": ("P", "七项有效载荷越权写入均403且用户/设备/任务数量不变；授权写入可执行", "TC-003-valid-denials.json;TC-002-lockout.json;TC-003-permissions.json", ""),
    "TC-003.S3": ("P", "两类非管理员带admin筛选也仅见自身；管理员见多角色、关键操作及越权事件", "TC-003-audit-scope.json", ""),
}

path = HERE / "steps.csv"
with path.open(encoding="utf-8-sig", newline="") as source:
    rows = list(csv.DictReader(source))
assert len(rows) == 200
for row in rows:
    if row["stepId"] not in updates:
        continue
    status, actual, evidence, issue = updates[row["stepId"]]
    assert row["status"] in {"NOT_RUN", status}
    row.update(status=status, observedAt="2026-10-25", actual=actual,
               evidence=";".join("acceptance/stage3/evidence/" + item for item in evidence.split(";")) if evidence else "",
               issue=issue)
with path.open("w", encoding="utf-8-sig", newline="") as target:
    writer = csv.DictWriter(target, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

rules_path = HERE / "rules.csv"
with rules_path.open(encoding="utf-8-sig", newline="") as source:
    rules = list(csv.DictReader(source))
for row in rules:
    if row["ruleId"] == "SRS_F001.R03":
        row.update(status="P", verifiedBy="TC-002.S1", evidence="acceptance/stage3/evidence/TC-002-lockout.json")
    elif row["ruleId"] == "SRS_F001.R04":
        row.update(status="P", verifiedBy="TC-003.S2", evidence="acceptance/stage3/evidence/TC-003-valid-denials.json")
with rules_path.open("w", encoding="utf-8-sig", newline="") as target:
    writer = csv.DictWriter(target, fieldnames=rules[0].keys())
    writer.writeheader()
    writer.writerows(rules)

print(json.dumps({"steps": {status: sum(row["status"] == status for row in rows)
                            for status in ("P", "F", "NT", "NOT_RUN")},
                  "rules": {status: sum(row["status"] == status for row in rules)
                            for status in ("P", "F", "NT", "NOT_RUN")}}, ensure_ascii=False))
