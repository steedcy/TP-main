"""Directed server-side role gate check; stores no credentials or bearer tokens."""
import importlib.util
import json
import urllib.error
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)

admin = env.API("系统管理员")
operator = env.API("运行操作员")
config = env.API("配置管理员")
before = operator("/tasks?page=1&size=1")["totalElements"]
checks = []
for role, api in (("CONFIG_ADMIN", config), ("SYSTEM_ADMIN", admin)):
    request = urllib.request.Request(env.BASE + "/tasks", data=json.dumps({
        "taskGoal": "阶段1权限定向检查：禁止创建", "taskFamily": "FLIGHT_CHANGE_RESPONSE"
    }, ensure_ascii=False).encode(), headers={"Content-Type": "application/json",
                                              "Authorization": "Bearer " + api.token}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
    assert status == 403, (role, status)
    checks.append({"role": role, "httpStatus": status})
after = operator("/tasks?page=1&size=1")["totalElements"]
assert after == before, (before, after)
audit = admin("/operation-logs?operationType=ACCESS_DENIED&page=1&size=20")["content"]
assert all(any(row.get("role") == item["role"] and row.get("sourceIp")
               and row.get("operationResult") == "FAILED" for row in audit) for item in checks)

evidence = {"observedAt": datetime.now(timezone.utc).isoformat(), "checks": checks,
            "tasksBefore": before, "tasksAfter": after, "denialRoleIpAudit": True, "result": "PASS"}
target = Path(__file__).parent / "evidence" / "authorization-directed.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"result": "PASS", "evidence": str(target)}, ensure_ascii=False))
