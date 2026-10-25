"""Live TC-002.S1-S3 lockout retest in the isolated V1.5 schema.

Creates three temporary accounts, leaves them inactive, and writes no
passwords, bearer tokens, or password hashes to evidence.
"""
import datetime
import importlib.util
import json
import pathlib
import secrets
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)
DEST = pathlib.Path(__file__).resolve().parent / "evidence/TC-002-lockout.json"
admin = env.API("系统管理员")


def login(username, password):
    request = urllib.request.Request(env.BASE + "/auth/login",
        data=json.dumps({"username": username, "password": password}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = json.load(response)
            return {"httpStatus": response.status, "code": body.get("code"),
                    "sessionCreated": bool(body.get("data", {}).get("token")),
                    "message": body.get("message")}
    except urllib.error.HTTPError as error:
        body = json.loads(error.read())
        return {"httpStatus": error.code, "code": body.get("code"),
                "sessionCreated": False, "message": body.get("message")}


def users():
    return {row["username"]: row for row in admin("/users?page=1&size=100")["content"]}


def state(username):
    row = users()[username]
    return {"status": row["status"], "failedLoginAttempts": row["failedLoginAttempts"]}


stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
password = "T3!" + secrets.token_urlsafe(17)
wrong = "wrong-T3!" + secrets.token_urlsafe(12)
names = {key: "s3" + key.lower() + stamp for key in "ABC"}
evidence = {"observedAt": env.stamp(), "gitHead": "0d798ceb53bc37498f353b4796f2081b92e2011b",
            "schema": "tip_stage2_v14", "accounts": names, "checks": {}}
created = {}
try:
    for key, username in names.items():
        created[key] = admin("/users", "POST", {"username": username,
            "password": password, "realName": "Stage 3 " + key,
            "role": "OPERATOR", "contact": "00000000000"})["id"]
    admin("/users/" + str(created["C"]) + "/status", "POST", {"status": "INACTIVE"})
    evidence["checks"]["initialStates"] = {key: state(name) for key, name in names.items()}
    evidence["checks"]["unknownLogin"] = login("s3missing" + stamp, wrong)
    evidence["checks"]["inactiveLogin"] = login(names["C"], password)
    evidence["checks"]["accountBWrongLogin"] = login(names["B"], wrong)
    evidence["checks"]["accountAAfterS1"] = state(names["A"])
    evidence["checks"]["accountBAfterS1"] = state(names["B"])
    evidence["checks"]["aFailures"] = []
    for attempt in range(3):
        evidence["checks"]["aFailures"].append({"response": login(names["A"], wrong),
                                                  "state": state(names["A"])})
    evidence["checks"]["lockedCorrectPassword"] = login(names["A"], password)
    admin("/users/" + str(created["A"]) + "/unlock", "POST")
    evidence["checks"]["afterUnlock"] = state(names["A"])
    evidence["checks"]["afterUnlockWrong"] = []
    for attempt in range(2):
        evidence["checks"]["afterUnlockWrong"].append({"response": login(names["A"], wrong),
                                                        "state": state(names["A"])})
    evidence["checks"]["correctAfterTwoFailures"] = login(names["A"], password)
    evidence["checks"]["afterCorrect"] = state(names["A"])
    evidence["checks"]["wrongAfterCorrect"] = login(names["A"], wrong)
    evidence["checks"]["afterOneMoreWrong"] = state(names["A"])
    rows = admin("/operation-logs?page=1&size=100")["content"]
    related = [row for row in rows if row.get("username") in names.values()
               or any(name in str(row.get("targetId", "")) for name in names.values())]
    evidence["checks"]["audit"] = {"rowCount": len(related),
        "hasTimeIpResult": all((row.get("operationTime") or row.get("createdAt"))
                               and row.get("sourceIp") and row.get("operationResult")
                               for row in related if row.get("operationType") == "LOGIN"),
        "containsPassword": password in json.dumps(related) or wrong in json.dumps(related)}
finally:
    for key, user_id in created.items():
        if key != "C":
            admin("/users/" + str(user_id) + "/status", "POST", {"status": "INACTIVE"})
    evidence["cleanup"] = {key: state(name) for key, name in names.items() if key in created}
    DEST.parent.mkdir(exist_ok=True)
    DEST.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(json.dumps({"evidence": str(DEST), "checks": evidence["checks"],
                  "cleanup": evidence["cleanup"]}, ensure_ascii=False))
