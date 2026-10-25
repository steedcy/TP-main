"""TC-069: deletion guard, reversible preset edit, and definition validation."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("配置管理员")
presets = [d for d in api("/task-definitions") if d["isPreset"]]
assert len(presets) == 3 and all(d["definitionStatus"] == "ENABLED" for d in presets)
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "presetsBefore": presets, "deletionAttempts": [], "edit": {}, "validation": {}, "restore": {}}
out = Path(__file__).parent / "evidence/TC-069-preset-definitions.json"

for preset in presets:
    try:
        response = local.request(local.BASE + f"/task-definitions/{preset['id']}", "DELETE", token=api.token)
        ev["deletionAttempts"].append({"id": preset["id"], "http": 200, "response": response})
    except RuntimeError as error:
        ev["deletionAttempts"].append({"id": preset["id"], "error": str(error)})
ev["presetsAfterDeleteAttempts"] = [api(f"/task-definitions/{p['id']}") for p in presets]

target = presets[0]
original = api(f"/task-definitions/{target['id']}")
def payload(detail):
    return {key: detail[key] for key in ("goalTemplate", "sceneParams", "availableCapabilityTypes",
                                      "constraintDescription", "completionCondition")}
modified = payload(original)
modified["sceneParams"] = [*modified["sceneParams"], {
    "name": "stage3OptionalProbe", "type": "String", "required": False,
    "defaultValue": "", "range": "阶段3可逆编辑验证"}]
modified["constraintDescription"] = original["constraintDescription"] + "；阶段3可逆编辑验证"
try:
    ev["edit"]["request"] = modified
    ev["edit"]["response"] = api(f"/task-definitions/{target['id']}", "PUT", modified)
    ev["edit"]["detailDuringEdit"] = api(f"/task-definitions/{target['id']}")
finally:
    api(f"/task-definitions/{target['id']}", "PUT", payload(original))
    restored = api(f"/task-definitions/{target['id']}")
    ev["restore"]["detail"] = restored
    ev["restore"]["payloadMatchesOriginal"] = payload(restored) == payload(original)

name = "S3_TC069_VALIDATION_ONLY"
assert not any(d["taskName"] == name for d in api("/task-definitions"))
valid = {"taskName": name, "goalTemplate": "虚构航显测试目标",
         "sceneParams": [{"name": "sampleLocation", "type": "String", "required": True, "range": "虚构地点"}],
         "availableCapabilityTypes": ["CAP_INFO_DISPLAY"],
         "constraintDescription": "仅F2测试区", "completionCondition": "航显成功"}
for label, change in [
    ("duplicateName", {"taskName": target["taskName"]}),
    ("emptyParams", {"sceneParams": []}),
    ("emptyCapabilities", {"availableCapabilityTypes": []}),
    ("unknownCapability", {"availableCapabilityTypes": ["CAP_INVALID_STAGE3"]}),
    ("blankConstraint", {"constraintDescription": ""}),
]:
    request = {**valid, **change}
    try:
        response = local.request(local.BASE + "/task-definitions", "POST", request, api.token)
        ev["validation"][label] = {"request": request, "http": 200, "response": response}
        created = response.get("data")
        if created:
            api(f"/task-definitions/{created['id']}", "DELETE")
            ev["validation"][label]["deletedAfterProbe"] = created["id"]
    except RuntimeError as error:
        ev["validation"][label] = {"request": request, "error": str(error)}
ev["validation"]["unexpectedSelectable"] = [d["taskName"] for d in api("/task-definitions")
                                             if d["taskName"] == name]
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"presetDeleteRejected": ["error" in x for x in ev["deletionAttempts"]],
                  "editRestored": ev["restore"].get("payloadMatchesOriginal"),
                  "validationRejected": {k: "error" in v for k, v in ev["validation"].items()
                                         if isinstance(v, dict)}}, ensure_ascii=False))
