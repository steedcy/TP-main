"""TC-054.S1 two-step live dry-run: receipt before completion and step ordering."""
import copy
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
agents = [a for a in config("/device-agents?page=1&size=100")["content"]
          if a["deviceCode"].startswith("SIM_F2_")]
assert len(agents) == 6 and all(a["onlineStatus"] == "ONLINE" and
    a["workStatus"] == "IDLE" and a["currentTaskId"] is None for a in agents)
agent = next(a for a in agents if a["deviceCode"] == code)
base = config("/devices/" + code)["accessEndpoint"] + "/device-api/v1"
secret = local.secrets()[code]
second = copy.deepcopy(template["steps"][0])
second["stepSeq"] = 2
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "templateId": template["id"],
      "templateVersionBefore": template["templateVersion"], "originalSteps": template["steps"],
      "twoSteps": [template["steps"][0], second], "deviceCode": code,
      "agentId": agent["agentId"], "restore": {}}
out = stage / "evidence" / ("TC-054-two-step-receipt-order-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
task_id = None


def snapshot():
    return {"at": datetime.now(timezone.utc).isoformat(),
            "task": operator(f"/tasks/{task_id}"),
            "assignments": operator(f"/tasks/{task_id}/step-assignments"),
            "events": operator(f"/tasks/{task_id}/events"),
            "commands": [c for c in config(f"/simulators/{code}/commands")
                         if c["taskId"] == task_id],
            "agent": config("/device-agents/" + agent["agentId"])}


try:
    updated = config(f"/baseline-templates/{template['id']}", "PUT",
                     {"inputParams": template["inputParams"], "steps": ev["twoSteps"]})
    ev["twoStepDraftVersion"] = updated["templateVersion"]
    ev["delayDuringMs"] = local.request(base + "/control/delay?milliseconds=12000",
                                        "POST", token=secret)["milliseconds"]
    started = config(f"/baseline-templates/{template['id']}/dry-run", "POST",
                     {"inputParams": {}, "simulatedDevices": [
                         {"stepSeq": 1, "agentId": agent["agentId"]},
                         {"stepSeq": 2, "agentId": agent["agentId"]}]})
    task_id = started["taskId"]
    ev["started"] = started
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        commands = [c for c in config(f"/simulators/{code}/commands") if c["taskId"] == task_id]
        if any(c["commandType"] == "EXECUTE_CAPABILITY" and c["stepSeq"] == 1 for c in commands):
            break
        time.sleep(.15)
    ev["step1Received"] = snapshot()
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        commands = [c for c in config(f"/simulators/{code}/commands") if c["taskId"] == task_id]
        if any(c["commandType"] == "EXECUTE_CAPABILITY" and c["stepSeq"] == 2 for c in commands):
            break
        time.sleep(.15)
    ev["step2Received"] = snapshot()
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        task = operator(f"/tasks/{task_id}")
        if task["status"] in ("COMPLETED", "FAILED", "PENDING_MANUAL"):
            break
        time.sleep(.4)
    ev["finished"] = snapshot()
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
        restored = config(f"/baseline-templates/{template['id']}", "PUT",
                          {"inputParams": template["inputParams"], "steps": template["steps"]})
        ev["restore"]["templateVersion"] = restored["templateVersion"]
        config(f"/baseline-templates/{template['id']}/disable", "POST")
        final_template = config(f"/baseline-templates/{template['id']}")
        ev["restore"]["templateStatus"] = final_template["templateStatus"]
        ev["restore"]["templateStepsMatch"] = final_template["steps"] == template["steps"]
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
                  "firstStatus": ev.get("step1Received", {}).get("task", {}).get("status"),
                  "secondStatus": ev.get("step2Received", {}).get("task", {}).get("status"),
                  "finalStatus": ev.get("finished", {}).get("task", {}).get("status"),
                  "restore": ev["restore"]}, ensure_ascii=False))
