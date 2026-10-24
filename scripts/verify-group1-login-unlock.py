"""Verify local login lock/unlock audit while keeping credentials out of evidence."""
import importlib.util
import json
import pathlib
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)


def login(username, password):
    body = json.dumps({"username": username, "password": password}).encode()
    request = urllib.request.Request(env.BASE + "/auth/login", body,
                                     {"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


admin = env.API("系统管理员")
username, password = env.account("配置管理员")
status, response = login(username, password)
assert status == 200, "test account did not start active"
user_id = response["data"]["user"]["id"]
before_rows = admin("/operation-logs?page=1&size=1")["content"]
before_id = before_rows[0]["id"] if before_rows else 0
try:
    failures = [login(username, password + "-wrong")[0] for _ in range(3)]
    assert all(status != 200 for status in failures), "wrong password was accepted"
    assert login(username, password)[0] != 200, "three failed logins did not lock the account"
finally:
    users = admin("/users?page=1&size=100")["content"]
    target = next(user for user in users if user["id"] == user_id)
    if target["status"] == "LOCKED":
        admin(f"/users/{user_id}/unlock", "POST")

assert login(username, password)[0] == 200, "account did not recover after unlock"
logs = admin(f"/operation-logs?username={username}&page=1&size=100")["content"]
new = [row for row in logs if row["id"] > before_id]
assert sum(row["operationType"] == "LOGIN" and row["operationResult"] == "FAILED"
           and row.get("role") == "CONFIG_ADMIN" and bool(row.get("sourceIp")) for row in new) >= 3
assert any(row["id"] > before_id and row["operationTarget"] == username
           and row["operationType"] == "MANUAL_HANDLING" and row.get("sourceIp")
           and row.get("role") == "SYSTEM_ADMIN" for row in
           admin("/operation-logs?operationType=MANUAL_HANDLING&page=1&size=100")["content"])

result = {"recordedAt": env.stamp(), "scope": "GROUP1_LOGIN_UNLOCK_AUDIT",
          "failedLoginStatuses": failures, "lockedAfterThree": True,
          "unlockedBySystemAdmin": True, "loginAfterUnlock": "SUCCESS",
          "auditHasRoleAndSourceIp": True, "result": "PASS"}
out = env.EVIDENCE / "20261024-group1-login-unlock.json"
env.save(out, result)
print(json.dumps({"result": "PASS", "evidence": str(out)}, ensure_ascii=False))
