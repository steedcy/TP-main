"""TC-093: add a same-type simulator, connect it, and execute an existing step."""
import hashlib
import importlib.util
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("配置管理员")
operator = local.API("运行操作员")
code = "S3_TC093_DISPLAY_C"
port = 8195
fixture = dict(local.load(local.FIXTURES / "devices.json")[0])
fixture.update(deviceCode=code, deviceName="阶段三临时同类航显",
               accessEndpoint=f"http://127.0.0.1:{port}",
               accessCredentialRef="S3-TC093-ONLY",
               remark="阶段三同类设备新增与现有任务能力调用；虚构档案")
fixture.pop("capabilities")
template = next(x for x in api("/baseline-templates") if x["templateName"] == "S3_TC028_DISPLAY_DRYRUN")
assert template["templateStatus"] == "DISABLED" and len(template["steps"]) == 1
assert template["steps"][0]["capabilityType"] == "CAP_INFO_DISPLAY"
assert not any(x["deviceCode"] == code for x in api("/devices?page=1&size=100")["content"])
agents = [x for x in api("/device-agents?page=1&size=100")["content"] if x["deviceCode"].startswith("SIM_F2_")]
assert len(agents) == 6 and all(x["onlineStatus"] == "ONLINE" and x["workStatus"] == "IDLE" for x in agents)
jar = root / "simulator" / "target" / "device-simulator-runtime.jar"
assert jar.exists(), jar
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
source_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "deviceCode": code, "existingTemplateId": template["id"],
      "templateVersion": template["templateVersion"], "sourceHeadBefore": source_head,
      "simulatorJarShaBefore": sha(jar), "originalSixOnlineIdle": True, "cleanup": {}}
out = stage / "evidence" / ("TC-093-same-type-new-device-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
created = False
pid = None
task_id = None
try:
    ev["device"] = api("/devices", "POST", fixture)
    created = True
    token = api("/devices/" + code + "/device-token/rotate", "POST")["accessToken"]
    local.start_simulator(fixture, token)
    pid = local.load(local.LOCAL / "processes.json")[code]["pid"]
    ev["connectionTest"] = api("/devices/" + code + "/connection-test", "POST")
    ev["agentCreated"] = api("/device-agents", "POST", {"deviceCode": code})
    agent_id = ev["agentCreated"]["agentId"]
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        agent = api("/device-agents/" + agent_id)
        if agent["onlineStatus"] == "ONLINE":
            break
        time.sleep(.4)
    ev["agentBeforeTask"] = agent
    source_cap = next(x for x in api("/devices/SIM_F2_DISPLAY/capabilities")
                      if x["capabilityCode"] == "CAP_INFO_DISPLAY")
    cap_code = "S3_TC093_INFO_C"
    cap_path = "/devices/" + code + "/capabilities"
    ev["capabilityCreated"] = api(cap_path, "POST", {
        "capabilityCode": cap_code, "capabilityName": "阶段三新增航显信息发布",
        "capabilityType": "CAP_INFO_DISPLAY", "inputParams": source_cap["inputParams"],
        "outputParams": source_cap["outputParams"], "applicableCondition": "F2",
        "capabilityDescription": "阶段三临时同类能力"})
    ev["capabilityTested"] = api(cap_path + "/" + cap_code + "/test", "POST")
    ev["capabilityEnabled"] = api(cap_path + "/" + cap_code + "/status", "POST",
                                   {"status": "ENABLED"})
    ev["preparedExistingTemplate"] = api(
        f"/baseline-templates/{template['id']}", "PUT",
        {"inputParams": template["inputParams"], "steps": template["steps"]})
    started = api(f"/baseline-templates/{template['id']}/dry-run", "POST",
                  {"inputParams": {}, "simulatedDevices": [
                      {"stepSeq": 1, "agentId": agent_id}]})
    task_id = started["taskId"]
    ev["started"] = started
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        task = operator(f"/tasks/{task_id}")
        if task["status"] in ("COMPLETED", "FAILED", "PENDING_MANUAL"):
            break
        time.sleep(.4)
    ev["task"] = task
    ev["assignments"] = operator(f"/tasks/{task_id}/step-assignments")
    ev["commands"] = [x for x in api(f"/simulators/{code}/commands") if x["taskId"] == task_id]
    ev["events"] = operator(f"/tasks/{task_id}/events")
    ev["agentAfterTask"] = api("/device-agents/" + agent_id)
finally:
    if task_id is not None:
        try:
            status = operator(f"/tasks/{task_id}")["status"]
            if status in ("PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT", "DOWNGRADING", "EXECUTING"):
                ev["cleanup"]["cancel"] = api(
                    f"/baseline-templates/{template['id']}/dry-runs/{task_id}/cancel", "POST")
        except Exception as error:
            ev["cleanup"]["cancelError"] = str(error)
    if created:
        try:
            api("/devices/" + code, "DELETE")
            ev["cleanup"]["deviceStatus"] = api("/devices/" + code)["deviceStatus"]
        except Exception as error:
            ev["cleanup"]["deviceError"] = str(error)
    try:
        ev["cleanup"]["templateDisable"] = api(
            f"/baseline-templates/{template['id']}/disable", "POST")
    except Exception as error:
        ev["cleanup"]["templateDisableError"] = str(error)
    if pid is not None:
        proc = subprocess.run(["powershell", "-NoProfile", "-Command",
            f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"],
            capture_output=True, text=True)
        if "device-simulator-runtime.jar" in proc.stdout:
            ev["cleanup"]["simulatorStopped"] = subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"], capture_output=True).returncode == 0
        else:
            ev["cleanup"]["simulatorStopped"] = False
    ev["sourceHeadAfter"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    ev["simulatorJarShaAfter"] = sha(jar)
    ev["cleanup"]["existingTemplateStillDisabled"] = api(
        f"/baseline-templates/{template['id']}")["templateStatus"] == "DISABLED"
    ev["cleanup"]["originalSixOnlineIdle"] = all(
        x["onlineStatus"] == "ONLINE" and x["workStatus"] == "IDLE" and x["currentTaskId"] is None
        for x in api("/device-agents?page=1&size=100")["content"] if x["deviceCode"].startswith("SIM_F2_"))
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": out.name, "taskId": task_id,
                  "status": ev.get("task", {}).get("status"), "cleanup": ev["cleanup"]}, ensure_ascii=False))
