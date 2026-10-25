"""TC-003.S3: fresh all-role audit visibility check without sensitive values."""
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)
OUT = pathlib.Path(__file__).resolve().parent / "evidence/TC-003-audit-scope.json"
sessions = {name: env.API(name) for name in ("系统管理员", "配置管理员", "运行操作员")}
scope = {}
for role, session in sessions.items():
    rows = session("/operation-logs?" + ("" if role == "系统管理员" else "username=admin&") + "page=1&size=100")["content"]
    username = env.account(role)[0]
    scope[role] = {"rowCount": len(rows), "visibleUsernames": sorted({row.get("username") for row in rows if row.get("username")}),
                   "ownOnly": all(row.get("username") == username for row in rows),
                   "eventTypes": sorted({row.get("operationType") for row in rows if row.get("operationType")}),
                   "hasTimeIpResult": all((row.get("operationTime") or row.get("createdAt"))
                           and row.get("sourceIp") and row.get("operationResult") for row in rows)}
evidence = {"observedAt": env.stamp(), "gitHead": "0d798ceb53bc37498f353b4796f2081b92e2011b",
    "scope": scope,
    "pass": all(scope[role]["ownOnly"] and scope[role]["hasTimeIpResult"] for role in ("配置管理员", "运行操作员"))
        and len(scope["系统管理员"]["visibleUsernames"]) > 1
        and "ACCESS_DENIED" in scope["系统管理员"]["eventTypes"]}
OUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(evidence, ensure_ascii=False))
