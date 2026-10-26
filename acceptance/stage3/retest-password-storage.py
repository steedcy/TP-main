"""SRS_F001.R01: inspect salted irreversible hashes without exposing secrets."""
import importlib.util
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
db_spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(db_spec)
db_spec.loader.exec_module(db)
admin = local.API("系统管理员")
stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
names = ["s3hasha" + stamp, "s3hashb" + stamp]
password = "S3!" + secrets.token_urlsafe(20)
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "accounts": names, "cleanup": {}}
out = stage / "evidence" / ("TC-001-password-storage-" + stamp + ".json")
created = []
try:
    for name in names:
        user = admin("/users", "POST", {"username": name, "password": password,
            "realName": "Stage 3 hash", "role": "OPERATOR", "contact": "00000000000"})
        created.append(user["id"])
    hashes = db.query(db.source,
        "SELECT username,password_hash FROM tip_stage2_v14.users WHERE username IN (" +
        ",".join("'" + name + "'" for name in names) + ") ORDER BY username").splitlines()
    parsed = dict(row.split("|", 1) for row in hashes)
    assert set(parsed) == set(names)
    ev["hashChecks"] = {
        "rowCount": len(parsed),
        "allBcryptFormat": all(len(h) == 60 and h.startswith(("$2a$", "$2b$", "$2y$"))
                               for h in parsed.values()),
        "samePasswordDifferentHashes": parsed[names[0]] != parsed[names[1]],
        "plaintextAbsentFromHashRows": all(password not in h for h in parsed.values()),
        "hashLengths": [len(parsed[name]) for name in names],
        "algorithmPrefixes": [parsed[name][:4] for name in names]}
    ev["loginChecks"] = []
    for name in names:
        result = local.request(local.BASE + "/auth/login", "POST",
                               {"username": name, "password": password})
        ev["loginChecks"].append({"username": name, "accepted": bool(result["data"]["token"])})
        local.request(local.BASE + "/auth/logout", "POST", token=result["data"]["token"])
    logs = admin("/operation-logs?page=1&size=100")["content"]
    related = [row for row in logs if row.get("username") in names]
    ev["auditChecks"] = {"rowCount": len(related),
        "loginAndLogoutPresent": all(
            {row["operationType"] for row in related if row["username"] == name}
            >= {"LOGIN", "LOGOUT"} for name in names),
        "plaintextAbsent": password not in json.dumps(related, ensure_ascii=False)}
finally:
    for user_id in created:
        try:
            admin("/users/" + str(user_id) + "/status", "POST", {"status": "INACTIVE"})
        except Exception as error:
            ev["cleanup"][str(user_id)] = str(error)
        else:
            ev["cleanup"][str(user_id)] = "INACTIVE"
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "checks": ev.get("hashChecks"),
                  "loginChecks": ev.get("loginChecks"), "auditChecks": ev.get("auditChecks"),
                  "cleanup": ev["cleanup"]}, ensure_ascii=False))
