"""F028.R07: enumerate each role's operation-log visibility and filter bypass."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)

def sample(role, query):
    response = local.API(role)(query)
    return {"totalElements": response["totalElements"],
            "returned": len(response["content"]),
            "usernames": sorted({row["username"] for row in response["content"]}),
            "minId": min((row["id"] for row in response["content"]), default=None),
            "maxId": max((row["id"] for row in response["content"]), default=None)}

roles = ("系统管理员", "配置管理员", "运行操作员")
admin, config, operator = (local.account(role)[0] for role in roles)
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "usernameByRole": dict(zip(roles, (admin, config, operator))),
      "unfiltered": {role: sample(role, "/operation-logs?page=1&size=1000") for role in roles},
      "crossUserFilter": {
          "配置管理员": sample("配置管理员", "/operation-logs?username=" + admin + "&page=1&size=1000"),
          "运行操作员": sample("运行操作员", "/operation-logs?username=" + admin + "&page=1&size=1000")}}
out = stage / "evidence" / ("SRS_F028-audit-roles-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "unfiltered": ev["unfiltered"],
                  "crossUserFilter": ev["crossUserFilter"]}, ensure_ascii=False))
