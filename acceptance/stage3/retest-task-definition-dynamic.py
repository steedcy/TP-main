"""Stage 3 TC-068/AC-001: isolate an extension definition and retain raw API results."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("配置管理员")
name = "S3_TC068_DYNAMIC_DEFINITION"
out = Path(__file__).parent / "evidence/TC-068-dynamic-definition-api.json"
assert not any(item["taskName"] == name for item in api("/task-definitions")), "test definition already exists"

valid = {
    "taskName": name,
    "goalTemplate": "请在虚构的F2测试区域显示协助提示",
    "sceneParams": [{"name": "sampleLocation", "type": "String", "required": True,
                     "defaultValue": "", "range": "虚构测试地点，1到40字"}],
    "availableCapabilityTypes": ["CAP_INFO_DISPLAY"],
    "constraintDescription": "仅使用F2测试区的智慧航显",
    "completionCondition": "航显返回显示成功",
}
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "definitionName": name, "beforeCount": len(api("/task-definitions")), "requests": {},
      "observations": {}, "cleanup": {}}

def attempt(label, payload):
    try:
        response = local.request(local.BASE + "/task-definitions", "POST", payload, api.token)
        ev["requests"][label] = {"request": payload, "http": 200, "response": response}
        return response.get("data")
    except RuntimeError as error:
        ev["requests"][label] = {"request": payload, "error": str(error)}
        return None

for label, change in [
    ("blankName", {"taskName": ""}),
    ("longName", {"taskName": "N" * 65}),
    ("longGoal", {"goalTemplate": "测" * 501}),
    ("emptyParams", {"sceneParams": []}),
    ("missingParamName", {"sceneParams": [{"name": "", "type": "String", "required": True}]}),
    ("noCapabilities", {"availableCapabilityTypes": []}),
    ("unknownCapability", {"availableCapabilityTypes": ["CAP_UNKNOWN"]}),
    ("blankCompletion", {"completionCondition": ""}),
]:
    attempt(label, {**valid, **change})

created = attempt("valid", valid)
assert created and created["taskName"] == name
ev["observations"]["created"] = created
ev["observations"]["detailAfterCreate"] = api(f"/task-definitions/{created['id']}")
attempt("duplicateName", valid)
updated = api(f"/task-definitions/{created['id']}", "PUT", {
    "goalTemplate": valid["goalTemplate"] + "，测试更新版",
    "sceneParams": valid["sceneParams"],
    "availableCapabilityTypes": valid["availableCapabilityTypes"],
    "constraintDescription": valid["constraintDescription"],
    "completionCondition": valid["completionCondition"],
})
ev["observations"]["updated"] = updated
ev["observations"]["enabledListContains"] = any(
    d["id"] == created["id"] and d["definitionStatus"] == "ENABLED"
    for d in api("/task-definitions"))
ev["observations"]["id"] = created["id"]
ev["observations"]["definitionCode"] = created["definitionCode"]
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"definitionId": created["id"], "definitionCode": created["definitionCode"],
                  "invalidCases": {k: ("error" in v) for k, v in ev["requests"].items() if k != "valid"},
                  "updated": updated["goalTemplate"]}, ensure_ascii=False))
