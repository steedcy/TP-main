"""TC-014.S2/R04: reject offline selection, dispatch an equivalent online simulator."""
import importlib.util
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    item = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(item)
    return item


local = module("local", root / "scripts/local-test-environment.py")
db = module("db", root / "acceptance/stage2/db-isolation.py")
config = local.API("配置管理员")
code, alternative = "SIM_F2_DISPLAY", "SIM_F2_FLIGHT"
agents = {a["deviceCode"]: a for a in config("/device-agents?page=1&size=100")["content"]}
assert all(agents[c]["agentStatus"] == "ENABLED" and agents[c]["onlineStatus"] == "ONLINE"
           and agents[c]["workStatus"] == "IDLE" and agents[c]["currentTaskId"] is None
           for c in (code, alternative))
assert next(cap for cap in config("/devices/" + alternative + "/capabilities")
            if cap["capabilityType"] == "CAP_INFO_DISPLAY")["capabilityStatus"] == "ENABLED"
template = next(t for t in config("/baseline-templates")
                if t["templateName"] == "S3_TC028_DISPLAY_DRYRUN")
assert template["templateStatus"] == "DISABLED" and len(template["steps"]) == 1
device = config("/devices/" + code)
secret = local.secrets()[code]
heartbeat_url = device["accessEndpoint"] + "/device-api/v1/control/heartbeat"
assert re.fullmatch(r"AGT-[A-Z0-9]{8}", agents[code]["agentId"])
assert re.fullmatch(r"AGT-[A-Z0-9]{8}", agents[alternative]["agentId"])
out = stage / "evidence" / ("TC-014-offline-assignment-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")


def agent(item):
    return config("/device-agents/" + agents[item]["agentId"])


def raw_dry_run(selected):
    path = f"/baseline-templates/{template['id']}/dry-run"
    payload = {"inputParams": {}, "simulatedDevices": [{"stepSeq": 1, "agentId": selected}]}
    req = urllib.request.Request(local.BASE + path, method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + config.token})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return {"httpStatus": response.status, "payload": payload,
                    "response": json.loads(response.read().decode("utf-8"))}
    except urllib.error.HTTPError as error:
        return {"httpStatus": error.code, "payload": payload,
                "response": json.loads(error.read().decode("utf-8"))}


def count_tasks():
    return int(db.query(db.source, "SELECT count(*) FROM tip_stage2_v14.tasks"))


def count_commands(agent_code):
    return int(db.query(db.source, "SELECT count(*) FROM tip_stage2_v14.device_commands "
        "WHERE agent_code='" + agent_code + "'"))


ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "templateId": template["id"],
      "templateVersionBefore": template["templateVersion"],
      "offlineAgentCode": agents[code]["agentId"],
      "alternativeAgentCode": agents[alternative]["agentId"],
      "beforeTaskCount": count_tasks(),
      "beforeOfflineAgentCommandCount": count_commands(agents[code]["agentId"]),
      "restore": {}}
heartbeat_stopped = False
task_id = None
try:
    updated = config(f"/baseline-templates/{template['id']}", "PUT",
        {"inputParams": template["inputParams"], "steps": template["steps"]})
    ev["templateDraft"] = {k: updated[k] for k in ("templateVersion", "templateStatus")}
    local.request(heartbeat_url + "?value=false", "POST", token=secret)
    heartbeat_stopped = True
    deadline = time.monotonic() + 55
    while time.monotonic() < deadline and agent(code)["onlineStatus"] != "OFFLINE":
        time.sleep(1)
    ev["offlineAgentAtSelection"] = agent(code)
    ev["alternativeAgentAtSelection"] = agent(alternative)
    assert ev["offlineAgentAtSelection"]["onlineStatus"] == "OFFLINE"
    assert ev["alternativeAgentAtSelection"]["onlineStatus"] == "ONLINE"
    ev["offlineSelection"] = raw_dry_run(agents[code]["agentId"])
    ev["taskCountAfterOfflineSelection"] = count_tasks()
    ev["offlineAgentCommandCountAfterReject"] = count_commands(agents[code]["agentId"])
    ev["alternativeSelection"] = raw_dry_run(agents[alternative]["agentId"])
    if ev["alternativeSelection"]["httpStatus"] == 200:
        task_id = ev["alternativeSelection"]["response"]["data"]["taskId"]
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            result = config(f"/baseline-templates/{template['id']}/dry-runs/{task_id}")
            if result["result"] not in ("RUNNING", "IN_PROGRESS", "PENDING"):
                break
            time.sleep(0.5)
        ev["dryRunResult"] = result
        ev["taskStatus"] = db.query(db.source,
            "SELECT status FROM tip_stage2_v14.tasks WHERE id=" + str(task_id))
        ev["selectionRows"] = db.query(db.source,
            "SELECT a.agent_code,s.step_seq FROM tip_stage2_v14.dry_run_device_selections s "
            "JOIN tip_stage2_v14.device_agents a ON a.id=s.device_agent_id "
            "WHERE s.task_id=" + str(task_id)).splitlines()
        ev["commandRows"] = db.query(db.source,
            "SELECT agent_code,command_type,command_status FROM tip_stage2_v14.device_commands "
            "WHERE task_id=" + str(task_id) + " ORDER BY id").splitlines()
    ev["afterTaskCount"] = count_tasks()
    ev["afterOfflineAgentCommandCount"] = count_commands(agents[code]["agentId"])
finally:
    if task_id is not None:
        status = db.query(db.source,
            "SELECT status FROM tip_stage2_v14.tasks WHERE id=" + str(task_id))
        if status in ("PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT", "DOWNGRADING", "EXECUTING"):
            try:
                ev["restore"]["cancelResult"] = config(
                    f"/baseline-templates/{template['id']}/dry-runs/{task_id}/cancel", "POST")
            except Exception as error:
                ev["restore"]["cancelError"] = str(error)
    if heartbeat_stopped:
        ev["restore"]["heartbeat"] = local.request(heartbeat_url + "?value=true", "POST", token=secret)
    ev["restore"]["template"] = config(f"/baseline-templates/{template['id']}/disable", "POST")
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline and agent(code)["onlineStatus"] != "ONLINE":
        time.sleep(1)
    ev["restore"]["displayAgent"] = agent(code)
    ev["restore"]["alternativeAgent"] = agent(alternative)
    ev["finishedAt"] = datetime.now(timezone.utc).isoformat()
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": out.name,
    "offlineSelectionStatus": ev.get("offlineSelection", {}).get("httpStatus"),
    "alternativeSelectionStatus": ev.get("alternativeSelection", {}).get("httpStatus"),
    "taskId": task_id, "taskStatus": ev.get("taskStatus"),
    "commands": ev.get("commandRows"), "restored": ev["restore"]["displayAgent"]["onlineStatus"]},
    ensure_ascii=False))
