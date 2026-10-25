"""Fresh stage-3 negative boundary request against a stable simulated display."""
import importlib.util
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("配置管理员")
device = "SIM_F2_DISPLAY"
path = "/devices/" + device + "/capabilities"
before = len(api(path))
payload = {"capabilityCode": "S3_TC018_OUT_OF_BOUNDARY", "capabilityName": "越界验证",
           "capabilityType": "CAP_BAGGAGE_MEASURE",
           "inputParams": [{"name": "contentData", "type": "String", "required": True}],
           "outputParams": [{"name": "displayStatus", "type": "String", "required": True}]}
request = urllib.request.Request(local.BASE + path, method="POST",
    data=json.dumps(payload, ensure_ascii=False).encode(),
    headers={"Authorization": "Bearer " + api.token, "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(request, timeout=10) as response:
        status = response.status
        message = json.loads(response.read()).get("message")
except urllib.error.HTTPError as error:
    status = error.code
    message = json.loads(error.read()).get("message")
after = api(path)
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "deviceCode": device, "deviceType": "SIMULATOR", "simulatedDeviceType": "SMART_DISPLAY",
      "rejectedCapabilityType": payload["capabilityType"], "httpStatus": status,
      "boundaryMessage": message, "beforeCapabilityCount": before,
      "afterCapabilityCount": len(after),
      "rejectedCodeAbsent": not any(x["capabilityCode"] == payload["capabilityCode"] for x in after)}
out = Path(__file__).resolve().parent / "evidence/TC-018-instance-boundary.json"
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(ev, ensure_ascii=False))
