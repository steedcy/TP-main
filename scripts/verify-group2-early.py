"""Check the SRS earlier-departure option at API schema and simulated device boundary."""
import importlib.util
import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)
config = env.API("配置管理员")
capabilities = config("/devices/SIM_F2_FLIGHT/capabilities")
flight = next(c for c in capabilities if c["capabilityType"] == "CAP_FLIGHT_UPDATE")
update_type = next(p for p in flight["inputParams"] if p["name"] == "updateType")
assert "EARLY" in update_type["range"].split("/"), "V16 did not update enabled capability schema"
fixture = next(d for d in env.load(env.FIXTURES / "devices.json") if d["deviceCode"] == "SIM_F2_FLIGHT")
agent = next(a for a in config("/device-agents?page=1&size=100")["content"] if a["deviceCode"] == "SIM_F2_FLIGHT")
body = {"commandId": "TEST-EARLY-" + time.strftime("%H%M%S"), "capabilityType": "CAP_FLIGHT_UPDATE",
        "inputParams": {"flightNumber": "R08EARLY", "updateType": "EARLY",
                        "updateContent": "虚构航班R08EARLY提前20分钟", "displayDuration": 60}}
result = env.request(fixture["accessEndpoint"] + "/device-api/v1/agents/" + agent["agentId"] + "/capability-test",
                     "POST", body, token=env.secrets()["SIM_F2_FLIGHT"])
destination = env.EVIDENCE / ("20261024-group2-early-" + time.strftime("%H%M%S") + ".json")
env.save(destination, {"recordedAt": env.stamp(), "case": "GROUP2_EARLY_SCHEMA_AND_DEVICE",
                       "deviceCode": "SIM_F2_FLIGHT", "schemaRange": update_type["range"], "testResult": result})
assert result["result"] == "SUCCESS" and result["outputParams"]["publishStatus"] == "SUCCESS"
print(json.dumps({"schemaRange": update_type["range"], "result": result["result"], "evidence": str(destination)}, ensure_ascii=False))
