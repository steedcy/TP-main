"""TC-009.S1: create a fresh simulator dossier and complete its real handshake."""
import importlib.util
import json
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("配置管理员")
code = "S3_TC009_SUCCESS"
port = 8191
fixture = dict(local.load(local.FIXTURES / "devices.json")[0])
fixture.update(deviceCode=code, deviceName="阶段三临时连接成功航显",
               accessEndpoint=f"http://127.0.0.1:{port}",
               accessCredentialRef="S3-TC009-ONLY",
               remark="阶段三连接成功测试；虚构档案")
fixture.pop("capabilities")
out = Path(__file__).parent / "evidence" / (
    "TC-009-connection-success-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")


def raw_agent_create():
    request = urllib.request.Request(local.BASE + "/device-agents", method="POST",
        data=json.dumps({"deviceCode": code}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + api.token})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read()).get("message")
    except urllib.error.HTTPError as error:
        body = json.loads(error.read())
        return error.code, body.get("message")


assert all(row["deviceCode"] != code for row in api("/devices?page=1&size=100")["content"])
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "deviceCode": code, "endpointPort": port,
      "cleanup": {}}
created = False
launched_pid = None
try:
    saved = api("/devices", "POST", fixture)
    created = True
    ev["saved"] = {key: saved.get(key) for key in
                   ("deviceCode", "deviceTypeCode", "simulatedDeviceType", "deviceStatus",
                    "connectionTestStatus", "connectionTestResult", "accessEndpoint")}
    ev["untestedAgentCreateHttpStatus"], ev["untestedAgentCreateMessage"] = raw_agent_create()
    issued_token = api("/devices/" + code + "/device-token/rotate", "POST")["accessToken"]
    local.start_simulator(fixture, issued_token)
    launched_pid = local.load(local.LOCAL / "processes.json")[code]["pid"]
    ev["health"] = local.request(fixture["accessEndpoint"] +
        "/device-api/v1/health?nonce=stage3-tc009", token=issued_token)
    began = time.monotonic()
    ev["connectionTestResponse"] = api("/devices/" + code + "/connection-test", "POST")
    ev["clientElapsedMs"] = round((time.monotonic() - began) * 1000)
    checked = api("/devices/" + code)
    ev["checked"] = {key: checked.get(key) for key in
                     ("connectionTestStatus", "connectionTestResult", "connectionTestAt",
                      "lastConnectionTestAt", "deviceStatus")}
    agent = api("/device-agents", "POST", {"deviceCode": code})
    ev["createdAgent"] = {key: agent.get(key) for key in
                          ("agentId", "deviceCode", "agentStatus", "onlineStatus")}
    ev["agentListed"] = any(a["deviceCode"] == code and a["agentId"] == agent["agentId"]
        for a in api("/device-agents?page=1&size=100")["content"])
finally:
    if created:
        try:
            api("/devices/" + code, "DELETE")
            ev["cleanup"]["deviceStatus"] = api("/devices/" + code)["deviceStatus"]
        except Exception as error:
            ev["cleanup"]["deviceError"] = str(error)
    if launched_pid is not None:
        # Stop only the simulator spawned by this script, after confirming its identity.
        check = subprocess.run(["powershell", "-NoProfile", "-Command",
            f"(Get-CimInstance Win32_Process -Filter 'ProcessId={launched_pid}').CommandLine"],
            capture_output=True, text=True)
        command = check.stdout.strip()
        if "device-simulator-runtime.jar" in command and str(port) not in command:
            # Port is in the process environment, not argv; the PID was recorded at launch.
            subprocess.run(["taskkill", "/PID", str(launched_pid), "/F"],
                           capture_output=True, text=True)
            ev["cleanup"]["simulatorStopped"] = True
        else:
            ev["cleanup"]["simulatorStopped"] = False
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(json.dumps({"evidence": str(out), "initialStatus": ev.get("saved", {}).get("connectionTestStatus"),
                  "testResult": ev.get("connectionTestResponse", {}).get("result"),
                  "agentCreated": ev.get("agentListed"), "cleanup": ev["cleanup"]}, ensure_ascii=False))
