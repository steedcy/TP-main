"""TC-035.S1: live snapshot excludes offline/disabled agents and disabled capability."""
import importlib.util
import json
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
db_spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(db_spec)
db_spec.loader.exec_module(db)
config, operator = local.API("配置管理员"), local.API("运行操作员")
codes = ["SIM_F2_DISPLAY", "SIM_F2_ROBOT_B", "SIM_F2_FLIGHT"]
def agent(code):
    return next(a for a in config("/device-agents?page=1&size=100")["content"] if a["deviceCode"] == code)
before = {code: agent(code) for code in codes}
assert all(a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE" and
           a["workStatus"] == "IDLE" for a in before.values())
cap_path = "/devices/SIM_F2_FLIGHT/capabilities/CAP_INFO_DISPLAY/status"
cap_before = next(c for c in config("/devices/SIM_F2_FLIGHT/capabilities")
                  if c["capabilityCode"] == "CAP_INFO_DISPLAY")
assert cap_before["capabilityStatus"] == "ENABLED"
display = config("/devices/SIM_F2_DISPLAY")
heartbeat_url = display["accessEndpoint"] + "/device-api/v1/control/heartbeat"
secret = local.secrets()["SIM_F2_DISPLAY"]
source = operator("/tasks/19")
assert source["status"] == "COMPLETED" and source["taskFamily"] == "OVERSIZE_BAGGAGE_HANDLING"
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "schema": "tip_stage2_v14", "beforeAgents": before, "capabilityBefore": cap_before,
      "injections": {}, "task": {}, "snapshot": {}, "restore": {}}
out = Path(__file__).parent / "evidence/TC-035-context-exclusions.json"
robot_disabled = cap_disabled = heartbeat_paused = False
task_id = None
try:
    config(cap_path, "POST", {"status": "DISABLED"})
    cap_disabled = True
    ev["injections"]["flightDisplayCapability"] = next(c for c in config("/devices/SIM_F2_FLIGHT/capabilities")
        if c["capabilityCode"] == "CAP_INFO_DISPLAY")["capabilityStatus"]
    config(f"/device-agents/{before['SIM_F2_ROBOT_B']['agentId']}/disable", "POST", {"confirmed": True})
    robot_disabled = True
    ev["injections"]["robotBAgent"] = agent("SIM_F2_ROBOT_B")["agentStatus"]
    local.request(heartbeat_url + "?value=false", "POST", token=secret)
    heartbeat_paused = True
    deadline = time.monotonic() + 55
    while time.monotonic() < deadline and agent("SIM_F2_DISPLAY")["onlineStatus"] != "OFFLINE":
        time.sleep(2)
    ev["injections"]["displayAgent"] = agent("SIM_F2_DISPLAY")["onlineStatus"]
    assert ev["injections"]["displayAgent"] == "OFFLINE"
    ev["injections"]["agentStatesAtSubmit"] = [
        {"code": a["deviceCode"], "agentStatus": a["agentStatus"], "onlineStatus": a["onlineStatus"]}
        for a in config("/device-agents?page=1&size=100")["content"]
        if a["deviceCode"].startswith("SIM_F2_")]
    max_before = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
    request = {"taskGoal": source["taskGoal"], "taskFamily": source["taskFamily"],
               "sceneParams": source["sceneParams"]}
    ev["task"]["request"] = request
    try:
        ev["task"]["submitResponse"] = operator("/tasks", "POST", request)
    except RuntimeError as error:
        ev["task"]["submitError"] = str(error)
    max_after = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
    ev["task"]["beforeMaxId"] = max_before
    ev["task"]["afterMaxId"] = max_after
    assert max_after > max_before
    task_id = max_after
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        contexts = operator(f"/tasks/{task_id}/context-snapshots")
        if contexts:
            break
        time.sleep(0.5)
    ev["task"]["statusAtSnapshot"] = operator(f"/tasks/{task_id}")["status"]
    ev["snapshot"]["raw"] = contexts
    if contexts:
        initial = min(contexts, key=lambda c: c["id"])
        ev["snapshot"]["initialId"] = initial["id"]
        ev["snapshot"]["agents"] = json.loads(initial["agents"])
        ev["snapshot"]["coverage"] = json.loads(initial["capabilityCoverage"])
        ev["snapshot"]["failed"] = json.loads(initial["failedAgentCodes"])
finally:
    if heartbeat_paused:
        try:
            local.request(heartbeat_url + "?value=true", "POST", token=secret)
            ev["restore"]["heartbeatEnabled"] = True
        except Exception as error:
            ev["restore"]["heartbeatError"] = str(error)
    if robot_disabled:
        try:
            ev["restore"]["robotB"] = config("/device-agents", "POST",
                {"deviceCode": "SIM_F2_ROBOT_B"})["agentStatus"]
        except Exception as error:
            ev["restore"]["robotBError"] = str(error)
    if cap_disabled:
        try:
            config(cap_path, "POST", {"status": "ENABLED"})
            ev["restore"]["flightDisplayCapability"] = next(c for c in config("/devices/SIM_F2_FLIGHT/capabilities")
                if c["capabilityCode"] == "CAP_INFO_DISPLAY")["capabilityStatus"]
        except Exception as error:
            ev["restore"]["capabilityError"] = str(error)
    if task_id:
        deadline = time.monotonic() + 35
        task = operator(f"/tasks/{task_id}")
        while task["status"] in ["PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT", "DOWNGRADING", "EXECUTING"] \
                and time.monotonic() < deadline:
            time.sleep(1)
            task = operator(f"/tasks/{task_id}")
        if task["status"] in ["PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT", "DOWNGRADING", "EXECUTING"]:
            try:
                task = operator(f"/tasks/{task_id}/terminate", "POST",
                    {"confirmed": True, "reason": "阶段3上下文隔离复测清场"})
            except Exception as error:
                ev["restore"]["taskTerminateError"] = str(error)
        ev["task"]["final"] = task
        ev["task"]["events"] = operator(f"/tasks/{task_id}/events")
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        current = [a for a in config("/device-agents?page=1&size=100")["content"]
                   if a["deviceCode"].startswith("SIM_F2_")]
        if len(current) == 6 and all(a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE"
                                     and a["workStatus"] == "IDLE" for a in current):
            break
        time.sleep(1)
    ev["restore"]["agents"] = current
    ev["restore"]["allSixOnlineIdle"] = len(current) == 6 and all(
        a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE"
        for a in current)
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"taskId": task_id, "snapshotAgents": [a["deviceCode"] for a in ev["snapshot"].get("agents", [])],
                  "coverage": ev["snapshot"].get("coverage"), "finalTaskStatus": ev["task"].get("final", {}).get("status"),
                  "allSixOnlineIdle": ev["restore"]["allSixOnlineIdle"]}, ensure_ascii=False))
