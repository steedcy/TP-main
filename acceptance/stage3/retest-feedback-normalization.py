"""TC-024.S1: real simulator timeout and signed invalid feedback during a dry-run."""
import importlib.util
import json
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
template = next(t for t in api("/baseline-templates")
                if t["templateName"] == "S3_TC028_DISPLAY_DRYRUN")
assert template["templateStatus"] == "DISABLED"
agent = next(a for a in api("/device-agents?page=1&size=100")["content"]
             if a["deviceCode"] == "SIM_F2_DISPLAY")
assert agent["onlineStatus"] == "ONLINE" and agent["workStatus"] == "IDLE"
assert agent["currentTaskId"] is None
device = api("/devices/SIM_F2_DISPLAY")
base = device["accessEndpoint"] + "/device-api/v1"
secret = local.secrets()["SIM_F2_DISPLAY"]
out = stage / "evidence" / ("TC-024-feedback-normalization-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "templateId": template["id"],
      "agentBefore": agent, "phases": {}, "restore": {}}
active_id = None

def event_rows(task_id):
    return db.query(db.source,
        "SELECT event_type || '|' || coalesce(reason_code,'') FROM tip_stage2_v14.task_events "
        f"WHERE task_id={task_id} ORDER BY id").splitlines()

def command_rows(task_id):
    return db.query(db.source,
        "SELECT command_type || '|' || command_status || '|' || command_id "
        f"FROM tip_stage2_v14.device_commands WHERE task_id={task_id} ORDER BY id").splitlines()

def draft():
    current = api(f"/baseline-templates/{template['id']}")
    return api(f"/baseline-templates/{template['id']}", "PUT",
               {"inputParams": current["inputParams"], "steps": current["steps"]})

def start():
    return api(f"/baseline-templates/{template['id']}/dry-run", "POST",
               {"inputParams": {}, "simulatedDevices": [
                   {"stepSeq": 1, "agentId": agent["agentId"]}]})

try:
    ev["phases"]["timeout"] = {}
    timeout = ev["phases"]["timeout"]
    timeout["templateVersion"] = draft()["templateVersion"]
    timeout["simulatorControl"] = local.request(base + "/control/scenario", "POST",
        {"scenarioResult": "TIMEOUT"}, token=secret)["scenarioResult"]
    started = start()
    active_id = started["taskId"]
    timeout["taskId"] = active_id
    deadline = time.monotonic() + 35
    result = started
    while result["result"] == "RUNNING" and time.monotonic() < deadline:
        time.sleep(0.5)
        result = api(f"/baseline-templates/{template['id']}/dry-runs/{active_id}")
    timeout["dryRun"] = result
    timeout["commands"] = command_rows(active_id)
    timeout["events"] = event_rows(active_id)
    active_id = None if result["result"] != "RUNNING" else active_id
    local.request(base + "/control/scenario", "POST", {"scenarioResult": "SUCCESS"}, token=secret)

    invalid = ev["phases"]["invalid"] = {}
    invalid["templateVersion"] = draft()["templateVersion"]
    invalid["delayMs"] = local.request(base + "/control/delay?milliseconds=45000", "POST",
                                      token=secret)["milliseconds"]
    started = start()
    active_id = started["taskId"]
    invalid["taskId"] = active_id
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        commands = command_rows(active_id)
        if any(row.startswith("EXECUTE_CAPABILITY|") for row in commands):
            break
        time.sleep(0.2)
    invalid["commandsBefore"] = commands
    command_id = next(row.split("|")[2] for row in commands
                      if row.startswith("EXECUTE_CAPABILITY|"))
    invalid["eventRowsBefore"] = event_rows(active_id)
    report = {"reportType": "EXECUTION_FEEDBACK",
              "reportedAt": datetime.now(timezone.utc).isoformat(),
              "feedback": {"commandId": command_id, "attemptNo": 0,
                           "executionResult": "UNRECOGNIZED", "reasonCode": "BAD_PROTO",
                           "outputParams": {}}}
    invalid["sentFeedback"] = report
    try:
        invalid["response"] = local.request(
            f"http://127.0.0.1:8080/device-api/v1/agents/{agent['agentId']}/report",
            "POST", report, token=secret)
        invalid["httpAccepted"] = True
    except Exception as error:
        invalid["httpAccepted"] = False
        invalid["httpError"] = str(error)
    invalid["eventRowsAfter"] = event_rows(active_id)
    invalid["commandsAfter"] = command_rows(active_id)
    invalid["dryRunAfter"] = api(f"/baseline-templates/{template['id']}/dry-runs/{active_id}")
finally:
    if active_id is not None:
        try:
            ev["restore"]["cancel"] = api(
                f"/baseline-templates/{template['id']}/dry-runs/{active_id}/cancel", "POST")
        except Exception as error:
            ev["restore"]["cancelError"] = str(error)
    for key, url, data in (
        ("scenario", base + "/control/scenario", {"scenarioResult": "SUCCESS"}),
        ("delayMs", base + "/control/delay?milliseconds=1000", None),
    ):
        try:
            ev["restore"][key] = local.request(url, "POST", data, token=secret)
        except Exception as error:
            ev["restore"][key + "Error"] = str(error)
    try:
        api(f"/baseline-templates/{template['id']}/disable", "POST")
        ev["restore"]["templateStatus"] = api(
            f"/baseline-templates/{template['id']}")["templateStatus"]
    except Exception as error:
        ev["restore"]["templateError"] = str(error)
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        agents = [a for a in api("/device-agents?page=1&size=100")["content"]
                  if a["deviceCode"].startswith("SIM_F2_")]
        if len(agents) == 6 and all(a["agentStatus"] == "ENABLED" and
            a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE" and
            a["currentTaskId"] is None for a in agents):
            break
        time.sleep(0.5)
    ev["restore"]["allSixOnlineIdle"] = len(agents) == 6 and all(
        a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE" and
        a["workStatus"] == "IDLE" and a["currentTaskId"] is None for a in agents)
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(json.dumps({"evidence": str(out),
                  "timeoutResult": ev["phases"].get("timeout", {}).get("dryRun", {}).get("result"),
                  "invalidAccepted": ev["phases"].get("invalid", {}).get("httpAccepted"),
                  "allSixOnlineIdle": ev["restore"]["allSixOnlineIdle"]}, ensure_ascii=False))
