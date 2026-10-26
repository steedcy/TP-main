"""SRS_F007.R08: verify the live simulated adapter identity and executed command path."""
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
api = local.API("配置管理员")
code = "SIM_F2_DISPLAY"
device = api("/devices/" + code)
agent = next(a for a in api("/device-agents?page=1&size=100")["content"]
             if a["deviceCode"] == code)
assert device["isSimulator"] is True
assert agent["agentStatus"] == "ENABLED" and agent["onlineStatus"] == "ONLINE"
health = local.request(device["accessEndpoint"] + "/device-api/v1/health?nonce=S3-R08",
                       token=local.secrets()[code])
assert health["deviceCode"] == code and health["protocolVersion"] == "1.0"
assert health["simulatedDeviceType"] == "SMART_DISPLAY"
command_rows = db.query(db.source,
    "SELECT json_build_object('taskId',task_id,'agentCode',agent_code,"
    "'commandType',command_type,'commandId',command_id,"
    "'status',command_status,'response',response_payload::jsonb)::text "
    "FROM tip_stage2_v14.device_commands WHERE task_id=56 "
    f"AND agent_code='{agent['agentId']}' ORDER BY id").splitlines()
commands = [json.loads(row) for row in command_rows]
assert any(row["commandType"] == "EXECUTE_CAPABILITY" and row["status"] == "SUCCEEDED"
           for row in commands)
events = db.query(db.source,
    "SELECT event_type FROM tip_stage2_v14.task_events WHERE task_id=56 ORDER BY id").splitlines()
assert "EXECUTION_FEEDBACK_RECEIVED" in events
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "device": {k: device.get(k) for k in
          ("deviceCode", "deviceTypeCode", "simulatedDeviceType", "isSimulator", "accessEndpoint")},
      "agent": agent, "simulatorHealth": health, "stage3TaskId": 56,
      "taskCommands": commands, "taskEventTypes": events}
out = stage / "evidence" / ("TC-023-simulator-adapter-baseline-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "protocol": health["protocolVersion"],
                  "simulatedType": health["simulatedDeviceType"],
                  "commandStatuses": [r["commandType"] + ":" + r["status"] for r in commands]},
                 ensure_ascii=False))
