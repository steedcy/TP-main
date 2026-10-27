"""Observe a real received command before and after its completion condition is met."""
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
template = next(item for item in config("/baseline-templates")
                if item["templateName"] == "S3_TC028_DISPLAY_DRYRUN")
assert template["templateStatus"] == "DISABLED" and len(template["steps"]) == 1
assert template["steps"][0]["completionCondition"] == "displayStatus=SUCCESS"
agents = [a for a in config("/device-agents?page=1&size=100")["content"]
          if a["deviceCode"].startswith("SIM_F2_")]
assert len(agents) == 6 and all(a["onlineStatus"] == "ONLINE" and
    a["workStatus"] == "IDLE" and a["currentTaskId"] is None for a in agents)
agent = next(a for a in agents if a["deviceCode"] == code)
base = config("/devices/" + code)["accessEndpoint"] + "/device-api/v1"
secret = local.secrets()[code]
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "templateId": template["id"],
      "templateVersionBefore": template["templateVersion"], "deviceCode": code,
      "agentId": agent["agentId"], "restore": {}}
task_id = None
out = stage / "evidence" / ("SRS_F017-R07-ack-gated-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
try:
    ev["delayBeforeMs"] = 1000
    updated = config(f"/baseline-templates/{template['id']}", "PUT",
                     {"inputParams": template["inputParams"], "steps": template["steps"]})
    ev["draftVersion"] = updated["templateVersion"]
    ev["delayDuringMs"] = local.request(base + "/control/delay?milliseconds=20000",
                                        "POST", token=secret)["milliseconds"]
    started = config(f"/baseline-templates/{template['id']}/dry-run", "POST",
                     {"inputParams": {}, "simulatedDevices": [
                         {"stepSeq": 1, "agentId": agent["agentId"]}]})
    task_id = started["taskId"]
    ev["started"] = started
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        commands = [c for c in config(f"/simulators/{code}/commands") if c["taskId"] == task_id]
        if {c["commandType"] for c in commands} >= {"TASK_ACCEPT", "EXECUTE_CAPABILITY"}:
            break
        time.sleep(.2)
    ev["receivedAt"] = datetime.now(timezone.utc).isoformat()
    ev["receivedCommands"] = commands
    ev["taskAtReceipt"] = operator(f"/tasks/{task_id}")
    ev["assignmentsAtReceipt"] = operator(f"/tasks/{task_id}/step-assignments")
    ev["eventsAtReceipt"] = operator(f"/tasks/{task_id}/events")
    deadline = time.monotonic() + 55
    while time.monotonic() < deadline:
        final_task = operator(f"/tasks/{task_id}")
        if final_task["status"] in ("COMPLETED", "FAILED", "PENDING_MANUAL"):
            break
        time.sleep(.5)
    ev["finishedAt"] = datetime.now(timezone.utc).isoformat()
    ev["taskAfterFeedback"] = final_task
    ev["assignmentsAfterFeedback"] = operator(f"/tasks/{task_id}/step-assignments")
    ev["eventsAfterFeedback"] = operator(f"/tasks/{task_id}/events")
    ev["commandsAfterFeedback"] = [c for c in config(f"/simulators/{code}/commands")
                                    if c["taskId"] == task_id]
finally:
    if task_id is not None:
        try:
            if operator(f"/tasks/{task_id}")["status"] in (
                "PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT", "DOWNGRADING", "EXECUTING"):
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
        config(f"/baseline-templates/{template['id']}/disable", "POST")
        ev["restore"]["templateStatus"] = config(
            f"/baseline-templates/{template['id']}")["templateStatus"]
    except Exception as error:
        ev["restore"]["templateError"] = str(error)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        agents = [a for a in config("/device-agents?page=1&size=100")["content"]
                  if a["deviceCode"].startswith("SIM_F2_")]
        if len(agents) == 6 and all(a["onlineStatus"] == "ONLINE" and
                a["workStatus"] == "IDLE" and a["currentTaskId"] is None for a in agents):
            break
        time.sleep(.5)
    ev["restore"]["allSixOnlineIdle"] = len(agents) == 6 and all(
        a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE" and
        a["currentTaskId"] is None for a in agents)
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": out.name, "taskId": task_id,
                  "receiptStatus": ev.get("taskAtReceipt", {}).get("status"),
                  "finalStatus": ev.get("taskAfterFeedback", {}).get("status"),
                  "receiptEventTypes": [x["eventType"] for x in ev.get("eventsAtReceipt", [])],
                  "allSixOnlineIdle": ev["restore"]["allSixOnlineIdle"]}, ensure_ascii=False))
