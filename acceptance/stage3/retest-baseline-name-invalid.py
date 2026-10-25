"""TC-025 invalid baseline name endpoints with no fixture mutation."""
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
inputs = [{"name": "contentData", "type": "String", "required": True, "defaultValue": "测试"}]
step = {"capabilityType": "CAP_INFO_DISPLAY", "stepTimeout": 60,
        "completionCondition": "displayStatus=SUCCESS",
        "paramMapping": [{"target": "contentData", "source": "TEMPLATE_INPUT.contentData"}]}
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "beforeTemplateCount": before, "cases": {}}
for label, name in [("empty", ""), ("over64", "X" * 65)]:
    request = urllib.request.Request(local.BASE + "/baseline-templates", method="POST",
        data=json.dumps({"templateName": name, "templateIntent": "OVERSIZE_BAGGAGE_HANDLING",
                         "inputParams": inputs, "steps": [step]}, ensure_ascii=False).encode(),
        headers={"Authorization": "Bearer " + api.token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status, body = response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        status, body = error.code, json.loads(error.read())
    ev["cases"][label] = {"nameLength": len(name), "httpStatus": status, "message": body.get("message")}
ev["afterTemplateCount"] = len(api("/baseline-templates"))
out = Path(__file__).resolve().parent / "evidence/TC-025-baseline-invalid-names.json"
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(ev, ensure_ascii=False))
