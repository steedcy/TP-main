"""TC-012.S1: exercise both disable confirmation paths during real occupation."""
import importlib.util
import json
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
config = local.API("配置管理员")
operator = local.API("运行操作员")
code = "SIM_F2_DISPLAY"
template = next(t for t in config("/baseline-templates")
                if t["templateName"] == "S3_TC028_DISPLAY_DRYRUN")
assert template["templateStatus"] == "DISABLED"
agent = next(a for a in config("/device-agents?page=1&size=100")["content"]
             if a["deviceCode"] == code)
assert (agent["agentStatus"], agent["onlineStatus"], agent["workStatus"],
        agent["currentTaskId"]) == ("ENABLED", "ONLINE", "IDLE", None)
base = config("/devices/" + code)["accessEndpoint"] + "/device-api/v1"
secret = local.secrets()[code]
out = stage / "evidence" / (
    "TC-012-disable-busy-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "agentId": agent["agentId"],
      "templateId": template["id"], "before": agent, "restore": {}}
task_id = None
try:
    ev["draft"] = config(f"/baseline-templates/{template['id']}", "PUT",
                         {"inputParams": template["inputParams"], "steps": template["steps"]})
    ev["delayMs"] = local.request(base + "/control/delay?milliseconds=45000",
                                  "POST", token=secret)["milliseconds"]
    started = config(f"/baseline-templates/{template['id']}/dry-run", "POST",
                     {"inputParams": {}, "simulatedDevices": [
                         {"stepSeq": 1, "agentId": agent["agentId"]}]})
    task_id = started["taskId"]
    ev["dryRunStarted"] = started
    deadline = time.monotonic() + 18
    while time.monotonic() < deadline:
        busy = config("/device-agents/" + agent["agentId"])
        if busy["workStatus"] == "BUSY" and busy["currentTaskId"] == task_id:
            break
        time.sleep(.2)
    ev["atBusy"] = busy
    assert busy["workStatus"] == "BUSY" and busy["currentTaskId"] == task_id
    ev["eventsBefore"] = operator(f"/tasks/{task_id}/events")
    try:
        config("/device-agents/" + agent["agentId"] + "/disable", "POST",
               {"confirmed": False})
        ev["cancelConfirmation"] = {"accepted": True}
    except RuntimeError as error:
        ev["cancelConfirmation"] = {"accepted": False, "error": str(error)}
    ev["afterCancelConfirmation"] = config("/device-agents/" + agent["agentId"])
    ev["eventsAfterCancelConfirmation"] = operator(f"/tasks/{task_id}/events")
    config("/device-agents/" + agent["agentId"] + "/disable", "POST",
           {"confirmed": True})
    ev["afterConfirmedDisable"] = config("/device-agents/" + agent["agentId"])
    ev["eventsAfterConfirmedDisable"] = operator(f"/tasks/{task_id}/events")
    ev["taskAfterConfirmedDisable"] = operator(f"/tasks/{task_id}")
    time.sleep(2)
    ev["afterTwoSeconds"] = config("/device-agents/" + agent["agentId"])
    ev["eventsAfterTwoSeconds"] = operator(f"/tasks/{task_id}/events")
finally:
    if task_id is not None:
        try:
            ev["restore"]["cancel"] = config(
                f"/baseline-templates/{template['id']}/dry-runs/{task_id}/cancel", "POST")
        except Exception as error:
            ev["restore"]["cancelError"] = str(error)
    try:
        ev["restore"]["delayMs"] = local.request(
            base + "/control/delay?milliseconds=1000", "POST", token=secret)["milliseconds"]
    except Exception as error:
        ev["restore"]["delayError"] = str(error)
    try:
        ev["restore"]["reenabled"] = config("/device-agents", "POST", {"deviceCode": code})
    except Exception as error:
        ev["restore"]["reenableError"] = str(error)
    try:
        config(f"/baseline-templates/{template['id']}/disable", "POST")
        ev["restore"]["templateStatus"] = config(
            f"/baseline-templates/{template['id']}")["templateStatus"]
    except Exception as error:
        ev["restore"]["templateError"] = str(error)
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        agents = [a for a in config("/device-agents?page=1&size=100")["content"]
                  if a["deviceCode"].startswith("SIM_F2_")]
        if len(agents) == 6 and all(
            a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE"
            and a["workStatus"] == "IDLE" and a["currentTaskId"] is None
            for a in agents):
            break
        time.sleep(.5)
    ev["restore"]["agents"] = agents
    if task_id is not None:
        ev["restore"]["finalEvents"] = operator(f"/tasks/{task_id}/events")
        ev["restore"]["finalDryRun"] = config(
            f"/baseline-templates/{template['id']}/dry-runs/{task_id}")
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(json.dumps({"evidence": str(out), "taskId": task_id,
                  "afterConfirmedDisable": ev.get("afterConfirmedDisable", {}).get("agentStatus"),
                  "allSixOnlineIdle": len(agents) == 6 and all(
                      a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE"
                      and a["workStatus"] == "IDLE" and a["currentTaskId"] is None
                      for a in agents)}, ensure_ascii=False))
