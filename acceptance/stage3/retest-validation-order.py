"""Reproduce TC-003.S2 authorization order with invalid and valid bodies."""
import importlib.util
import json
import pathlib
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)
OUT = pathlib.Path(__file__).resolve().parent / "evidence/TC-003-validation-order.json"
operator = env.API("运行操作员")
admin = env.API("系统管理员")


def post(body):
    request = urllib.request.Request(env.BASE + "/users", json.dumps(body).encode(),
        {"Content-Type": "application/json", "Authorization": "Bearer " + operator.token}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = {"httpStatus": response.status, "code": json.load(response).get("code")}
    except urllib.error.HTTPError as error:
        result = {"httpStatus": error.code, "code": json.loads(error.read()).get("code")}
    return result


before = admin("/users?page=1&size=100")["totalElements"]
invalid = post({"username": "S3_VALIDATION_ORDER"})
valid = post({"username": "S3_VALIDATION_ORDER", "password": "TestOnly!123456",
              "realName": "Stage3 denied", "role": "OPERATOR", "contact": "00000000000"})
after = admin("/users?page=1&size=100")["totalElements"]
evidence = {"observedAt": env.stamp(), "gitHead": "586ed9ed71abb62abc80baecaead028fa5b6c73f",
    "role": "OPERATOR", "endpoint": "POST /api/v1/users", "invalidBody": invalid,
    "validBody": valid, "userCountBefore": before, "userCountAfter": after,
    "finding": "Invalid unauthorised write is answered 400 before the role check; original TC-003.S2 requires 403 for an unauthorized write.",
    "reproduced": invalid["httpStatus"] == 400 and valid["httpStatus"] == 403 and before == after}
OUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(evidence, ensure_ascii=False))
