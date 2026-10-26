"""TC-024.S2: test eight forbidden instruction keys at the signed simulator adapter."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("配置管理员")
code = "SIM_F2_DISPLAY"
agent = next(a for a in api("/device-agents?page=1&size=100")["content"]
             if a["deviceCode"] == code)
assert agent["agentStatus"] == "ENABLED" and agent["onlineStatus"] == "ONLINE"
assert agent["workStatus"] == "IDLE" and agent["currentTaskId"] is None
device = api("/devices/" + code)
secret = local.secrets()[code]
url = device["accessEndpoint"] + "/device-api/v1/agents/" + agent["agentId"] + "/capability-test"
required = {"contentType": "TEXT", "contentData": "阶段三安全字段测试", "displayDuration": 10}
fields = ("speed", "acceleration", "attitude", "pathPoints",
          "obstacleAvoidance", "emergencyStop", "speedLimit", "lostConnectionParking")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "scope": "signed simulator capability-test adapter, not task dispatch",
      "deviceCode": code, "agentBefore": agent, "cases": []}

def call(command_id, extra):
    params = dict(required)
    params.update(extra)
    body = {"commandId": command_id, "capabilityType": "CAP_INFO_DISPLAY",
            "inputParams": params}
    response = local.request(url, "POST", body, token=secret)
    return {"commandId": command_id, "addedFields": extra, "response": response}

ev["baseline"] = call("S3-TC024-NORMAL", {})
assert ev["baseline"]["response"]["result"] == "SUCCESS"
for index, field in enumerate(fields, 1):
    ev["cases"].append(call(f"S3-TC024-{index:02d}", {field: "TEST_CONTROL_VALUE"}))
ev["agentAfter"] = api("/device-agents/" + agent["agentId"])
assert ev["agentAfter"]["workStatus"] == "IDLE"
assert ev["agentAfter"]["currentTaskId"] is None
out = stage / "evidence" / ("TC-024-motion-adapter-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "baseline": ev["baseline"]["response"]["result"],
                  "results": {next(iter(row["addedFields"])): row["response"]["result"]
                              for row in ev["cases"]}}, ensure_ascii=False))
