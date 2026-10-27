"""Temporarily route the isolated V1.5 backend to the local fault model, then restore it."""
import hashlib
import importlib.util
import json
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
mode_path = root / ".local-test/planning-fault.json"
mode_original = mode_path.read_text(encoding="utf-8")
journal = root / ".local-test/planning-requests.jsonl"
journal_before = len(journal.read_text(encoding="utf-8").splitlines())
runtime = root / ".local-test/runtime/backend.jar"
target = root / "backend/target/airport-ai-app-1.0.0.jar"
assert hashlib.sha256(runtime.read_bytes()).digest() == hashlib.sha256(target.read_bytes()).digest()
config = local.API("配置管理员")
before_agents = [a for a in config("/device-agents?page=1&size=100")["content"]
                 if a["deviceCode"].startswith("SIM_F2_")]
assert len(before_agents) == 6 and all(a["agentStatus"] == "ENABLED" and
    a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE" and
    a["currentTaskId"] is None for a in before_agents)
out = stage / "evidence" / ("TC-050-controlled-profile-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "runtimeJarSha256": hashlib.sha256(runtime.read_bytes()).hexdigest(),
      "providerDuring": "external local fault fixture on 127.0.0.1:8099",
      "journalBeforeLines": journal_before, "steps": [], "restore": {}}
fixture_started = False
backend_switched = False


def stopped_backend():
    pid = int(json.loads((root / ".local-test/processes.json").read_text(encoding="utf-8"))["backend"]["pid"])
    ps = (f"$targetPid={pid}; $proc=Get-CimInstance Win32_Process -Filter \"ProcessId=$targetPid\"; "
          "$listener=Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction Stop; "
          "if ($null -eq $proc -or $proc.Name -ne 'java.exe' -or "
          "$proc.CommandLine -notlike '*.local-test*runtime*backend.jar*' -or "
          "$listener.OwningProcess -ne $targetPid) { throw 'backend identity mismatch' }; "
          "Stop-Process -Id $targetPid -Force; 'STOPPED_VERIFIED_RUNTIME_BACKEND'")
    result = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                            capture_output=True, text=True, timeout=25)
    assert result.returncode == 0 and "STOPPED_VERIFIED_RUNTIME_BACKEND" in result.stdout, result.stderr[-500:]
    return pid


def port_open(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def rebind():
    api = local.API("配置管理员")
    values = local.secrets()
    agents = [a for a in api("/device-agents?page=1&size=100")["content"]
              if a["deviceCode"].startswith("SIM_F2_")]
    for agent in agents:
        code = agent["deviceCode"]
        base = api("/devices/" + code)["accessEndpoint"] + "/device-api/v1"
        local.request(base + "/agents/" + agent["agentId"] + "/binding", "POST", {
            "deviceCode": code, "agentCode": agent["agentId"],
            "reportUrl": "http://127.0.0.1:8080/device-api/v1/agents/" + agent["agentId"] + "/report",
            "heartbeatIntervalSeconds": 5, "heartbeatTimeoutSeconds": 30}, values[code])
        local.request(base + "/control/online?value=true", "POST", token=values[code])
        local.request(base + "/control/heartbeat?value=true", "POST", token=values[code])
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        latest = [a for a in api("/device-agents?page=1&size=100")["content"]
                  if a["deviceCode"].startswith("SIM_F2_")]
        if len(latest) == 6 and all(a["onlineStatus"] == "ONLINE" and
            a["workStatus"] == "IDLE" and a["currentTaskId"] is None for a in latest):
            return latest
        time.sleep(1)
    raise RuntimeError("six simulators did not return ONLINE/IDLE")


try:
    assert not port_open(8099), "fixture port already occupied; refuse unknown process"
    local.launch("planning-fixture", [sys.executable, str(root / "scripts/planning-fault-server.py")],
                 local.env())
    fixture_started = True
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and not port_open(8099):
        time.sleep(0.25)
    assert port_open(8099)
    ev["steps"].append({"fixtureStarted": True})
    ev["steps"].append({"stoppedOriginalBackendPid": stopped_backend()})
    environment = local.env()
    database = environment.get("DB_NAME", "airport_ai")
    environment.update(SPRING_DATASOURCE_URL="jdbc:postgresql://localhost:5432/" + database +
                       "?currentSchema=tip_stage2_v14",
                       SPRING_FLYWAY_SCHEMAS="tip_stage2_v14",
                       SPRING_FLYWAY_DEFAULT_SCHEMA="tip_stage2_v14",
                       DEMO_RESET_ENABLED="true", PLANNING_MODEL_PROVIDER="external",
                       PLANNING_MODEL_ENDPOINT="http://127.0.0.1:8099",
                       PLANNING_MODEL_API_KEY="local-fixture")
    local.launch("backend", [shutil.which("java"), "-Xms128m", "-Xmx384m",
                             "-XX:+UseSerialGC", "-jar", str(runtime)], environment)
    backend_switched = True
    ev["steps"].append({"faultBackendHealth": local.wait_health(
        "http://127.0.0.1:8080/actuator/health")})
    ev["steps"].append({"agentsReady": len(rebind())})
    run = subprocess.run([sys.executable, str(stage / "retest-baseline-execution-failure.py")],
                         cwd=root, capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=180)
    ev["steps"].append({"testExitCode": run.returncode,
                        "testOutput": run.stdout.strip() if run.returncode == 0 else run.stderr[-1200:]})
    ev["newModelRequests"] = [json.loads(line) for line in
                              journal.read_text(encoding="utf-8").splitlines()[journal_before:]]
    assert run.returncode == 0
    assert any(r["phase"] == "goal" for r in ev["newModelRequests"])
    assert any(r["phase"] == "planning" for r in ev["newModelRequests"])
except Exception as error:
    ev["error"] = str(error)
finally:
    mode_path.write_text(mode_original, encoding="utf-8")
    ev["restore"]["fixtureModeExact"] = mode_path.read_text(encoding="utf-8") == mode_original
    if backend_switched and port_open(8080):
        try:
            ev["restore"]["stoppedFaultBackendPid"] = stopped_backend()
        except Exception as error:
            ev["restore"]["stopFaultBackendError"] = str(error)
    if not port_open(8080):
        recovery = subprocess.run([sys.executable, str(stage / "restart-stage3-services.py")],
                                  cwd=root, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=180)
        ev["restore"]["moonshotExitCode"] = recovery.returncode
        ev["restore"]["moonshotOutput"] = recovery.stdout.strip() if recovery.returncode == 0 else recovery.stderr[-1200:]
    if fixture_started:
        fixture_pid = int(json.loads((root / ".local-test/processes.json").read_text(encoding="utf-8"))
                          ["planning-fixture"]["pid"])
        ps = (f"$targetPid={fixture_pid}; "
              "$listener=Get-NetTCPConnection -LocalPort 8099 -State Listen -ErrorAction SilentlyContinue; "
              "if ($listener -and $listener.OwningProcess -eq $targetPid) { "
              "Stop-Process -Id $targetPid -Force; 'STOPPED_FIXTURE' }")
        result = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                                capture_output=True, text=True, timeout=20)
        ev["restore"]["fixtureStopped"] = (result.returncode == 0 and
            "STOPPED_FIXTURE" in result.stdout)
    try:
        ev["restore"]["backendHealth"] = local.request("http://127.0.0.1:8080/actuator/health")
        ev["restore"]["agents"] = [a for a in local.API("配置管理员")(
            "/device-agents?page=1&size=100")["content"] if a["deviceCode"].startswith("SIM_F2_")]
    except Exception as error:
        ev["restore"]["verificationError"] = str(error)
    ev["finishedAt"] = datetime.now(timezone.utc).isoformat()
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": out.name, "test": ev["steps"][-1] if ev["steps"] else None,
                  "newModelRequests": len(ev.get("newModelRequests", [])),
                  "moonshotRestored": ev["restore"].get("moonshotExitCode") == 0,
                  "fixtureStopped": ev["restore"].get("fixtureStopped"),
                  "error": ev.get("error")}, ensure_ascii=False))
if ev.get("error"):
    raise RuntimeError(ev["error"])
