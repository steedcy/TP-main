"""TC-015.S1: invalid format and identity on the real device report endpoint."""
import importlib.util
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


local = module("local", root / "scripts/local-test-environment.py")
db = module("db", root / "acceptance/stage2/db-isolation.py")
api = local.API("配置管理员")
code = "SIM_F2_DISPLAY"
agent = next(x for x in api("/device-agents?page=1&size=100")["content"] if x["deviceCode"] == code)
agent_code = agent["agentId"]
assert re.fullmatch(r"AGT-[A-Z0-9]{8}", agent_code)
agent_id = int(db.query(db.source,
    f"SELECT id FROM tip_stage2_v14.device_agents WHERE agent_code='{agent_code}'"))
event_sql = f"SELECT count(*) FROM tip_stage2_v14.device_events WHERE device_agent_id={agent_id}"
before_events = int(db.query(db.source, event_sql))
before_device = api("/devices/" + code)
body = {"reportType": "STATUS", "reportedAt": datetime.now(timezone.utc).isoformat(),
        "status": {"onlineStatus": "INVALID", "workStatus": "IDLE", "location": {"x": 999, "y": 999}}}


def post(token):
    request = urllib.request.Request(
        "http://127.0.0.1:8080/device-api/v1/agents/" + agent_code + "/report",
        data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


format_status = post(local.secrets()[code])
identity_status = post("S3_BAD_DEVICE_TOKEN")
after_agent = next(x for x in api("/device-agents?page=1&size=100")["content"] if x["deviceCode"] == code)
after_device = api("/devices/" + code)
evidence = {
    "observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
    "isolatedSchema": "tip_stage2_v14", "deviceCode": code,
    "invalidFormatHttpStatus": format_status, "invalidIdentityHttpStatus": identity_status,
    "deviceEventDelta": int(db.query(db.source, event_sql)) - before_events,
    "onlineStatusUnchanged": after_agent["onlineStatus"] == agent["onlineStatus"],
    "workStatusUnchanged": after_agent["workStatus"] == agent["workStatus"],
    "positionUnchanged": (after_device["positionX"], after_device["positionY"])
                         == (before_device["positionX"], before_device["positionY"]),
}
out = Path(__file__).resolve().parent / "evidence/TC-015-invalid-report.json"
out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(evidence, ensure_ascii=False))
