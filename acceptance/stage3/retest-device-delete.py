"""TC-010.S3: idle device deletion, agent archive and operation audit."""
import importlib.util
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("配置管理员")
code = "S3_TC010_DELETE_B"
fixture = dict(local.load(local.FIXTURES / "devices.json")[0])
fixture.update(deviceCode=code, deviceName="阶段三临时删除航显",
               accessEndpoint="http://127.0.0.1:8191", accessCredentialRef="S3-TC010-ONLY",
               remark="阶段三删除与留痕测试；虚构档案")
fixture.pop("capabilities")
out = stage / "evidence" / (
    "TC-010-device-delete-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
assert all(row["deviceCode"] != code for row in api("/devices?page=1&size=100")["content"])
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "deviceCode": code, "cleanup": {}}
created = False
pid = None
try:
    ev["createdDevice"] = api("/devices", "POST", fixture)
    created = True
    token = api("/devices/" + code + "/device-token/rotate", "POST")["accessToken"]
    local.start_simulator(fixture, token)
    pid = local.load(local.LOCAL / "processes.json")[code]["pid"]
    ev["connectionTest"] = api("/devices/" + code + "/connection-test", "POST")
    ev["createdAgent"] = api("/device-agents", "POST", {"deviceCode": code})
    agent_id = ev["createdAgent"]["agentId"]
    ev["agentBeforeDelete"] = api("/device-agents/" + agent_id)
    original = api("/devices/" + code)
    ev["taskIdBeforeDelete"] = ev["agentBeforeDelete"].get("currentTaskId")
    ev["modifiedDevice"] = api("/devices/" + code, "PUT", {
        "deviceName": original["deviceName"], "areaCode": original["areaCode"],
        "positionX": original["positionX"], "positionY": original["positionY"],
        "accessEndpoint": original["accessEndpoint"], "accessCredentialRef": "",
        "statusReportInterval": original["statusReportInterval"],
        "remark": "阶段三删除前已修改备注；虚构档案"})
    api("/devices/" + code + "/status", "POST", {"status": "INACTIVE"})
    ev["afterDisable"] = {"deviceStatus": api("/devices/" + code)["deviceStatus"],
                           "agentStatus": api("/device-agents/" + agent_id)["agentStatus"]}
    api("/devices/" + code + "/status", "POST", {"status": "ACTIVE"})
    ev["afterEnable"] = {"deviceStatus": api("/devices/" + code)["deviceStatus"],
                          "agentStatus": api("/device-agents/" + agent_id)["agentStatus"]}
    # The idle, disabled agent remains bound to the active device and is archived on deletion.
    node = "C:/Users/savy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
    environment = os.environ.copy()
    environment["PLAYWRIGHT_CORE_PATH"] = (
        "C:/Users/savy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright-core")
    browser = subprocess.run([node, str(stage / "retest-device-delete-ui.cjs"), code],
                             cwd=root, env=environment, capture_output=True, text=True, timeout=90)
    ev["browserExitCode"] = browser.returncode
    ev["browserOutput"] = browser.stdout.strip() if browser.returncode == 0 else browser.stderr.strip()[-500:]
    if browser.returncode == 0:
        ev["afterConfirmDevice"] = api("/devices/" + code)
        ev["afterConfirmAgent"] = api("/device-agents/" + agent_id)
        ev["activeListContainsDevice"] = any(row["deviceCode"] == code
            for row in api("/devices?page=1&size=100")["content"])
    logs = api("/operation-logs?page=1&size=100")["content"]
    ev["operationLogs"] = [row for row in logs if code in (row.get("operationTarget") or "")
                           or agent_id in (row.get("operationTarget") or "")]
finally:
    if created:
        try:
            if api("/devices/" + code)["deviceStatus"] != "DELETED":
                api("/devices/" + code, "DELETE")
            ev["cleanup"]["deviceStatus"] = api("/devices/" + code)["deviceStatus"]
        except Exception as error:
            ev["cleanup"]["deviceError"] = str(error)
    if pid is not None:
        probe = subprocess.run(["powershell", "-NoProfile", "-Command",
            f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"],
            capture_output=True, text=True)
        if "device-simulator-runtime.jar" in probe.stdout:
            stopped = subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                                     capture_output=True, text=True)
            ev["cleanup"]["simulatorStopped"] = stopped.returncode == 0
        else:
            ev["cleanup"]["simulatorStopped"] = False
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(json.dumps({"evidence": str(out), "browserExitCode": ev.get("browserExitCode"),
                  "afterConfirmStatus": ev.get("afterConfirmDevice", {}).get("deviceStatus"),
                  "afterConfirmAgentStatus": ev.get("afterConfirmAgent", {}).get("agentStatus"),
                  "operationTypes": [row["operationType"] for row in ev.get("operationLogs", [])],
                  "cleanup": ev["cleanup"]}, ensure_ascii=False))
