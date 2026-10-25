"""TC-012.S2: device disable/enable propagation to its idle agent, with restoration."""
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
code = "SIM_F2_DISPLAY"


def agent():
    return next(x for x in api("/device-agents?page=1&size=100")["content"] if x["deviceCode"] == code)


before = agent()
assert before["agentStatus"] == "ENABLED" and before["onlineStatus"] == "ONLINE"
assert before["currentTaskId"] is None
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "deviceCode": code,
      "beforeAgentStatus": before["agentStatus"], "beforeOnlineStatus": before["onlineStatus"]}
try:
    api("/devices/" + code + "/status", "POST", {"status": "INACTIVE"})
    ev["afterDisableDeviceStatus"] = api("/devices/" + code)["deviceStatus"]
    disabled = agent()
    ev["afterDisableAgentStatus"] = disabled["agentStatus"]
    ev["afterDisableOnlineStatus"] = disabled["onlineStatus"]
    api("/devices/" + code + "/status", "POST", {"status": "ACTIVE"})
    ev["afterEnableDeviceStatus"] = api("/devices/" + code)["deviceStatus"]
    enabled = agent()
    ev["afterEnableAgentStatus"] = enabled["agentStatus"]
    ev["afterEnableOnlineStatus"] = enabled["onlineStatus"]
finally:
    if api("/devices/" + code)["deviceStatus"] != "ACTIVE":
        api("/devices/" + code + "/status", "POST", {"status": "ACTIVE"})
    if agent()["agentStatus"] != "ENABLED":
        api("/device-agents", "POST", {"deviceCode": code})
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and agent()["onlineStatus"] != "ONLINE":
        time.sleep(1)
    final = agent()
    ev["restoredAgentStatus"] = final["agentStatus"]
    ev["restoredOnlineStatus"] = final["onlineStatus"]
    ev["restoredDeviceStatus"] = api("/devices/" + code)["deviceStatus"]

out = Path(__file__).resolve().parent / "evidence/TC-012-status-sync.json"
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(ev, ensure_ascii=False))
