"""TC-052.S1: race two dry-run steps for one simulator agent."""
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
template = next(x for x in api("/baseline-templates") if x["templateName"] == "S3_TC028_DISPLAY_DRYRUN")
assert template["templateStatus"] == "DISABLED"
agents = {a["deviceCode"]: a for a in api("/device-agents?page=1&size=100")["content"]}
primary, backup = agents["SIM_F2_DISPLAY"], agents["SIM_F2_FLIGHT"]
assert all(a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE" and
           a["workStatus"] == "IDLE" and a["currentTaskId"] is None for a in (primary, backup))
device = api("/devices/SIM_F2_DISPLAY")
simulator = device["accessEndpoint"] + "/device-api/v1"
secret = local.secrets()["SIM_F2_DISPLAY"]
out = stage / "evidence" / ("TC-052-concurrent-claim-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "templateId": template["id"],
      "primaryAgent": primary, "backupAgent": backup, "restore": {}}
active = []
delay_changed = False


def start(agent):
    return api(f"/baseline-templates/{template['id']}/dry-run", "POST",
               {"inputParams": {}, "simulatedDevices": [
                   {"stepSeq": 1, "agentId": agent["agentId"]}]})


def commands(task_id):
    return db.query(db.source, "SELECT agent_code,command_type,command_status,command_id "
                    f"FROM tip_stage2_v14.device_commands WHERE task_id={task_id} ORDER BY id").splitlines()


try:
    updated = api(f"/baseline-templates/{template['id']}", "PUT",
                  {"inputParams": template["inputParams"], "steps": template["steps"]})
    ev["templateDraft"] = {key: updated[key] for key in ("templateVersion", "templateStatus")}
    ev["delayMs"] = local.request(simulator + "/control/delay?milliseconds=45000",
                                  "POST", token=secret)["milliseconds"]
    delay_changed = True
    first = start(primary)
    active.append(first["taskId"])
    ev["first"] = {"start": first}
    deadline = time.monotonic() + 18
    while time.monotonic() < deadline:
        busy = api("/device-agents/" + primary["agentId"])
        if busy["workStatus"] == "BUSY" and busy["currentTaskId"] == first["taskId"]:
            break
        time.sleep(0.2)
    assert busy["workStatus"] == "BUSY" and busy["currentTaskId"] == first["taskId"]
    ev["first"]["agentAtBusy"] = busy
    ev["first"]["commandsAtBusy"] = commands(first["taskId"])
    before = int(db.query(db.source, "SELECT count(*) FROM tip_stage2_v14.tasks"))
    try:
        ev["sameAgentStart"] = start(primary)
    except RuntimeError as error:
        ev["sameAgentError"] = str(error)
    ev["taskCountBeforeSecond"] = before
    ev["taskCountAfterSecond"] = int(db.query(db.source, "SELECT count(*) FROM tip_stage2_v14.tasks"))
    ev["agentAfterSecond"] = api("/device-agents/" + primary["agentId"])
    ev["first"]["commandsAfterSecond"] = commands(first["taskId"])
    alternative = start(backup)
    active.append(alternative["taskId"])
    ev["backup"] = {"start": alternative, "agent": api("/device-agents/" + backup["agentId"]),
                    "commands": commands(alternative["taskId"])}
finally:
    for task_id in active:
        try:
            ev["restore"][str(task_id)] = api(
                f"/baseline-templates/{template['id']}/dry-runs/{task_id}/cancel", "POST")
        except Exception as error:
            ev["restore"][str(task_id) + "Error"] = str(error)
    if delay_changed:
        ev["restore"]["delayMs"] = local.request(simulator + "/control/delay?milliseconds=1000",
                                                  "POST", token=secret)["milliseconds"]
    ev["restore"]["template"] = api(f"/baseline-templates/{template['id']}/disable", "POST")
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        current = [a for a in api("/device-agents?page=1&size=100")["content"]
                   if a["deviceCode"].startswith("SIM_F2_")]
        if len(current) == 6 and all(a["onlineStatus"] == "ONLINE" and
            a["workStatus"] == "IDLE" and a["currentTaskId"] is None for a in current):
            break
        time.sleep(0.5)
    ev["restore"]["agents"] = current
    ev["restore"]["taskStatuses"] = {str(i): db.query(db.source,
        f"SELECT status FROM tip_stage2_v14.tasks WHERE id={i}") for i in active}
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": out.name, "firstId": ev["first"]["start"]["taskId"],
                  "sameAgentError": ev.get("sameAgentError"),
                  "secondCreated": ev["taskCountAfterSecond"] - ev["taskCountBeforeSecond"],
                  "backupId": ev["backup"]["start"]["taskId"],
                  "restored": all(a["workStatus"] == "IDLE" for a in ev["restore"]["agents"])},
                 ensure_ascii=False))
