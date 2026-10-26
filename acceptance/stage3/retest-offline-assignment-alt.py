"""R04 follow-up: reject an offline display, execute on a second eligible display."""
import importlib.util
import json
import re
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


local = module("local", root / "scripts/local-test-environment.py")
db = module("db", root / "acceptance/stage2/db-isolation.py")
api = local.API("配置管理员")
code, alt, cap_code = "SIM_F2_DISPLAY", "S3_TC014_ALT_DISPLAY_B", "S3_TC014_ALT_INFO_B"
template = next(t for t in api("/baseline-templates")
                if t["templateName"] == "S3_TC028_DISPLAY_DRYRUN")
assert template["templateStatus"] == "DISABLED"
assert all(d["deviceCode"] != alt for d in api("/devices?page=1&size=100")["content"])
source = api("/devices/" + code)
agent = next(a for a in api("/device-agents?page=1&size=100")["content"]
             if a["deviceCode"] == code)
assert agent["onlineStatus"] == "ONLINE" and agent["workStatus"] == "IDLE"
assert agent["currentTaskId"] is None and re.fullmatch(r"AGT-[A-Z0-9]{8}", agent["agentId"])
source_cap = next(c for c in api("/devices/" + code + "/capabilities")
                  if c["capabilityType"] == "CAP_INFO_DISPLAY" and c["capabilityStatus"] == "ENABLED")
fixture = dict(local.load(local.FIXTURES / "devices.json")[0])
fixture.update(deviceCode=alt, deviceName="阶段三临时备用航显",
               positionX=850, positionY=4220,
               accessEndpoint="http://127.0.0.1:8203",
               accessCredentialRef="S3-TC014-ALT-ONLY",
               remark="离线分配保护的同类型在线候选；虚构数据")
fixture.pop("capabilities")
out = stage / "evidence" / ("TC-014-offline-assignment-alt-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
secret = local.secrets()[code]
heartbeat = source["accessEndpoint"] + "/device-api/v1/control/heartbeat"


def count(sql):
    return int(db.query(db.source, sql))


def raw(selected):
    payload = {"inputParams": {}, "simulatedDevices": [{"stepSeq": 1, "agentId": selected}]}
    req = urllib.request.Request(local.BASE + f"/baseline-templates/{template['id']}/dry-run",
        method="POST", data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + api.token})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return {"httpStatus": response.status, "payload": payload,
                    "response": json.loads(response.read().decode("utf-8"))}
    except urllib.error.HTTPError as error:
        return {"httpStatus": error.code, "payload": payload,
                "response": json.loads(error.read().decode("utf-8"))}


ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "offlineDevice": code,
      "alternativeDevice": alt, "templateId": template["id"],
      "templateVersionBefore": template["templateVersion"],
      "beforeTaskCount": count("SELECT count(*) FROM tip_stage2_v14.tasks"),
      "beforeOfflineCommandCount": count("SELECT count(*) FROM tip_stage2_v14.device_commands "
        "WHERE agent_code='" + agent["agentId"] + "'"), "restore": {}}
created = False
simulator_pid = None
stopped = False
task_id = None
alt_agent = None
try:
    ev["createdDevice"] = api("/devices", "POST", fixture)["deviceCode"]
    created = True
    token = api("/devices/" + alt + "/device-token/rotate", "POST")["accessToken"]
    local.start_simulator(fixture, token)
    simulator_pid = local.load(local.LOCAL / "processes.json")[alt]["pid"]
    ev["connectionTest"] = api("/devices/" + alt + "/connection-test", "POST")
    assert ev["connectionTest"]["result"] == "PASSED"
    alt_agent = api("/device-agents", "POST", {"deviceCode": alt})["agentId"]
    ev["alternativeAgentCode"] = alt_agent
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        current = api("/device-agents/" + alt_agent)
        if current["onlineStatus"] == "ONLINE":
            break
        time.sleep(1)
    ev["alternativeAgentBefore"] = current
    assert current["onlineStatus"] == "ONLINE" and current["workStatus"] == "IDLE"
    cap_path = "/devices/" + alt + "/capabilities"
    created_cap = api(cap_path, "POST", {"capabilityCode": cap_code,
        "capabilityName": "阶段三备用航显展示能力", "capabilityType": "CAP_INFO_DISPLAY",
        "inputParams": source_cap["inputParams"], "outputParams": source_cap["outputParams"],
        "applicableCondition": "F2", "capabilityDescription": "临时同类型候选"})
    ev["alternativeCapabilityCreated"] = created_cap["capabilityStatus"]
    tested = api(cap_path + "/" + cap_code + "/test", "POST")
    ev["alternativeCapabilityTest"] = {k: tested.get(k) for k in
        ("capabilityStatus", "testResult", "lastTestAt")}
    api(cap_path + "/" + cap_code + "/status", "POST", {"status": "ENABLED"})
    ev["alternativeCapabilityEnabled"] = next(c["capabilityStatus"] for c in api(cap_path)
                                               if c["capabilityCode"] == cap_code)
    assert ev["alternativeCapabilityEnabled"] == "ENABLED"
    updated = api(f"/baseline-templates/{template['id']}", "PUT",
        {"inputParams": template["inputParams"], "steps": template["steps"]})
    ev["templateDraft"] = {k: updated[k] for k in ("templateVersion", "templateStatus")}
    local.request(heartbeat + "?value=false", "POST", token=secret)
    stopped = True
    deadline = time.monotonic() + 55
    while time.monotonic() < deadline:
        offline = api("/device-agents/" + agent["agentId"])
        if offline["onlineStatus"] == "OFFLINE":
            break
        time.sleep(1)
    ev["offlineAgentAtSelection"] = offline
    assert offline["onlineStatus"] == "OFFLINE"
    ev["alternativeAgentAtSelection"] = api("/device-agents/" + alt_agent)
    ev["offlineSelection"] = raw(agent["agentId"])
    ev["taskCountAfterOfflineReject"] = count("SELECT count(*) FROM tip_stage2_v14.tasks")
    ev["alternativeSelection"] = raw(alt_agent)
    if ev["alternativeSelection"]["httpStatus"] == 200:
        task_id = ev["alternativeSelection"]["response"]["data"]["taskId"]
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            result = api(f"/baseline-templates/{template['id']}/dry-runs/{task_id}")
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
    ev["afterTaskCount"] = count("SELECT count(*) FROM tip_stage2_v14.tasks")
    ev["afterOfflineCommandCount"] = count("SELECT count(*) FROM tip_stage2_v14.device_commands "
        "WHERE agent_code='" + agent["agentId"] + "'")
finally:
    if task_id is not None:
        status = db.query(db.source,
            "SELECT status FROM tip_stage2_v14.tasks WHERE id=" + str(task_id))
        if status in ("PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT", "DOWNGRADING", "EXECUTING"):
            try:
                ev["restore"]["cancelResult"] = api(
                    f"/baseline-templates/{template['id']}/dry-runs/{task_id}/cancel", "POST")
            except Exception as error:
                ev["restore"]["cancelError"] = str(error)
    if stopped:
        ev["restore"]["heartbeat"] = local.request(heartbeat + "?value=true", "POST", token=secret)
    try:
        api(f"/baseline-templates/{template['id']}/disable", "POST")
        ev["restore"]["templateStatus"] = api(
            f"/baseline-templates/{template['id']}")["templateStatus"]
    except Exception as error:
        ev["restore"]["templateError"] = str(error)
    if created:
        try:
            api("/devices/" + alt, "DELETE")
            ev["restore"]["alternativeDeviceStatus"] = api("/devices/" + alt)["deviceStatus"]
        except Exception as error:
            ev["restore"]["alternativeDeviceError"] = str(error)
    if simulator_pid is not None:
        probe = subprocess.run(["powershell", "-NoProfile", "-Command",
            f"(Get-CimInstance Win32_Process -Filter 'ProcessId={simulator_pid}').CommandLine"],
            capture_output=True, encoding="utf-8", errors="replace")
        if "device-simulator-runtime.jar" in probe.stdout:
            stop = subprocess.run(["taskkill", "/PID", str(simulator_pid), "/F"],
                capture_output=True, encoding="utf-8", errors="replace")
            ev["restore"]["alternativeSimulatorStopped"] = stop.returncode == 0
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        restored = api("/device-agents/" + agent["agentId"])
        if restored["onlineStatus"] == "ONLINE":
            break
        time.sleep(1)
    ev["restore"]["originalAgent"] = restored
    ev["finishedAt"] = datetime.now(timezone.utc).isoformat()
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": out.name,
    "offlineSelectionStatus": ev.get("offlineSelection", {}).get("httpStatus"),
    "alternativeSelectionStatus": ev.get("alternativeSelection", {}).get("httpStatus"),
    "taskId": task_id, "taskStatus": ev.get("taskStatus"),
    "commands": ev.get("commandRows"), "restored": ev["restore"]["originalAgent"]["onlineStatus"]},
    ensure_ascii=False))
