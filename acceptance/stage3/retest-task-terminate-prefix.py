"""TC-066.S2: terminate during step two and verify completed prefix retention."""
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
db_spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(db_spec)
db_spec.loader.exec_module(db)
config, operator = local.API("配置管理员"), local.API("运行操作员")
code = "SIM_F2_DISPLAY"
template = next(t for t in config("/baseline-templates")
                if t["templateName"] == "S3_TC028_DISPLAY_DRYRUN")
assert template["templateStatus"] == "DISABLED" and len(template["steps"]) == 1
agent = next(a for a in config("/device-agents?page=1&size=100")["content"]
             if a["deviceCode"] == code)
assert (agent["agentStatus"], agent["onlineStatus"], agent["workStatus"],
        agent["currentTaskId"]) == ("ENABLED", "ONLINE", "IDLE", None)
base = config("/devices/" + code)["accessEndpoint"] + "/device-api/v1"
secret = local.secrets()[code]
steps = copy.deepcopy(template["steps"])
second = copy.deepcopy(steps[0])
second["stepSeq"] = 2
steps.append(second)
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "templateId": template["id"],
      "templateBefore": {k: template.get(k) for k in ("templateVersion", "templateStatus", "steps")},
      "agentBefore": {k: agent.get(k) for k in (
          "agentId", "agentStatus", "onlineStatus", "workStatus", "currentTaskId")},
      "restore": {}}
out = stage / "evidence" / ("TC-066-terminate-prefix-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
task_id = None
try:
    updated = config(f"/baseline-templates/{template['id']}", "PUT",
                     {"inputParams": template["inputParams"], "steps": steps})
    ev["twoStepTemplate"] = {k: updated.get(k) for k in (
        "id", "templateVersion", "templateStatus", "steps")}
    ev["delayMs"] = local.request(base + "/control/delay?milliseconds=15000",
                                  "POST", token=secret)["milliseconds"]
    started = config(f"/baseline-templates/{template['id']}/dry-run", "POST",
                     {"inputParams": {}, "simulatedDevices": [
                         {"stepSeq": 1, "agentId": agent["agentId"]},
                         {"stepSeq": 2, "agentId": agent["agentId"]}]})
    task_id = started["taskId"]
    ev["started"] = started
    deadline = time.monotonic() + 55
    found = False
    while time.monotonic() < deadline:
        assignments = operator(f"/tasks/{task_id}/step-assignments")
        by_seq = {a["stepSeq"]: a for a in assignments}
        if by_seq.get(1, {}).get("stepStatus") == "COMPLETED" and \
           by_seq.get(2, {}).get("stepStatus") == "EXECUTING":
            found = True
            break
        time.sleep(.25)
    ev["prefixReached"] = found
    ev["taskBeforeTerminate"] = operator(f"/tasks/{task_id}")
    ev["assignmentsBeforeTerminate"] = assignments
    ev["agentBeforeTerminate"] = config("/device-agents/" + agent["agentId"])
    assert found and ev["taskBeforeTerminate"]["status"] == "EXECUTING"
    ev["terminateResponse"] = operator(f"/tasks/{task_id}/terminate", "POST",
        {"reason": "阶段3已完成前缀保留复测", "confirmed": True})
    ev["taskAfterTerminate"] = operator(f"/tasks/{task_id}")
    ev["assignmentsAfterTerminate"] = operator(f"/tasks/{task_id}/step-assignments")
    ev["eventsAfterTerminate"] = operator(f"/tasks/{task_id}/events")
    ev["agentAfterTerminate"] = config("/device-agents/" + agent["agentId"])
    commands = db.query(db.source,
        "SELECT id,command_type,command_status,step_seq FROM tip_stage2_v14.device_commands "
        "WHERE task_id=" + str(task_id) + " ORDER BY id").splitlines()
    ev["commandsAfterTerminate"] = [dict(zip(
        ("id", "type", "status", "stepSeq"), line.split("|"))) for line in commands]
finally:
    if task_id is not None:
        try:
            status = operator(f"/tasks/{task_id}")["status"]
            if status not in ("MANUAL_TERMINATED", "COMPLETED", "FAILED"):
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
        config(f"/baseline-templates/{template['id']}/disable", "POST")
        current = config(f"/baseline-templates/{template['id']}")
        ev["restore"]["template"] = {k: current.get(k) for k in (
            "templateVersion", "templateStatus", "steps")}
        ev["restore"]["sameTemplateSteps"] = current["steps"] == template["steps"]
    except Exception as error:
        ev["restore"]["templateError"] = str(error)
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        agents = [a for a in config("/device-agents?page=1&size=100")["content"]
                  if a["deviceCode"].startswith("SIM_F2_")]
        if len(agents) == 6 and all(a["agentStatus"] == "ENABLED" and
            a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE" and
            a["currentTaskId"] is None for a in agents):
            break
        time.sleep(.5)
    ev["restore"]["allSixOnlineIdle"] = len(agents) == 6 and all(
        a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE"
        and a["workStatus"] == "IDLE" and a["currentTaskId"] is None for a in agents)
    if task_id is not None:
        ev["restore"]["taskFinal"] = operator(f"/tasks/{task_id}")["status"]
        ev["restore"]["assignmentsFinal"] = operator(f"/tasks/{task_id}/step-assignments")
        ev["restore"]["eventsFinal"] = operator(f"/tasks/{task_id}/events")
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "taskId": task_id,
                  "prefixReached": ev.get("prefixReached"),
                  "taskAfterTerminate": ev.get("taskAfterTerminate", {}).get("status"),
                  "finalAssignments": [(a["stepSeq"], a["stepStatus"])
                                       for a in ev["restore"].get("assignmentsFinal", [])],
                  "allSixOnlineIdle": ev["restore"]["allSixOnlineIdle"],
                  "sameTemplateSteps": ev["restore"].get("sameTemplateSteps")}, ensure_ascii=False))
