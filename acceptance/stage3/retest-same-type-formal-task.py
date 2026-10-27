"""TC-093.S2: route an actual oversize task to a newly configured display."""
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
config = local.API("配置管理员")
operator = local.API("运行操作员")
source = operator("/tasks/19")
assert source["status"] == "COMPLETED" and source["taskFamily"] == "OVERSIZE_BAGGAGE_HANDLING"
request = {key: source[key] for key in ("taskGoal", "taskFamily", "sceneParams")}
original = next(x for x in config("/device-agents?page=1&size=100")["content"]
                if x["deviceCode"] == "SIM_F2_DISPLAY")
assert original["agentStatus"] == "ENABLED" and original["onlineStatus"] == "ONLINE"
assert original["workStatus"] == "IDLE" and original["currentTaskId"] is None
others = [x for x in config("/device-agents?page=1&size=100")["content"]
          if x["deviceCode"].startswith("SIM_F2_")]
assert len(others) == 6 and all(x["onlineStatus"] == "ONLINE" and x["workStatus"] == "IDLE" for x in others)
code = "S3_TC093_DISPLAY_D"
cap_code = "S3_TC093_INFO_D"
port = 8196
fixture = dict(local.load(local.FIXTURES / "devices.json")[0])
fixture.update(deviceCode=code, deviceName="阶段三正式任务临时航显",
               accessEndpoint=f"http://127.0.0.1:{port}",
               accessCredentialRef="S3-TC093-D-ONLY",
               remark="阶段三同类设备正式任务调用；虚构档案")
fixture.pop("capabilities")
assert not any(x["deviceCode"] == code for x in config("/devices?page=1&size=100")["content"])
out = stage / "evidence" / ("TC-093-same-type-formal-task-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "sourceTaskId": 19, "request": request,
      "existingDisplayAgentBefore": original, "newDeviceCode": code, "cleanup": {}}
created = False
pid = None
task_id = None
disabled = False
try:
    ev["newDevice"] = config("/devices", "POST", fixture)
    created = True
    token = config("/devices/" + code + "/device-token/rotate", "POST")["accessToken"]
    local.start_simulator(fixture, token)
    pid = local.load(local.LOCAL / "processes.json")[code]["pid"]
    ev["connectionTest"] = config("/devices/" + code + "/connection-test", "POST")
    ev["newAgent"] = config("/device-agents", "POST", {"deviceCode": code})
    agent_id = ev["newAgent"]["agentId"]
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        agent = config("/device-agents/" + agent_id)
        if agent["onlineStatus"] == "ONLINE":
            break
        time.sleep(.4)
    ev["newAgentOnline"] = agent
    source_cap = next(x for x in config("/devices/SIM_F2_DISPLAY/capabilities")
                      if x["capabilityCode"] == "CAP_INFO_DISPLAY")
    path = "/devices/" + code + "/capabilities"
    ev["capabilityCreated"] = config(path, "POST", {
        "capabilityCode": cap_code, "capabilityName": "阶段三正式任务信息发布",
        "capabilityType": "CAP_INFO_DISPLAY", "inputParams": source_cap["inputParams"],
        "outputParams": source_cap["outputParams"], "applicableCondition": "F2",
        "capabilityDescription": "阶段三临时同类设备"})
    ev["capabilityTest"] = config(path + "/" + cap_code + "/test", "POST")
    config(path + "/" + cap_code + "/status", "POST", {"status": "ENABLED"})
    ev["capabilityEnabled"] = next(x for x in config(path) if x["capabilityCode"] == cap_code)
    config("/device-agents/" + original["agentId"] + "/disable", "POST", {"confirmed": True})
    disabled = True
    ev["existingDisplayDisabled"] = config("/device-agents/" + original["agentId"])
    ev["newAgentBeforeTask"] = config("/device-agents/" + agent_id)
    ev["submitted"] = operator("/tasks", "POST", request)
    task_id = ev["submitted"]["id"]
    deadline = time.monotonic() + 110
    while time.monotonic() < deadline:
        task = operator(f"/tasks/{task_id}")
        if task["status"] in ("COMPLETED", "FAILED", "PENDING_MANUAL"):
            break
        time.sleep(.8)
    ev["task"] = task
    ev["plans"] = operator(f"/tasks/{task_id}/plan-versions")
    ev["assignments"] = operator(f"/tasks/{task_id}/step-assignments")
    ev["events"] = operator(f"/tasks/{task_id}/events")
    ev["newDeviceCommands"] = [x for x in config(f"/simulators/{code}/commands")
                               if x["taskId"] == task_id]
finally:
    if task_id is not None:
        try:
            task = operator(f"/tasks/{task_id}")
            if task["status"] not in ("COMPLETED", "FAILED", "PENDING_MANUAL", "TERMINATED"):
                ev["cleanup"]["terminate"] = operator(f"/tasks/{task_id}/terminate", "POST",
                    {"reason": "阶段三试验清理"})
        except Exception as error:
            ev["cleanup"]["terminateError"] = str(error)
    if disabled:
        try:
            ev["cleanup"]["originalReenabled"] = config("/device-agents", "POST",
                {"deviceCode": "SIM_F2_DISPLAY"})
        except Exception as error:
            ev["cleanup"]["originalEnableError"] = str(error)
    if created:
        try:
            config("/devices/" + code, "DELETE")
            ev["cleanup"]["newDeviceStatus"] = config("/devices/" + code)["deviceStatus"]
        except Exception as error:
            ev["cleanup"]["newDeviceError"] = str(error)
    if pid is not None:
        ps = subprocess.run(["powershell", "-NoProfile", "-Command",
            f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"],
            capture_output=True, text=True)
        if "device-simulator-runtime.jar" in ps.stdout:
            ev["cleanup"]["simulatorStopped"] = subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"], capture_output=True).returncode == 0
        else:
            ev["cleanup"]["simulatorStopped"] = False
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        originals = [x for x in config("/device-agents?page=1&size=100")["content"]
                     if x["deviceCode"].startswith("SIM_F2_")]
        if len(originals) == 6 and all(x["agentStatus"] == "ENABLED" and
             x["onlineStatus"] == "ONLINE" and x["workStatus"] == "IDLE" and
             x["currentTaskId"] is None for x in originals):
            break
        time.sleep(.5)
    ev["cleanup"]["originalSixOnlineIdle"] = len(originals) == 6 and all(
        x["agentStatus"] == "ENABLED" and x["onlineStatus"] == "ONLINE" and
        x["workStatus"] == "IDLE" and x["currentTaskId"] is None for x in originals)
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": out.name, "taskId": task_id,
                  "status": ev.get("task", {}).get("status"),
                  "newDeviceCommandCount": len(ev.get("newDeviceCommands", [])),
                  "cleanup": {k: v for k, v in ev["cleanup"].items() if k != "originalReenabled"}},
                 ensure_ascii=False))
