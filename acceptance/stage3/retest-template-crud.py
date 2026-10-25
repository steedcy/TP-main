"""TC-018/019 isolated capability-template validation, versioning, and cleanup."""
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
db_spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(db_spec)
db_spec.loader.exec_module(db)
api = local.API("配置管理员")
base = "/device-types/SMART_DISPLAY/capability-templates"
code = "S3_TC018_TEMPLATE"
bad_code = "S3_TC018_INCOMPLETE"


def status(payload):
    request = urllib.request.Request(local.BASE + base,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + api.token})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read()).get("message")
    except urllib.error.HTTPError as error:
        try:
            body = json.loads(error.read())
        except Exception:
            body = {}
        return error.code, body.get("message")


def names():
    return {row["templateCode"] for row in api(base)}


def get_status(path):
    request = urllib.request.Request(local.BASE + path,
        headers={"Authorization": "Bearer " + api.token})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def input_param(name, required=True, default=None):
    return {"name": name, "type": "String", "required": required,
            "defaultValue": default, "range": "TEXT" if name == "contentType" else ""}


before_names = names()
assert code not in before_names and bad_code not in before_names
payload = {"templateCode": code, "templateName": "阶段三临时信息展示模板",
           "capabilityType": "CAP_INFO_DISPLAY",
           "inputParams": [input_param("contentType", default="TEXT"), input_param("contentData")],
           "outputParams": [{"name": "displayStatus", "type": "String", "required": True}],
           "templateDescription": "阶段三隔离验证"}
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "typeCode": "SMART_DISPLAY",
      "beforeTemplateCount": len(before_names), "invalid": {}}
mutations = {
    "emptyCode": dict(payload, templateCode=""),
    "longCode": dict(payload, templateCode="A" * 33),
    "badCodeCharacters": dict(payload, templateCode="S3-BAD-CODE"),
    "longName": dict(payload, templateName="N" * 65),
    "longDescription": dict(payload, templateDescription="D" * 501),
    "emptyInput": dict(payload, inputParams=[]),
    "missingInputName": dict(payload, inputParams=[{"type": "String", "required": True}]),
    "emptyOutput": dict(payload, outputParams=[]),
    "outOfBoundaryType": dict(payload, capabilityType="CAP_BAGGAGE_MEASURE"),
}
for label, variant in mutations.items():
    response_status, message = status(variant)
    ev["invalid"][label] = {"httpStatus": response_status,
                             "boundaryMessage": "该设备类型不支持此能力类型" in (message or ""),
                             "missingNameMessage": "参数名不能为空" in (message or "")}
ev["invalidRequestsCreatedNoTemplate"] = names() == before_names
created = []
try:
    first = api(base, "POST", payload)
    created.append(code)
    ev["createdVersion"] = first["templateVersion"]
    ev["createdUsageCount"] = first["usageCount"]
    ev["duplicateHttpStatus"] = status(payload)[0]
    updated = api(base + "/" + code, "PUT", {
        "templateName": payload["templateName"],
        "inputParams": [input_param("contentType", default="TEXT"), input_param("contentData", default="updated")],
        "outputParams": payload["outputParams"], "templateDescription": payload["templateDescription"]})
    ev["updatedVersion"] = updated["templateVersion"]
    ev["updatedDefaultVisible"] = any(row.get("name") == "contentData" and row.get("defaultValue") == "updated"
                                       for row in updated["inputParams"])
    ev["listedVersionAfterUpdate"] = next(row["templateVersion"] for row in api(base) if row["templateCode"] == code)
    ev["historicalVersionEndpointStatus"] = get_status(base + "/" + code + "/versions")
    ev["versionRowsAfterUpdate"] = db.query(db.source,
        "SELECT template_version FROM tip_stage2_v14.capability_template "
        "WHERE device_type_code='SMART_DISPLAY' AND template_code='S3_TC018_TEMPLATE'").splitlines()
    incomplete = dict(payload, templateCode=bad_code, templateName="阶段三缺必填参数验证",
                      inputParams=[input_param("unexpectedParam")])
    incomplete_status, _ = status(incomplete)
    ev["incompleteRequiredInputHttpStatus"] = incomplete_status
    if incomplete_status == 200:
        created.append(bad_code)
    ev["beforeCleanupTemplateCount"] = len(names())
finally:
    cleanup_errors = []
    for item in reversed(created):
        try:
            api(base + "/" + item, "DELETE")
        except Exception:
            cleanup_errors.append(item)
    ev["cleanupErrors"] = cleanup_errors
    ev["afterCleanupTemplateCount"] = len(names())
    ev["temporaryCodesAbsentAfter"] = all(item not in names() for item in (code, bad_code))

out = Path(__file__).resolve().parent / "evidence/TC-018-019-template-crud.json"
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(ev, ensure_ascii=False))
