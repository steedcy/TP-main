"""SRS_F027.R08: actual trace read role matrix and denial audit."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
system = local.API("系统管理员")
config = local.API("配置管理员")
operator = local.API("运行操作员")
username = local.account("配置管理员")[0]
path = "/tasks/19/events"
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "taskId": 19,
      "authorized": {"systemAdminEventCount": len(system(path)),
                     "operatorEventCount": len(operator(path))}}
try:
    config(path)
    ev["configAdmin"] = {"accepted": True}
except RuntimeError as error:
    ev["configAdmin"] = {"accepted": False, "error": str(error)}
logs = system("/operation-logs?username=" + quote(username) +
              "&operationType=ACCESS_DENIED&page=1&size=100")["content"]
ev["denialLogs"] = [{key: row.get(key) for key in (
    "id", "username", "operationType", "operationTarget", "operationResult",
    "sourceIp", "createdAt")} for row in logs
    if row.get("operationTarget") == "/api/v1" + path]
out = stage / "evidence" / ("TC-084-trace-permissions-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "authorized": ev["authorized"],
                  "configAdmin": ev["configAdmin"],
                  "denialLogCount": len(ev["denialLogs"])}, ensure_ascii=False))
