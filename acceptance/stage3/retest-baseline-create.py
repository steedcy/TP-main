"""TC-025/026 isolated baseline creation, sequential validation and cleanup."""
import copy
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
base = "/baseline-templates"
name = "S3_TC025_ORDERED"
invalid_name = "S3_TC026_BAD_OUTPUT"
out = Path(__file__).resolve().parent / "evidence/TC-025-026-baseline-create.json"
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "templateName": name, "invalid": {}, "cleanup": {}}


def raw(payload):
    request = urllib.request.Request(local.BASE + base, method="POST",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Authorization": "Bearer " + api.token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


before = api(base)
assert name not in {x["templateName"] for x in before}
assert invalid_name not in {x["templateName"] for x in before}
fixture = json.loads((root / "scripts/test-fixtures/baselines.json").read_text(encoding="utf-8"))[0]
steps = [copy.deepcopy(fixture["steps"][i]) for i in (3, 0, 1, 2)]
for mapping in steps[3]["paramMapping"]:
    if mapping["source"] == "STEP2_OUTPUT.baggageInfo":
        mapping["source"] = "STEP3_OUTPUT.baggageInfo"
payload = {"templateName": name, "templateIntent": fixture["taskFamily"],
           "inputParams": fixture["inputParams"], "steps": steps}
created_ids = []
try:
    created = api(base, "POST", payload)
    created_ids.append(created["id"])
    ev["created"] = {key: created.get(key) for key in
                     ("id", "templateName", "templateIntent", "templateVersion", "templateStatus", "isPreset")}
    ev["savedStepOrder"] = [x["capabilityType"] for x in created["steps"]]
    ev["savedStepSeq"] = [x["stepSeq"] for x in created["steps"]]
    ev["savedStepTimeouts"] = [x["stepTimeout"] for x in created["steps"]]
    ev["savedRequiredInputCount"] = sum(x["required"] for x in created["inputParams"])
    ev["detailMatchesList"] = api(base + "/" + str(created["id"]))["templateVersion"] == next(
        x["templateVersion"] for x in api(base) if x["id"] == created["id"])

    variants = {
        "duplicateName": payload,
        "sixSteps": dict(payload, templateName="S3_TC026_SIX", steps=steps + [steps[0], steps[0]]),
        "capabilityGap": dict(payload, templateName="S3_TC026_GAP",
                              steps=[dict(steps[0], capabilityType="CAP_SIM_STATUS")] + steps[1:]),
        "undefinedInput": dict(payload, templateName="S3_TC026_UNDEFINED_INPUT",
                               steps=[dict(steps[0], paramMapping=[{"target": "contentData", "source": "TEMPLATE_INPUT.noSuchInput"}])] + steps[1:]),
        "requiredUnmapped": dict(payload, templateName="S3_TC026_UNMAPPED",
                                 inputParams=fixture["inputParams"] + [{"name": "neverMapped", "type": "String", "required": True}]),
        "emptyCompletion": dict(payload, templateName="S3_TC026_NO_COMPLETION",
                                steps=[dict(steps[0], completionCondition="")] + steps[1:]),
        "timeoutBelowTen": dict(payload, templateName="S3_TC026_SHORT_TIMEOUT",
                                steps=[dict(steps[0], stepTimeout=9)] + steps[1:]),
        "timeoutAboveSixHundred": dict(payload, templateName="S3_TC026_LONG_TIMEOUT",
                                      steps=[dict(steps[0], stepTimeout=601)] + steps[1:]),
        "undefinedPriorOutput": dict(payload, templateName=invalid_name,
                                      steps=steps[:3] + [dict(steps[3], paramMapping=[
                                          dict(m, source="STEP3_OUTPUT.noSuchOutput") if m["target"] == "baggageInfo" else m
                                          for m in steps[3]["paramMapping"]])]),
    }
    for label, variant in variants.items():
        status, response = raw(variant)
        ev["invalid"][label] = {"httpStatus": status, "message": response.get("message")}
        if status == 200:
            created_ids.append(response["data"]["id"])
            ev["invalid"][label]["createdStatus"] = response["data"]["templateStatus"]
    ev["newNamesAfterInvalid"] = sorted(x["templateName"] for x in api(base)
                                        if x["templateName"].startswith("S3_TC02"))
finally:
    for ident in reversed(created_ids):
        try:
            api(base + "/" + str(ident), "DELETE")
        except Exception as error:
            ev["cleanup"][str(ident)] = str(error)
    ev["cleanup"]["namesAbsent"] = all(x["templateName"] not in (name, invalid_name) for x in api(base))
    ev["cleanup"]["countRestored"] = len(api(base)) == len(before)
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(ev, ensure_ascii=False))
