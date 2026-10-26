"""Record the corrected isolated runtime after the host stopped local services."""
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
db_spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(db_spec)
db_spec.loader.exec_module(db)
api = local.API("配置管理员")
operator = local.API("运行操作员")
agents = [a for a in api("/device-agents?page=1&size=100")["content"]
          if a["deviceCode"].startswith("SIM_F2_")]
jar = root / ".local-test/runtime/backend.jar"
target = root / "backend/target/airport-ai-app-1.0.0.jar"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
log = (root / ".local-test/backend.log").read_text(encoding="utf-8", errors="replace")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(),
      "incident": "Host restart stopped 8080, 5173, and 8091-8096. Initial generic backend command used public schema; no formal case was executed. Backend was stopped and relaunched with the isolated schema, then six simulators were restarted and rebound to the isolated agent identities.",
      "initialPublicStartupSeen": 'Current version of schema "public": 16' in log,
      "correctedIsolatedStartupSeen": 'Current version of schema "tip_stage2_v14": 16' in log,
      "runtimeJarSha256": sha(jar), "targetJarSha256": sha(target),
      "isolatedTaskCount": int(db.query(db.source, "SELECT count(*) FROM tip_stage2_v14.tasks")),
      "task37Status": operator("/tasks/37")["status"],
      "agentStates": [{"deviceCode": a["deviceCode"], "agentId": a["agentId"],
                       "agentStatus": a["agentStatus"], "onlineStatus": a["onlineStatus"],
                       "workStatus": a["workStatus"]} for a in agents],
      "templateStates": [{"name": t["templateName"], "version": t["templateVersion"],
                          "status": t["templateStatus"]} for t in api("/baseline-templates")],
      "boundToIsolatedAgents": json.loads((Path(__file__).parent /
          "evidence/stage3-services-recovered-20261026.json").read_text(encoding="utf-8"))["allSixOnlineIdle"]}
ev["ready"] = ev["correctedIsolatedStartupSeen"] and ev["runtimeJarSha256"] == ev["targetJarSha256"] \
    and ev["task37Status"] == "COMPLETED" and ev["isolatedTaskCount"] == 37 \
    and len(agents) == 6 and all(a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE"
                                 and a["workStatus"] == "IDLE" for a in agents) \
    and ev["boundToIsolatedAgents"]
(Path(__file__).parent / "evidence/stage3-service-restart-audit.json").write_text(
    json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"ready": ev["ready"], "schema": "tip_stage2_v14",
                  "taskCount": ev["isolatedTaskCount"], "agents": len(agents)}, ensure_ascii=False))
assert ev["ready"]
