"""TC-014.S1: two signed reports 15 seconds apart, with API/DB/UI evidence."""
import importlib.util
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


local = module("local", root / "scripts/local-test-environment.py")
db = module("db", root / "acceptance/stage2/db-isolation.py")
api = local.API("配置管理员")
code = "SIM_F2_DISPLAY"
device = api("/devices/" + code)
agent = next(a for a in api("/device-agents?page=1&size=100")["content"]
             if a["deviceCode"] == code)
assert agent["agentStatus"] == "ENABLED" and agent["onlineStatus"] == "ONLINE"
assert agent["workStatus"] == "IDLE" and agent["currentTaskId"] is None
secret = local.secrets()[code]
agent_code = agent["agentId"]
base = device["accessEndpoint"] + "/device-api/v1"
event_sql = ("SELECT count(*) FROM tip_stage2_v14.device_events WHERE device_agent_id="
             "(SELECT id FROM tip_stage2_v14.device_agents WHERE agent_code='" + agent_code + "')")


def snapshot():
    result = api("/situation/snapshot")
    return next(row for row in result["agents"] if row["deviceCode"] == code)


def state():
    return {"agent": api("/device-agents/" + agent_code),
            "device": api("/devices/" + code), "situation": snapshot(),
            "db": db.query(db.source,
                "SELECT json_build_object('onlineStatus',a.online_status,'workStatus',a.work_status,"
                "'businessStatus',a.business_status,'lastReportedAt',a.last_reported_at,"
                "'areaCode',d.area_code,'positionX',d.position_x,'positionY',d.position_y) "
                "FROM tip_stage2_v14.device_agents a JOIN tip_stage2_v14.devices d "
                "ON d.id=a.device_id WHERE a.agent_code='" + agent_code + "'"),
            "deviceEventCount": int(db.query(db.source, event_sql))}


def browser(phase):
    env = os.environ.copy()
    env["PLAYWRIGHT_CORE_PATH"] = ("C:/Users/savy/.cache/codex-runtimes/"
                                   "codex-primary-runtime/dependencies/node/node_modules/playwright-core")
    node = "C:/Users/savy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
    run = subprocess.run([node, str(stage / "retest-status-report-ui.cjs"), phase],
                         cwd=root, env=env, capture_output=True, encoding="utf-8",
                         errors="replace", timeout=90)
    return {"exitCode": run.returncode,
            "output": (run.stdout if run.returncode == 0 else run.stderr)[-800:].strip()}


def edit_interval(value):
    current = api("/devices/" + code)
    payload = {key: current[key] for key in ("deviceName", "areaCode", "positionX",
               "positionY", "accessEndpoint", "statusReportInterval", "remark")}
    payload["accessCredentialRef"] = ""
    payload["statusReportInterval"] = value
    return api("/devices/" + code, "PUT", payload)


evidence = {"observedAt": datetime.now(timezone.utc).isoformat(),
            "runtimeInput": "V1.5", "isolatedSchema": "tip_stage2_v14",
            "agentCode": agent_code, "deviceCode": code,
            "before": state(), "reportIntervalBefore": device["statusReportInterval"],
            "phases": {}, "restore": {}}
out = stage / "evidence" / ("TC-014-status-report-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
heartbeat_stopped = False
interval_changed = False
try:
    edit_interval(15)
    interval_changed = True
    evidence["reportIntervalDuring"] = api("/devices/" + code)["statusReportInterval"]
    local.request(base + "/control/heartbeat?value=false", "POST", token=secret)
    heartbeat_stopped = True
    first_at = None
    for phase, work, x, y, zone in (("A", "BUSY", 900, 4300, "F2_ZONE_A"),
                                     ("B", "IDLE", 820, 4250, "F2_ZONE_B")):
        if first_at is not None:
            time.sleep(max(0, 15 - (time.monotonic() - first_at)))
        reported_at = datetime.now(timezone.utc).isoformat()
        request = {"reportType": "STATUS", "reportedAt": reported_at,
                   "status": {"onlineStatus": "ONLINE", "workStatus": work,
                              "location": {"x": x, "y": y, "zone": zone},
                              "businessStatus": {"testState": "PHASE_" + phase}}}
        sent_at = time.monotonic()
        if first_at is None:
            first_at = sent_at
        response = local.request("http://127.0.0.1:8080/device-api/v1/agents/" +
                                 agent_code + "/report", "POST", request, token=secret)
        evidence["phases"][phase] = {"request": request, "response": response,
            "sentAt": reported_at, "elapsedSinceASeconds": round(sent_at - first_at, 3),
            "after": state(), "browser": browser(phase)}
finally:
    if heartbeat_stopped:
        evidence["restore"]["heartbeat"] = local.request(
            base + "/control/heartbeat?value=true", "POST", token=secret)
    if interval_changed:
        edit_interval(device["statusReportInterval"])
    time.sleep(7)
    evidence["restore"]["after"] = state()
    evidence["restore"]["allSixOnlineIdle"] = all(
        a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE"
        and a["currentTaskId"] is None
        for a in api("/device-agents?page=1&size=100")["content"]
        if a["deviceCode"].startswith("SIM_"))
    evidence["finishedAt"] = datetime.now(timezone.utc).isoformat()
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": out.name,
                  "phases": {key: {"elapsed": val["elapsedSinceASeconds"],
                          "browser": val["browser"], "agentWork": val["after"]["agent"]["workStatus"],
                          "zone": val["after"]["situation"].get("location")}
                      for key, val in evidence["phases"].items()},
                  "restored": evidence["restore"]["allSixOnlineIdle"]}, ensure_ascii=False))
