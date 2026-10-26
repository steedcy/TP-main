"""TC-023.S1: exercise six unified message types with real unique command IDs."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("系统管理员")
agent = next(a for a in api("/device-agents?page=1&size=100")["content"]
             if a["deviceCode"] == "SIM_F2_DISPLAY")
assert agent["agentStatus"] == "ENABLED" and agent["onlineStatus"] == "ONLINE"
assert agent["workStatus"] == "IDLE" and agent["currentTaskId"] is None
url = "http://127.0.0.1:8080/internal/v1/device-agent/messages"
types = ("CAPABILITY_QUERY", "STATUS_QUERY", "TASK_ACCEPT", "TASK_REJECT",
         "EXECUTION_FEEDBACK", "TASK_CANCEL")

def send(message_type, command_id):
    body = {"commandId": command_id, "messageType": message_type,
            "agentId": agent["agentId"], "payload": {}}
    try:
        response = local.request(url, "POST", body, api.token)
        return {"messageType": message_type, "commandId": command_id,
                "accepted": True, "response": response}
    except Exception as error:
        return {"messageType": message_type, "commandId": command_id,
                "accepted": False, "error": str(error)}

stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "role": "系统管理员",
      "agentBefore": agent, "uniqueCommandIdProbes": [], "literalIdControls": []}
for index, message_type in enumerate(types, 1):
    ev["uniqueCommandIdProbes"].append(send(message_type,
        f"CMD-S3-023-{stamp}-{index:02d}"))
for message_type in types[:2]:
    ev["literalIdControls"].append(send(message_type, message_type))
ev["agentAfter"] = api("/device-agents/" + agent["agentId"])
assert ev["agentAfter"]["workStatus"] == "IDLE"
assert ev["agentAfter"]["currentTaskId"] is None
out = stage / "evidence" / ("TC-023-internal-messages-" + stamp + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out),
                  "uniqueIdAccepted": [r["accepted"] for r in ev["uniqueCommandIdProbes"]],
                  "literalQueryAccepted": [r["accepted"] for r in ev["literalIdControls"]]},
                 ensure_ascii=False))
