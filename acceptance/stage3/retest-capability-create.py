"""Fresh TC-020.S1 and TC-022.S1 checks in one temporary device."""
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
code = "S3_TC020_DISPLAY"
cap_code = "S3_TC020_INFO"
path = "/devices/" + code + "/capabilities"
out = Path(__file__).resolve().parent / "evidence/TC-020-022-capability-create.json"
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "deviceCode": code, "capabilityCode": cap_code,
      "invalid": {}, "cleanup": {}}


def raw(payload):
    request = urllib.request.Request(local.BASE + path, method="POST",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Authorization": "Bearer " + api.token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read()).get("message")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read()).get("message")


assert db.query(db.source, "SELECT count(*) FROM tip_stage2_v14.devices WHERE device_code='" + code + "'") == "0"
device = {"deviceCode": code, "deviceName": "阶段三临时能力测试航显",
          "deviceTypeCode": "SMART_DISPLAY", "isSimulator": False, "areaCode": "F2",
          "positionX": 11, "positionY": 11, "accessEndpoint": "http://127.0.0.1:8998",
          "accessCredentialRef": "S3-TEST-UNUSED", "statusReportInterval": 15,
          "remark": "仅阶段三实例能力验证"}
payload = {"capabilityCode": cap_code, "capabilityName": "阶段三信息展示",
           "capabilityType": "CAP_INFO_DISPLAY",
           "inputParams": [
               {"name": "contentType", "type": "String", "required": True, "defaultValue": "TEXT", "range": "TEXT"},
               {"name": "contentData", "type": "String", "required": True, "defaultValue": "stage3", "range": "非空"},
               {"name": "displayDuration", "type": "Number", "required": True, "defaultValue": "30", "range": "1～60"}],
           "outputParams": [{"name": "displayStatus", "type": "String", "required": True, "range": "结果"}],
           "applicableCondition": "F2 且设备在线", "capabilityDescription": "阶段三临时能力配置"}
try:
    api("/devices", "POST", device)
    ev["initialCapabilities"] = len(api(path))
    created = api(path, "POST", payload)
    ev["created"] = {key: created.get(key) for key in
                     ("capabilityCode", "capabilityName", "capabilityType", "inputParams", "outputParams",
                      "applicableConditions", "capabilityDescription", "capabilityStatus", "lastTestAt")}
    ev["listed"] = [{key: row.get(key) for key in ("capabilityCode", "capabilityStatus", "lastTestAt")}
                    for row in api(path)]
    variants = {
        "duplicateCode": payload,
        "emptyInput": dict(payload, capabilityCode="S3_TC020_EMPTY_INPUT", inputParams=[]),
        "emptyOutput": dict(payload, capabilityCode="S3_TC020_EMPTY_OUTPUT", outputParams=[]),
        "missingInputName": dict(payload, capabilityCode="S3_TC020_MISSING_NAME",
                                 inputParams=[{"type": "String", "required": True}]),
        "outOfBoundary": dict(payload, capabilityCode="S3_TC020_OUT_OF_BOUNDARY",
                              capabilityType="CAP_BAGGAGE_MEASURE"),
        "unknownStandardType": dict(payload, capabilityCode="S3_TC020_UNKNOWN_TYPE",
                                    capabilityType="CAP_NOT_IN_EIGHT"),
    }
    for name, variant in variants.items():
        status, message = raw(variant)
        ev["invalid"][name] = {"httpStatus": status, "message": message}
    ev["codesAfterInvalid"] = [x["capabilityCode"] for x in api(path)]
finally:
    try:
        api("/devices/" + code, "DELETE")
        db.query(db.source,
            "DELETE FROM tip_stage2_v14.device_capabilities WHERE device_id IN "
            "(SELECT id FROM tip_stage2_v14.devices WHERE device_code='S3_TC020_DISPLAY') "
            "AND capability_code LIKE 'S3_TC020_%'")
        ev["cleanup"]["deviceStatus"] = db.query(db.source,
            "SELECT device_status FROM tip_stage2_v14.devices WHERE device_code='S3_TC020_DISPLAY'")
        ev["cleanup"]["capabilityRows"] = db.query(db.source,
            "SELECT count(*) FROM tip_stage2_v14.device_capabilities WHERE device_id IN "
            "(SELECT id FROM tip_stage2_v14.devices WHERE device_code='S3_TC020_DISPLAY')")
    except Exception as error:
        ev["cleanup"]["error"] = str(error)
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(ev, ensure_ascii=False))
