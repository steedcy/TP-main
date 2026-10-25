"""TC-020/021: temporary capability through live idle display agent, then clean it."""
import importlib.util
import json
import re
import time
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
device = "SIM_F2_DISPLAY"
cap_code = "S3_TC020_LIVE_INFO"
path = "/devices/" + device + "/capabilities"
out = Path(__file__).resolve().parent / "evidence/TC-020-021-capability-live.json"
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "deviceCode": device,
      "capabilityCode": cap_code, "observations": {}, "cleanup": {}}


def raw(method, suffix, data=None):
    body = json.dumps(data, ensure_ascii=False).encode() if data is not None else None
    request = urllib.request.Request(local.BASE + path + suffix, method=method, data=body,
        headers={"Authorization": "Bearer " + api.token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read()).get("message")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read()).get("message")


def command_summary(command_id):
    assert re.fullmatch(r"TEST-[0-9a-f]{26}", command_id)
    row = db.query(db.source,
        "SELECT command_type,command_status,extract(epoch from (updated_at-created_at))::numeric(10,3),"
        "CASE WHEN response_payload IS NULL THEN 'N' ELSE 'Y' END "
        "FROM tip_stage2_v14.device_commands WHERE command_id='" + command_id + "'")
    return row


before = api(path)
assert cap_code not in {item["capabilityCode"] for item in before}
assert db.query(db.source, "SELECT count(*) FROM tip_stage2_v14.device_agents WHERE current_task_id IS NOT NULL") == "0"
agent = next(x for x in api("/device-agents?page=1&size=100")["content"] if x["deviceCode"] == device)
assert agent["agentStatus"] == "ENABLED" and agent["onlineStatus"] == "ONLINE" and agent["workStatus"] == "IDLE"
source_cap = next(x for x in before if x["capabilityCode"] == "CAP_INFO_DISPLAY")
payload = {"capabilityCode": cap_code, "capabilityName": "阶段三临时真实代理调用",
           "capabilityType": "CAP_INFO_DISPLAY", "inputParams": source_cap["inputParams"],
           "outputParams": source_cap["outputParams"], "applicableCondition": "F2",
           "capabilityDescription": "阶段三完成后删除"}
try:
    created = api(path, "POST", payload)
    ev["observations"]["createdStatus"] = created["capabilityStatus"]
    ev["observations"]["enableUntested"] = raw("POST", "/" + cap_code + "/status", {"status": "ENABLED"})
    t0 = time.monotonic()
    tested = api(path + "/" + cap_code + "/test", "POST")
    ev["observations"]["firstTestWallMs"] = round((time.monotonic() - t0) * 1000)
    ev["observations"]["firstTestStatus"] = tested["capabilityStatus"]
    ev["observations"]["firstTestResult"] = tested["testResult"]
    ev["observations"]["firstTestAt"] = tested["lastTestAt"]
    first_command = tested["testResult"].rsplit(" ", 1)[-1]
    ev["observations"]["firstCommandId"] = first_command
    ev["observations"]["firstCommandRecord"] = command_summary(first_command)
    api(path + "/" + cap_code + "/status", "POST", {"status": "ENABLED"})
    ev["observations"]["statusAfterEnable"] = next(x["capabilityStatus"] for x in api(path)
                                                          if x["capabilityCode"] == cap_code)
    edited_inputs = [dict(item) for item in source_cap["inputParams"]]
    next(item for item in edited_inputs if item["name"] == "contentData")["defaultValue"] = "stage3-edit"
    edited = api(path + "/" + cap_code, "PUT", {
        "capabilityName": payload["capabilityName"], "inputParams": edited_inputs,
        "outputParams": payload["outputParams"], "applicableCondition": "F2",
        "capabilityDescription": payload["capabilityDescription"]})
    ev["observations"]["statusAfterEdit"] = edited["capabilityStatus"]
    ev["observations"]["editClearedTestResult"] = edited["testResult"] is None
    ev["observations"]["enableAfterEdit"] = raw("POST", "/" + cap_code + "/status", {"status": "ENABLED"})
    retested = api(path + "/" + cap_code + "/test", "POST")
    ev["observations"]["retestStatus"] = retested["capabilityStatus"]
    second_command = retested["testResult"].rsplit(" ", 1)[-1]
    ev["observations"]["retestCommandId"] = second_command
    ev["observations"]["retestCommandRecord"] = command_summary(second_command)
    api(path + "/" + cap_code + "/status", "POST", {"status": "ENABLED"})
    api(path + "/" + cap_code + "/status", "POST", {"status": "DISABLED"})
    ev["observations"]["statusAfterDisable"] = next(x["capabilityStatus"] for x in api(path)
                                                           if x["capabilityCode"] == cap_code)
    logs = api("/operation-logs?page=1&size=100")["content"]
    ev["observations"]["auditTypes"] = sorted({x["operationType"] for x in logs
        if cap_code in str(x.get("operationTarget", ""))})
finally:
    try:
        db.query(db.source,
            "DELETE FROM tip_stage2_v14.device_capabilities WHERE capability_code='S3_TC020_LIVE_INFO' "
            "AND device_id=(SELECT id FROM tip_stage2_v14.devices WHERE device_code='SIM_F2_DISPLAY')")
        ev["cleanup"]["temporaryCapabilityAbsent"] = all(x["capabilityCode"] != cap_code for x in api(path))
        ev["cleanup"]["originalCapabilityCodesUnchanged"] = (
            {x["capabilityCode"] for x in api(path)} == {x["capabilityCode"] for x in before})
        after_agent = next(x for x in api("/device-agents?page=1&size=100")["content"] if x["deviceCode"] == device)
        ev["cleanup"]["agentStatus"] = [after_agent["agentStatus"], after_agent["onlineStatus"], after_agent["workStatus"]]
    except Exception as error:
        ev["cleanup"]["error"] = str(error)
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(ev, ensure_ascii=False))
