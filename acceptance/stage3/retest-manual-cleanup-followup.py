"""Verify asynchronous cancellation released all six simulator agents."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
operator, admin = local.API("运行操作员"), local.API("配置管理员")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14",
      "task71": {key: operator("/tasks/71").get(key) for key in
                 ("id", "taskCode", "status", "manualTerminateReason")},
      "fixtureMode": json.loads((root / ".local-test/planning-fault.json").read_text(encoding="utf-8"))}
ev["agents"] = [{key: agent.get(key) for key in
                 ("deviceCode", "agentStatus", "onlineStatus", "workStatus", "currentTaskId")}
                for agent in admin("/device-agents?page=1&size=100")["content"]
                if agent["deviceCode"].startswith("SIM_F2_")]
out = stage / "evidence" / ("TC-064-manual-cleanup-followup-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "taskStatus": ev["task71"]["status"],
                  "allSixOnlineIdle": len(ev["agents"]) == 6 and all(
                      a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE"
                      and a["workStatus"] == "IDLE" and a["currentTaskId"] is None
                      for a in ev["agents"])}, ensure_ascii=False))
