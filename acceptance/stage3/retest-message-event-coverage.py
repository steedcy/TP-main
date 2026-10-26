"""SRS_F007.R07: check event persistence for successful internal agent queries."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

local = module("local", root / "scripts/local-test-environment.py")
db = module("db", root / "acceptance/stage2/db-isolation.py")
api = local.API("系统管理员")
agent = next(a for a in api("/device-agents?page=1&size=100")["content"]
             if a["deviceCode"] == "SIM_F2_DISPLAY")
assert agent["onlineStatus"] == "ONLINE" and agent["workStatus"] == "IDLE"
assert agent["currentTaskId"] is None
url = "http://127.0.0.1:8080/internal/v1/device-agent/messages"

def counts():
    agent_code = agent["agentId"]
    return {
        "deviceEvents": int(db.query(db.source,
            "SELECT count(*) FROM tip_stage2_v14.device_events e "
            "JOIN tip_stage2_v14.device_agents a ON a.id=e.device_agent_id "
            f"WHERE a.agent_code='{agent_code}'")),
        "taskEvents": int(db.query(db.source, "SELECT count(*) FROM tip_stage2_v14.task_events")),
        "agentCommands": int(db.query(db.source,
            "SELECT count(*) FROM tip_stage2_v14.device_commands "
            f"WHERE agent_code='{agent_code}'")),
    }

ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "agentId": agent["agentId"],
      "note": "message-type literal command IDs are accepted by current validation defect DEF-S3-050",
      "before": counts(), "messages": []}
for message_type in ("CAPABILITY_QUERY", "STATUS_QUERY"):
    body = {"commandId": message_type, "messageType": message_type,
            "agentId": agent["agentId"], "payload": {}}
    response = local.request(url, "POST", body, api.token)
    data = response.get("data") or {}
    ev["messages"].append({"messageType": message_type, "commandId": message_type,
                           "apiCode": response.get("code"), "returnedCommandId": data.get("commandId"),
                           "returnedCapabilities": len(data.get("capabilities", [])),
                           "returnedAgentId": data.get("agentId")})
ev["after"] = counts()
ev["agentAfter"] = api("/device-agents/" + agent["agentId"])
assert all(row["apiCode"] == 200 and row["commandId"] == row["returnedCommandId"]
           for row in ev["messages"])
out = stage / "evidence" / ("TC-023-message-event-coverage-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "messages": [m["messageType"] for m in ev["messages"]],
                  "before": ev["before"], "after": ev["after"]}, ensure_ascii=False))
