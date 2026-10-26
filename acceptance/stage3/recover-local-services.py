"""Rebind existing stage-3 simulators after a host restart without reconfiguring data."""
import importlib.util
import json
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("配置管理员")
agents = [a for a in api("/device-agents?page=1&size=100")["content"]
          if a["deviceCode"].startswith("SIM_F2_")]
assert len(agents) == 6
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "before": agents, "bindings": [], "after": []}
values = local.secrets()
for agent in agents:
    code = agent["deviceCode"]
    device = api("/devices/" + code)
    base = device["accessEndpoint"] + "/device-api/v1"
    health = local.request(base + "/health?nonce=stage3-recovery", token=values[code], timeout=5)
    assert health["deviceCode"] == code
    binding = local.request(base + "/agents/" + agent["agentId"] + "/binding", "POST", {
        "deviceCode": code, "agentCode": agent["agentId"],
        "reportUrl": "http://127.0.0.1:8080/device-api/v1/agents/" + agent["agentId"] + "/report",
        "heartbeatIntervalSeconds": 5, "heartbeatTimeoutSeconds": 30}, values[code])
    online = local.request(base + "/control/online?value=true", "POST", token=values[code])
    heartbeat = local.request(base + "/control/heartbeat?value=true", "POST", token=values[code])
    ev["bindings"].append({"deviceCode": code, "health": health, "binding": binding,
                           "online": online, "heartbeat": heartbeat})
deadline = time.monotonic() + 25
while time.monotonic() < deadline:
    ev["after"] = [a for a in api("/device-agents?page=1&size=100")["content"]
                   if a["deviceCode"].startswith("SIM_F2_")]
    if len(ev["after"]) == 6 and all(a["agentStatus"] == "ENABLED" and
                                      a["onlineStatus"] == "ONLINE" and
                                      a["workStatus"] == "IDLE" for a in ev["after"]):
        break
    time.sleep(1)
ev["allSixOnlineIdle"] = len(ev["after"]) == 6 and all(
    a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE" and
    a["workStatus"] == "IDLE" for a in ev["after"])
(Path(__file__).parent / "evidence/stage3-services-recovered-20261026.json").write_text(
    json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"allSixOnlineIdle": ev["allSixOnlineIdle"],
                  "codes": [a["deviceCode"] for a in ev["after"]]}, ensure_ascii=False))
assert ev["allSixOnlineIdle"]
