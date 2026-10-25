"""TC-026.S2: reject motion controls in sequential baseline step fields."""
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
before = len(api("/baseline-templates"))
inputs = [
    {"name": "contentType", "type": "String", "required": True, "defaultValue": "TEXT"},
    {"name": "contentData", "type": "String", "required": True, "defaultValue": "阶段三测试"},
    {"name": "displayDuration", "type": "Integer", "required": True, "defaultValue": "60"},
]
step = {"capabilityType": "CAP_INFO_DISPLAY", "stepTimeout": 60,
        "completionCondition": "displayStatus=SUCCESS", "paramMapping": [
            {"target": x["name"], "source": "TEMPLATE_INPUT." + x["name"]} for x in inputs]}
motion_fields = ["speed", "acceleration", "attitude", "pathPoints", "obstacleAvoidance",
                 "emergencyStop", "speedLimit", "lostConnectionParking"]
variants = {field + "Param": dict(step, paramMapping=step["paramMapping"] +
            [{"target": field, "source": "TEMPLATE_INPUT.contentData"}]) for field in motion_fields}
variants["emergencyStopCondition"] = dict(step, completionCondition="emergencyStop=true")
variants["speedLimitCondition"] = dict(step, completionCondition="speedLimit=1")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "beforeTemplateCount": before, "variants": {}, "cleanupErrors": []}
for label, variant in variants.items():
    request = urllib.request.Request(local.BASE + "/baseline-templates", method="POST",
        data=json.dumps({"templateName": "S3_TC026_" + label, "templateIntent": "OVERSIZE_BAGGAGE_HANDLING",
                         "inputParams": inputs, "steps": [variant]}, ensure_ascii=False).encode(),
        headers={"Authorization": "Bearer " + api.token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = json.loads(response.read())
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
        body = json.loads(error.read())
    ev["variants"][label] = {"httpStatus": status, "message": body.get("message")}
    if status == 200:
        try:
            api("/baseline-templates/" + str(body["data"]["id"]), "DELETE")
        except Exception as error:
            ev["cleanupErrors"].append(label + ": " + str(error))
ev["afterTemplateCount"] = len(api("/baseline-templates"))
out = Path(__file__).resolve().parent / "evidence/TC-026-baseline-motion-safety-matrix.json"
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(ev, ensure_ascii=False))
