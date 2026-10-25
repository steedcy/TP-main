"""TC-025 valid name, timeout and five-step boundaries; isolated cleanup."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("配置管理员")
before = len(api("/baseline-templates"))
names = ["Q", "S3_TC025_" + "X" * 55]
assert len(names[1]) == 64
assert not ({x["templateName"] for x in api("/baseline-templates")} & set(names))
inputs = [
    {"name": "contentType", "type": "String", "required": True, "defaultValue": "TEXT"},
    {"name": "contentData", "type": "String", "required": True, "defaultValue": "测试"},
    {"name": "displayDuration", "type": "Integer", "required": True, "defaultValue": "60"},
]
step = {"capabilityType": "CAP_INFO_DISPLAY", "stepTimeout": 10,
        "completionCondition": "displayStatus=SUCCESS", "paramMapping": [
            {"target": x["name"], "source": "TEMPLATE_INPUT." + x["name"]} for x in inputs]}
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "beforeTemplateCount": before, "cases": [], "cleanupErrors": []}
created = []
try:
    for name, timeout, count in [(names[0], 10, 1), (names[1], 600, 5)]:
        payload = {"templateName": name, "templateIntent": "OVERSIZE_BAGGAGE_HANDLING",
                   "inputParams": inputs, "steps": [dict(step, stepTimeout=timeout) for _ in range(count)]}
        result = api("/baseline-templates", "POST", payload)
        created.append(result["id"])
        ev["cases"].append({"nameLength": len(name), "stepCount": len(result["steps"]),
                            "stepSeq": [x["stepSeq"] for x in result["steps"]],
                            "timeouts": [x["stepTimeout"] for x in result["steps"]],
                            "status": result["templateStatus"], "version": result["templateVersion"]})
    logs = api("/operation-logs?page=1&size=100")["content"]
    ev["createAuditCount"] = sum(1 for x in logs if x["operationType"] == "BASELINE_TEMPLATE_CREATE"
                                 and x.get("operationTarget") in names)
finally:
    for ident in reversed(created):
        try:
            api("/baseline-templates/" + str(ident), "DELETE")
        except Exception as error:
            ev["cleanupErrors"].append(str(error))
    ev["afterTemplateCount"] = len(api("/baseline-templates"))
    out = Path(__file__).resolve().parent / "evidence/TC-025-baseline-boundaries.json"
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(ev, ensure_ascii=False))
