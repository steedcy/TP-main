"""TC-014.S2: stop one simulator's heartbeats beyond the real 30-second threshold."""
import importlib.util
import json
import re
import time
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
device = api("/devices/" + code)
secret = local.secrets()[code]
endpoint = device["accessEndpoint"] + "/device-api/v1/control/heartbeat"


def agent():
    rows = api("/device-agents?page=1&size=100")["content"]
    return next(row for row in rows if row["deviceCode"] == code)


before = agent()
assert before["onlineStatus"] == "ONLINE" and before["currentTaskId"] is None
agent_code = before["agentId"]
assert re.fullmatch(r"AGT-[A-Z0-9]{8}", agent_code)
agent_id = int(db.query(db.source,
    f"SELECT id FROM tip_stage2_v14.device_agents WHERE agent_code='{agent_code}'"))


def count_event(kind):
    return int(db.query(db.source,
        f"SELECT count(*) FROM tip_stage2_v14.device_events WHERE device_agent_id={agent_id} "
        f"AND event_type='{kind}'"))


before_offline = count_event("AGENT_OFFLINE_DETECTED")
before_recovered = count_event("AGENT_ONLINE_RECOVERED")
evidence = {"startedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
            "isolatedSchema": "tip_stage2_v14", "deviceCode": code,
            "beforeOnlineStatus": before["onlineStatus"], "beforeLastReportedAt": before["lastReportedAt"]}
stopped_at = time.monotonic()
try:
    local.request(endpoint + "?value=false", "POST", token=secret)
    deadline = time.monotonic() + 58
    while time.monotonic() < deadline:
        current = agent()
        if current["onlineStatus"] == "OFFLINE":
            evidence["offlineElapsedSeconds"] = round(time.monotonic() - stopped_at, 2)
            evidence["offlineStatus"] = current["onlineStatus"]
            evidence["offlineLastReportedAt"] = current["lastReportedAt"]
            break
        time.sleep(2)
    else:
        evidence["offlineStatus"] = agent()["onlineStatus"]
    evidence["offlineEventDelta"] = count_event("AGENT_OFFLINE_DETECTED") - before_offline
    online_rows = api("/device-agents?onlineStatus=ONLINE&page=1&size=100")["content"]
    evidence["excludedFromOnlineFilter"] = all(row["deviceCode"] != code for row in online_rows)
finally:
    local.request(endpoint + "?value=true", "POST", token=secret)
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline and agent()["onlineStatus"] != "ONLINE":
        time.sleep(1)
    evidence["recoveredStatus"] = agent()["onlineStatus"]
    evidence["recoveryEventDelta"] = count_event("AGENT_ONLINE_RECOVERED") - before_recovered
    evidence["finishedAt"] = datetime.now(timezone.utc).isoformat()

out = Path(__file__).resolve().parent / "evidence/TC-014-heartbeat.json"
out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(evidence, ensure_ascii=False))
