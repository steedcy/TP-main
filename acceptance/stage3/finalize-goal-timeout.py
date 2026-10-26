"""Record enabled baseline, absent commands, and cleanup for TC-034 timeout."""
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
operator = local.API("运行操作员")
config = local.API("配置管理员")
task_id = 47
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "schema": "tip_stage2_v14",
      "runtimeInput": "V1.5", "taskBeforeCleanup": operator(f"/tasks/{task_id}"),
      "baselines": operator("/baseline-templates"),
      "deviceCommandCount": int(db.query(db.source,
          f"SELECT count(*) FROM tip_stage2_v14.device_commands WHERE task_id={task_id}")),
      "assignmentCount": int(db.query(db.source,
          f"SELECT count(*) FROM tip_stage2_v14.task_step_assignments WHERE task_id={task_id}")),
      "cancel": None, "taskAfterCleanup": None, "agentsAfter": None}
assert ev["taskBeforeCleanup"]["status"] == "PLANNING"
assert any(t["templateIntent"] == "OVERSIZE_BAGGAGE_HANDLING" and
           t["templateStatus"] == "ENABLED" for t in ev["baselines"])
assert ev["deviceCommandCount"] == 0 and ev["assignmentCount"] == 0
ev["cancel"] = operator(f"/tasks/{task_id}/cancel", "POST",
                        {"reason": "阶段3目标理解超时实测清场"})
ev["taskAfterCleanup"] = operator(f"/tasks/{task_id}")
ev["agentsAfter"] = [a for a in config("/device-agents?page=1&size=100")["content"]
                     if a["deviceCode"].startswith("SIM_F2_")]
out = Path(__file__).parent / "evidence" / (
    "TC-034-goal-timeout-cleanup-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"before": ev["taskBeforeCleanup"]["status"],
                  "after": ev["taskAfterCleanup"]["status"],
                  "enabledBaseline": True, "commands": ev["deviceCommandCount"],
                  "allSixOnlineIdle": len(ev["agentsAfter"]) == 6 and all(
                      a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE" and
                      a["workStatus"] == "IDLE" for a in ev["agentsAfter"]),
                  "evidence": str(out)}, ensure_ascii=False))
