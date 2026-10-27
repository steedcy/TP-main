"""Read-only final state after TC-043.S2 risk-rule toggle attempts."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
operator, config = local.API("运行操作员"), local.API("配置管理员")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "tasks": {}}
for id in (72, 73, 74, 75, 76, 77):
    task = operator(f"/tasks/{id}")
    ev["tasks"][str(id)] = {key: task.get(key) for key in
                            ("id", "taskCode", "status", "currentPlanVersionId",
                             "manualTerminateReason", "updatedAt")}
ev["rule"] = next(r for r in config("/risk-rules")
                  if r["ruleCode"] == "RULE_RESOURCE_CRITICAL")
ev["fixtureMode"] = json.loads((root / ".local-test/planning-fault.json").read_text(encoding="utf-8"))
ev["agents"] = [{key: a.get(key) for key in
                 ("deviceCode", "agentStatus", "onlineStatus", "workStatus", "currentTaskId")}
                for a in config("/device-agents?page=1&size=100")["content"]
                if a["deviceCode"].startswith("SIM_F2_")]
ev["audit"] = [r for r in config(
    "/operation-logs?operationType=RISK_RULE_CHANGE&page=1&size=100")["content"]
    if r.get("operationTarget") == "RULE_RESOURCE_CRITICAL"]
out = stage / "evidence" / ("TC-043-risk-rule-subsequent-followup-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out),
                  "taskStatuses": {id: row["status"] for id, row in ev["tasks"].items()},
                  "ruleEnabled": ev["rule"]["enabled"], "ruleVersion": ev["rule"]["ruleVersion"],
                  "auditCount": len(ev["audit"]),
                  "allSixOnlineIdle": len(ev["agents"]) == 6 and all(
                      a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE"
                      and a["workStatus"] == "IDLE" and a["currentTaskId"] is None
                      for a in ev["agents"])}, ensure_ascii=False))
