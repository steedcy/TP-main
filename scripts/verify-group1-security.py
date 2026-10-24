"""Run focused group 1 role and audit checks against the local test environment."""
import importlib.util
import json
import pathlib
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)


def raw(api, path, method="GET", body=None):
    payload = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    request = urllib.request.Request(
        env.BASE + path, payload,
        {"Content-Type": "application/json", "Authorization": "Bearer " + api.token},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    admin = env.API("系统管理员")
    operator = env.API("运行操作员")
    config = env.API("配置管理员")
    task_page = operator("/tasks?page=1&size=1")
    before_count = task_page["totalElements"]
    task_id = task_page["content"][0]["id"] if task_page["content"] else None
    before_audit = admin("/operation-logs?operationType=ACCESS_DENIED&page=1&size=1")["totalElements"]

    request = {"taskGoal": "首组权限回归：此请求必须在鉴权层拒绝，不能创建任务", "taskFamily": "FLIGHT_CHANGE_RESPONSE"}
    checks = []
    for label, api in (("CONFIG_ADMIN", config), ("SYSTEM_ADMIN", admin)):
        status, body = raw(api, "/tasks", "POST", request)
        require(status == 403, f"{label} task submission returned {status}, expected 403")
        checks.append({"role": label, "method": "POST", "path": "/tasks", "httpStatus": status, "code": body.get("code")})

    require(operator("/tasks?page=1&size=1")["totalElements"] == before_count,
            "a rejected request changed the task count")
    if task_id is not None:
        for path in (f"/tasks/{task_id}", f"/tasks/{task_id}/events", f"/tasks/{task_id}/plan-versions"):
            status, body = raw(config, path)
            require(status == 403, f"CONFIG_ADMIN history {path} returned {status}")
            checks.append({"role": "CONFIG_ADMIN", "method": "GET", "path": path, "httpStatus": status, "code": body.get("code")})
            status, _ = raw(admin, path)
            require(status == 200, f"SYSTEM_ADMIN history {path} returned {status}")
            checks.append({"role": "SYSTEM_ADMIN", "method": "GET", "path": path, "httpStatus": status})

    audit = admin("/operation-logs?operationType=ACCESS_DENIED&page=1&size=100")
    require(audit["totalElements"] >= before_audit + 2, "denials were not audited")
    recent = audit["content"][: audit["totalElements"] - before_audit]
    for role in ("CONFIG_ADMIN", "SYSTEM_ADMIN"):
        require(any(row.get("role") == role and row.get("operationResult") == "FAILED"
                    and row.get("sourceIp") for row in recent), f"missing {role} denial role/IP audit")
    result = {"recordedAt": env.stamp(), "scope": "GROUP1_TARGETED_API_REGRESSION",
              "build": "local rebuild of a7c1c4c", "checks": checks,
              "tasksBefore": before_count, "tasksAfter": operator("/tasks?page=1&size=1")["totalElements"],
              "newDeniedAuditCount": audit["totalElements"] - before_audit,
              "result": "PASS"}
    destination = env.EVIDENCE / "20261024-group1-role-api.json"
    env.save(destination, result)
    print(json.dumps({"result": result["result"], "checks": len(checks),
                      "newDeniedAuditCount": result["newDeniedAuditCount"], "evidence": str(destination)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
