"""TC-003.S2: valid unauthorized write payloads and unchanged-row checks."""
import importlib.util
import json
import pathlib
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)
OUT = pathlib.Path(__file__).resolve().parent / "evidence/TC-003-valid-denials.json"
admin, config, operator = (env.API(role) for role in ("系统管理员", "配置管理员", "运行操作员"))


def counts():
    return {"users": admin("/users?page=1&size=100")["totalElements"],
            "devices": config("/devices?page=1&size=100")["totalElements"],
            "tasks": operator("/tasks?page=1&size=1")["totalElements"]}


def attempt(role, session, endpoint, body):
    request = urllib.request.Request(env.BASE + endpoint,
        json.dumps(body, ensure_ascii=False).encode(),
        {"Content-Type": "application/json", "Authorization": "Bearer " + session.token},
        method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = {"role": role, "endpoint": endpoint, "httpStatus": response.status}
    except urllib.error.HTTPError as error:
        result = {"role": role, "endpoint": endpoint, "httpStatus": error.code}
    return result


username = "S3DENIEDUSER"
user = {"username": username, "password": "TestOnly!123456", "realName": "Stage3 denied",
        "role": "OPERATOR", "contact": "00000000000"}
device = {k: v for k, v in env.load(env.FIXTURES / "devices.json")[0].items() if k != "capabilities"}
device.update(deviceCode="S3_DENIED_DEVICE", deviceName="Stage3 denied", accessEndpoint="http://127.0.0.1:8999",
              accessCredentialRef="local-test/S3_DENIED_DEVICE")
task = {"taskGoal": "阶段3权限检查：本请求必须在服务端拒绝，不创建任务", "taskFamily": "FLIGHT_CHANGE_RESPONSE"}
before = counts()
checks = [attempt("OPERATOR", operator, "/users", user),
          attempt("CONFIG_ADMIN", config, "/users", user),
          attempt("OPERATOR", operator, "/devices", device),
          attempt("SYSTEM_ADMIN", admin, "/devices", device),
          attempt("CONFIG_ADMIN", config, "/tasks", task),
          attempt("SYSTEM_ADMIN", admin, "/tasks", task),
          attempt("CONFIG_ADMIN", config, "/tasks/16/terminate",
                  {"reason": "阶段3权限检查", "confirmed": True})]
after = counts()
evidence = {"observedAt": env.stamp(), "gitHead": "0d798ceb53bc37498f353b4796f2081b92e2011b",
            "schema": "tip_stage2_v14", "validBody": True, "before": before,
            "checks": checks, "after": after,
            "pass": all(row["httpStatus"] == 403 for row in checks) and before == after}
OUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(evidence, ensure_ascii=False))
