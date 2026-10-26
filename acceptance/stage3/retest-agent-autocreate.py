"""TC-011.S1 and SRS_F003.R01: fresh agent lifecycle and duplicate code."""
import importlib.util
import json
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("配置管理员")
code = "S3_TC011_AGENT"
fixture = dict(local.load(local.FIXTURES / "devices.json")[0])
fixture.update(deviceCode=code, deviceName="阶段三临时代理创建航显",
               accessEndpoint="http://127.0.0.1:8191", accessCredentialRef="S3-TC011-ONLY",
               remark="代理创建与唯一编码复测；虚构档案")
fixture.pop("capabilities")
out = Path(__file__).parent / "evidence" / (
    "TC-011-agent-autocreate-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")


def agent_list():
    return [row for row in api("/device-agents?page=1&size=100")["content"]
            if row["deviceCode"] == code]


def raw_duplicate():
    request = urllib.request.Request(local.BASE + "/devices", method="POST",
        data=json.dumps(fixture, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + api.token})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read()).get("message")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read()).get("message")


assert not agent_list()
assert all(row["deviceCode"] != code for row in api("/devices?page=1&size=100")["content"])
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "deviceCode": code, "cleanup": {}}
created = False
simulator_pid = None
try:
    ev["createdDevice"] = api("/devices", "POST", fixture)["deviceCode"]
    created = True
    ev["initialConnectionStatus"] = api("/devices/" + code)["connectionTestStatus"]
    ev["duplicateHttpStatus"], ev["duplicateMessage"] = raw_duplicate()
    ev["duplicateCount"] = sum(1 for row in api("/devices?page=1&size=100")["content"]
                               if row["deviceCode"] == code)
    token = api("/devices/" + code + "/device-token/rotate", "POST")["accessToken"]
    local.start_simulator(fixture, token)
    simulator_pid = local.load(local.LOCAL / "processes.json")[code]["pid"]
    ev["testResponse"] = api("/devices/" + code + "/connection-test", "POST")
    ev["agentsAfterSuccessfulTest"] = agent_list()
    ev["firstExplicitCreate"] = api("/device-agents", "POST", {"deviceCode": code})
    ev["agentsAfterFirstCreate"] = agent_list()
    ev["secondExplicitCreate"] = api("/device-agents", "POST", {"deviceCode": code})
    ev["agentsAfterSecondCreate"] = agent_list()
finally:
    if created:
        try:
            api("/devices/" + code, "DELETE")
            ev["cleanup"]["deviceStatus"] = api("/devices/" + code)["deviceStatus"]
            ev["cleanup"]["agentsAfterDelete"] = agent_list()
        except Exception as error:
            ev["cleanup"]["error"] = str(error)
    if simulator_pid is not None:
        probe = subprocess.run(["powershell", "-NoProfile", "-Command",
            f"(Get-CimInstance Win32_Process -Filter 'ProcessId={simulator_pid}').CommandLine"],
            capture_output=True, text=True)
        if "device-simulator-runtime.jar" in probe.stdout:
            stop = subprocess.run(["taskkill", "/PID", str(simulator_pid), "/F"],
                                  capture_output=True, text=True)
            ev["cleanup"]["simulatorStopped"] = stop.returncode == 0
        else:
            ev["cleanup"]["simulatorStopped"] = False
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(json.dumps({"evidence": str(out), "duplicateStatus": ev.get("duplicateHttpStatus"),
                  "agentsAfterTest": len(ev.get("agentsAfterSuccessfulTest", [])),
                  "afterTwoExplicitCreates": len(ev.get("agentsAfterSecondCreate", [])),
                  "cleanup": {key: value for key, value in ev["cleanup"].items()
                              if key != "agentsAfterDelete"}}, ensure_ascii=False))
