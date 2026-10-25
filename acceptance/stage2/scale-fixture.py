"""Create or retire fourteen temporary F2 simulators in the isolated runtime.

Six canonical F2 objects remain for the <=10-object demo setup. `prepare`
reaches twenty live objects for the separate performance setup; `cleanup`
returns to six. Tokens remain only in the ignored DPAPI store.
"""
import datetime
import importlib.util
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)
OUT = ROOT / "acceptance/stage2/evidence/scale-fixture.json"
CANONICAL = {d["deviceCode"] for d in env.load(env.FIXTURES / "devices.json")}


def save(data):
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def api_config():
    return env.API("配置管理员")


def status(api):
    devices = api("/devices?page=1&size=100")["content"]
    agents = api("/device-agents?page=1&size=100")["content"]
    return {"at": env.stamp(), "deviceCount": len(devices),
            "onlineEnabledCount": sum(a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE" for a in agents),
            "activeTemporaryCodes": [d["deviceCode"] for d in devices if d["deviceCode"] not in CANONICAL],
            "canonicalCount": sum(d["deviceCode"] in CANONICAL for d in devices)}


def prepare():
    if OUT.exists():
        prior = json.loads(OUT.read_text(encoding="utf-8"))
        if not prior.get("cleanup"):
            raise RuntimeError("prior fixture has not been cleaned; resume cleanup first")
    api = api_config()
    before = status(api)
    if before["deviceCount"] != 6 or before["canonicalCount"] != 6 or before["activeTemporaryCodes"]:
        raise RuntimeError("prepare requires exactly six canonical active devices")
    templates = env.load(env.FIXTURES / "devices.json")[:4]
    run_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    evidence = {"runId": run_id, "startedAt": env.stamp(), "before": before,
                "setup": "performance-20-objects", "temporaryDevices": []}
    save(evidence)
    tokens = env.secrets()
    for index in range(14):
        seq = index + 1
        template = templates[index % len(templates)]
        code = f"S2P{run_id}{seq:02d}"
        port = 8101 + index
        device = {"deviceCode": code, "deviceName": f"阶段2性能仿真体{seq:02d}",
                  "deviceTypeCode": "SIMULATOR", "isSimulator": True,
                  "simulatedDeviceType": template["simulatedDeviceType"], "areaCode": "F2_TEST",
                  "positionX": 790 + (seq % 7) * 4, "positionY": 4000 + seq * 9,
                  "accessEndpoint": f"http://127.0.0.1:{port}",
                  "accessCredentialRef": "local-test/" + code, "statusReportInterval": 5,
                  "remark": "隔离schema阶段2性能对象；结束后停用并删除"}
        api("/devices", "POST", device)
        tokens[code] = api("/devices/" + code + "/device-token/rotate", "POST")["accessToken"]
        env.store_secrets(tokens)
        env.start_simulator(device, tokens[code])
        connection = api("/devices/" + code + "/connection-test", "POST")
        if connection["result"] != "PASSED":
            raise RuntimeError(code + " connection failed")
        agent = api("/device-agents", "POST", {"deviceCode": code})
        env.request(device["accessEndpoint"] + "/device-api/v1/agents/" + agent["agentId"] + "/binding",
                    "POST", {"deviceCode": code, "agentCode": agent["agentId"],
                             "reportUrl": "http://127.0.0.1:8080/device-api/v1/agents/" + agent["agentId"] + "/report",
                             "heartbeatIntervalSeconds": 5, "heartbeatTimeoutSeconds": 30}, tokens[code])
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            live = next((a for a in api("/device-agents?page=1&size=100")["content"]
                         if a["deviceCode"] == code), None)
            if live and live["onlineStatus"] == "ONLINE":
                break
            time.sleep(1)
        else:
            raise RuntimeError(code + " heartbeat not observed")
        registry = env.load(ROOT / ".local-test/processes.json")
        evidence["temporaryDevices"].append({"code": code, "agentId": agent["agentId"],
                                              "port": port, "pid": registry[code]["pid"],
                                              "type": device["simulatedDeviceType"], "online": True})
        save(evidence)
        print(f"{seq}/14 {code} online", flush=True)
    evidence["preparedAt"] = env.stamp()
    evidence["performanceState"] = status(api)
    save(evidence)
    assert evidence["performanceState"]["deviceCount"] == 20
    assert evidence["performanceState"]["onlineEnabledCount"] == 20
    print(json.dumps(evidence["performanceState"], ensure_ascii=False))


def owned_process(pid):
    command = ("(Get-CimInstance Win32_Process -Filter 'ProcessId=" + str(pid) +
               "' | Select-Object -ExpandProperty CommandLine)")
    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError("process ownership query failed")
    line = result.stdout.strip().lower()
    return bool(line and str(ROOT).lower() in line and "device-simulator-runtime.jar" in line)


def cleanup():
    evidence = json.loads(OUT.read_text(encoding="utf-8"))
    if evidence.get("cleanup"):
        raise RuntimeError("fixture already cleaned")
    api = api_config()
    tokens = env.secrets()
    registry_path = ROOT / ".local-test/processes.json"
    registry = env.load(registry_path)
    known = {row["code"] for row in evidence["temporaryDevices"]}
    # Include objects created just before an interrupted prepare could save a row.
    prefix = "S2P" + evidence["runId"]
    for device in api("/devices?page=1&size=100")["content"]:
        code = device["deviceCode"]
        if code.startswith(prefix) and code not in known:
            evidence["temporaryDevices"].append({"code": code,
                                                  "pid": registry.get(code, {}).get("pid"),
                                                  "recoveredAfterInterruptedPrepare": True})
    save(evidence)
    for row in evidence["temporaryDevices"]:
        code, pid = row["code"], row["pid"]
        if pid and owned_process(pid):
            subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                            "Stop-Process -Id " + str(pid) + " -Force"], check=True)
        agent = next((a for a in api("/device-agents?page=1&size=100")["content"]
                      if a["deviceCode"] == code), None)
        if agent and agent["agentStatus"] == "ENABLED":
            api("/device-agents/" + agent["agentId"] + "/disable", "POST", {"confirmed": True})
        current = {d["deviceCode"] for d in api("/devices?page=1&size=100")["content"]}
        if code in current:
            api("/devices/" + code, "DELETE")
        tokens.pop(code, None)
        registry.pop(code, None)
        row["retiredAt"] = env.stamp()
        save(evidence)
    env.store_secrets(tokens)
    env.save(registry_path, registry)
    after = status(api)
    evidence["cleanup"] = {"at": env.stamp(), "after": after}
    save(evidence)
    assert after["deviceCount"] == 6 and after["canonicalCount"] == 6
    assert after["onlineEnabledCount"] == 6 and not after["activeTemporaryCodes"]
    print(json.dumps(after, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"prepare", "cleanup"}:
        raise SystemExit("usage: scale-fixture.py prepare|cleanup")
    prepare() if sys.argv[1] == "prepare" else cleanup()
