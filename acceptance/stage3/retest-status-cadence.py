"""TC-014: observe two automatic 15-second reports from a disposable simulator."""
import importlib.util
import json
import os
import shutil
import socket
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
code, port = "S3_TC014_CADENCE", 8201
with socket.socket() as probe:
    assert probe.connect_ex(("127.0.0.1", port)) != 0, "fixture port occupied"
assert all(a["deviceCode"] != code for a in api("/devices?page=1&size=100")["content"])
fixture = dict(local.load(local.FIXTURES / "devices.json")[0])
fixture.update(deviceCode=code, deviceName="阶段三十五秒上报仿真航显",
               areaCode="F2_CADENCE", positionX=835, positionY=4240,
               accessEndpoint=f"http://127.0.0.1:{port}",
               accessCredentialRef="S3-TC014-CADENCE-ONLY", statusReportInterval=15,
               remark="仅验证自动上报周期；虚构测试数据")
fixture.pop("capabilities")
out = stage / "evidence" / ("TC-014-status-cadence-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "deviceCode": code,
      "configuredIntervalSeconds": 15, "reports": [], "cleanup": {}}
created = False
proc = None
try:
    ev["createdDevice"] = {k: v for k, v in api("/devices", "POST", fixture).items()
                           if k in ("deviceCode", "statusReportInterval", "areaCode", "deviceStatus")}
    created = True
    token = api("/devices/" + code + "/device-token/rotate", "POST")["accessToken"]
    environment = local.env()
    environment.update(SIMULATOR_PORT=str(port), SIMULATOR_DEVICE_CODE=code,
        SIMULATED_DEVICE_TYPE="SMART_DISPLAY", SIMULATOR_DEVICE_TOKEN=token,
        SIMULATOR_X="835", SIMULATOR_Y="4240", SIMULATOR_ZONE="F2_CADENCE",
        SIMULATOR_HEARTBEAT_INTERVAL_SECONDS="15", SIMULATOR_EXECUTION_DELAY_MS="1000")
    jar = root / "simulator/target/device-simulator-runtime.jar"
    assert jar.exists()
    log_path = root / ".local-test/S3_TC014_CADENCE.log"
    with log_path.open("ab", buffering=0) as log:
        proc = subprocess.Popen([shutil.which("java"), "-Xms32m", "-Xmx128m",
            "-XX:MaxMetaspaceSize=128m", "-XX:+UseSerialGC", "-jar", str(jar)],
            cwd=root, env=environment, stdout=log, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW)
    ev["simulatorPid"] = proc.pid
    base = fixture["accessEndpoint"] + "/device-api/v1"
    ev["health"] = {k: v for k, v in local.wait_health(base + "/health?nonce=stage3-cadence", token).items()
                    if k in ("deviceCode", "onlineStatus", "workStatus", "location")}
    ev["connectionTest"] = api("/devices/" + code + "/connection-test", "POST")
    assert ev["connectionTest"]["result"] == "PASSED"
    agent = api("/device-agents", "POST", {"deviceCode": code})
    agent_code = agent["agentId"]
    ev["agentCode"] = agent_code
    ev["binding"] = local.request(base + "/agents/" + agent_code + "/binding", "POST", {
        "deviceCode": code, "agentCode": agent_code,
        "reportUrl": "http://127.0.0.1:8080/device-api/v1/agents/" + agent_code + "/report",
        "heartbeatIntervalSeconds": 15, "heartbeatTimeoutSeconds": 30}, token)
    deadline = time.monotonic() + 48
    last = agent.get("lastReportedAt")
    while time.monotonic() < deadline and len(ev["reports"]) < 2:
        now = api("/device-agents/" + agent_code)
        stamp = now.get("lastReportedAt")
        if stamp and stamp != last:
            last = stamp
            ev["reports"].append({"observedAt": datetime.now(timezone.utc).isoformat(),
                "lastReportedAt": stamp, "onlineStatus": now["onlineStatus"],
                "workStatus": now["workStatus"],
                "device": {k: api("/devices/" + code)[k] for k in ("areaCode", "positionX", "positionY")}})
        time.sleep(0.4)
    if len(ev["reports"]) == 2:
        first, second = (datetime.fromisoformat(r["lastReportedAt"]) for r in ev["reports"])
        ev["reportIntervalObservedSeconds"] = round((second - first).total_seconds(), 3)
finally:
    if created:
        try:
            api("/devices/" + code, "DELETE")
            ev["cleanup"]["deviceStatus"] = api("/devices/" + code)["deviceStatus"]
        except Exception as error:
            ev["cleanup"]["deviceError"] = str(error)
    if proc is not None:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=8)
        ev["cleanup"]["simulatorExitCode"] = proc.returncode
    ev["finishedAt"] = datetime.now(timezone.utc).isoformat()
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": out.name, "reportCount": len(ev["reports"]),
                  "intervalSeconds": ev.get("reportIntervalObservedSeconds"),
                  "cleanup": ev["cleanup"]}, ensure_ascii=False))
