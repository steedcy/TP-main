"""SRS_F001.R06: verify failed/successful login and logout audit rows."""
import importlib.util
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
admin = local.API("系统管理员")
stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
username = "s3audit" + stamp
password = "S3!" + secrets.token_urlsafe(18)
wrong = "bad!" + secrets.token_urlsafe(18)
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "username": username, "cleanup": {}}
out = stage / "evidence" / ("TC-001-session-audit-" + stamp + ".json")
user_id = None
token = None
try:
    user_id = admin("/users", "POST", {"username": username, "password": password,
        "realName": "Stage 3 audit", "role": "OPERATOR", "contact": "00000000000"})["id"]
    ev["userId"] = user_id
    try:
        local.request(local.BASE + "/auth/login", "POST",
                      {"username": username, "password": wrong})
        ev["failedLogin"] = {"unexpectedSuccess": True}
    except RuntimeError as error:
        ev["failedLogin"] = {"unexpectedSuccess": False, "error": str(error)}
    response = local.request(local.BASE + "/auth/login", "POST",
                             {"username": username, "password": password})
    token = response["data"]["token"]
    ev["successfulLogin"] = {"httpCode": response["code"],
                             "sessionCreated": bool(token)}
    logout = local.request(local.BASE + "/auth/logout", "POST", token=token)
    ev["logout"] = {"httpCode": logout["code"]}
    rows = admin("/operation-logs?username=" + quote(username) + "&page=1&size=100")["content"]
    ev["auditRows"] = [{key: row.get(key) for key in (
        "id", "userId", "username", "role", "operationType", "operationResult",
        "sourceIp", "operationTime", "createdAt", "operationTarget", "detail")}
        for row in rows]
    ev["containsCredential"] = any(
        text in json.dumps(ev["auditRows"], ensure_ascii=False)
        for text in (password, wrong, token))
finally:
    if user_id is not None:
        try:
            admin("/users/" + str(user_id) + "/status", "POST", {"status": "INACTIVE"})
            ev["cleanup"]["userStatus"] = "INACTIVE"
        except Exception as error:
            ev["cleanup"]["error"] = str(error)
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "operations": [
    (row["operationType"], row["operationResult"]) for row in ev.get("auditRows", [])],
    "containsCredential": ev.get("containsCredential"), "cleanup": ev["cleanup"]},
    ensure_ascii=False))
