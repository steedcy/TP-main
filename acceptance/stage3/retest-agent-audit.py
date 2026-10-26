"""TC-012.S3: observe create, disable, reenable and archive logs/events."""
import importlib.util
import json
import subprocess
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
api = local.API("配置管理员")
code = "S3_TC012_AUDIT"
fixture = dict(local.load(local.FIXTURES / "devices.json")[0])
fixture.update(deviceCode=code, deviceName="阶段三临时代理审计航显",
               accessEndpoint="http://127.0.0.1:8191", accessCredentialRef="S3-TC012-ONLY",
               remark="阶段三代理生命周期记录测试；虚构档案")
fixture.pop("capabilities")
out = stage / "evidence" / (
    "TC-012-agent-audit-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
assert all(d["deviceCode"] != code for d in api("/devices?page=1&size=100")["content"])
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "deviceCode": code, "cleanup": {}}
created = False
pid = None
try:
    api("/devices", "POST", fixture)
    created = True
    token = api("/devices/" + code + "/device-token/rotate", "POST")["accessToken"]
    local.start_simulator(fixture, token)
    pid = local.load(local.LOCAL / "processes.json")[code]["pid"]
    ev["connectionTest"] = api("/devices/" + code + "/connection-test", "POST")
    first = api("/device-agents", "POST", {"deviceCode": code})
    agent_id = first["agentId"]
    ev["createdAgent"] = {key: first.get(key) for key in
                          ("agentId", "agentStatus", "onlineStatus", "workStatus")}
    api("/device-agents/" + agent_id + "/disable", "POST", {"confirmed": True})
    ev["afterDisable"] = api("/device-agents/" + agent_id)
    reenabled = api("/device-agents", "POST", {"deviceCode": code})
    ev["reenabledAgent"] = {key: reenabled.get(key) for key in
                            ("agentId", "agentStatus", "onlineStatus", "workStatus")}
    api("/devices/" + code, "DELETE")
    ev["afterDeleteDevice"] = api("/devices/" + code)["deviceStatus"]
    ev["afterArchive"] = api("/device-agents/" + agent_id)
    try:
        api("/device-agents", "POST", {"deviceCode": code})
        ev["archiveReenableRejected"] = False
    except RuntimeError as error:
        ev["archiveReenableRejected"] = True
        ev["archiveReenableError"] = str(error)
    ev["afterRejectedReenable"] = api("/device-agents/" + agent_id)["agentStatus"]
    logs = api("/operation-logs?page=1&size=100")["content"]
    ev["agentOperationLogs"] = [row for row in logs
        if agent_id in (row.get("operationTarget") or "")]
    ev["deviceOperationLogs"] = [row for row in logs
        if code in (row.get("operationTarget") or "")]
    rows = db.query(db.source,
        "SELECT e.event_type FROM tip_stage2_v14.device_events e "
        "JOIN tip_stage2_v14.device_agents a ON a.id=e.device_agent_id "
        "WHERE a.agent_code='" + agent_id + "' ORDER BY e.id")
    ev["deviceEventTypes"] = rows.splitlines() if rows else []
finally:
    if created:
        try:
            if api("/devices/" + code)["deviceStatus"] != "DELETED":
                api("/devices/" + code, "DELETE")
            ev["cleanup"]["deviceStatus"] = api("/devices/" + code)["deviceStatus"]
        except Exception as error:
            ev["cleanup"]["error"] = str(error)
    if pid is not None:
        probe = subprocess.run(["powershell", "-NoProfile", "-Command",
            f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"],
            capture_output=True, text=True)
        if "device-simulator-runtime.jar" in probe.stdout:
            stop = subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                                  capture_output=True, text=True)
            ev["cleanup"]["simulatorStopped"] = stop.returncode == 0
        else:
            ev["cleanup"]["simulatorStopped"] = False
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(json.dumps({"evidence": str(out),
    "agentLogTypes": [x["operationType"] for x in ev.get("agentOperationLogs", [])],
    "deviceEventTypes": ev.get("deviceEventTypes", []),
    "archiveReenableRejected": ev.get("archiveReenableRejected"),
    "cleanup": ev["cleanup"]}, ensure_ascii=False))
