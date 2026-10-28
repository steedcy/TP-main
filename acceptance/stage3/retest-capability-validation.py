"""TC-041.S1: pass an invalid capability plan through live V1.5 validation.

The local model fixture supplies deterministic plan content only. The isolated
backend, supervisor, assignment, simulator adapter, and device feedback run live.
"""
import hashlib
import importlib.util
import json
import os
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
config = local.API("配置管理员")
operator = local.API("运行操作员")
variant = os.environ.get("STAGE3_CAP_VARIANT", "unknown-capability")
assert variant in ("unknown-capability", "no-online-candidate", "missing-input", "invalid-param",
                   "oversize-no-online-candidate")
source_id = 19 if variant == "oversize-no-online-candidate" else 73
source = operator(f"/tasks/{source_id}")
source_plan = next(p for p in operator(f"/tasks/{source_id}/plan-versions")
                   if p["source"] == ("BASELINE_TEMPLATE" if source_id == 19 else "AUTONOMOUS"))
assert source["status"] == "COMPLETED" and len(source_plan["planSteps"]) == 4
initial_steps = json.loads(json.dumps(source_plan["planSteps"], ensure_ascii=False))
assert source["taskFamily"] == ("OVERSIZE_BAGGAGE_HANDLING" if source_id == 19 else "FLIGHT_CHANGE_RESPONSE")
if variant == "unknown-capability":
    initial_steps[1]["capabilityType"] = "CAP_S3_UNKNOWN_TEST"
elif variant == "missing-input":
    assert "contentData" in initial_steps[1]["inputParams"]
    del initial_steps[1]["inputParams"]["contentData"]
elif variant == "invalid-param":
    initial_steps[1]["inputParams"]["displayDuration"] = 9999
agents = [a for a in config("/device-agents?page=1&size=100")["content"]
          if a["deviceCode"].startswith("SIM_F2_")]
assert len(agents) == 6 and all(a["agentStatus"] == "ENABLED" and
    a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE" and
    a["currentTaskId"] is None for a in agents)
mode_path = root / ".local-test/planning-fault.json"
mode_original = mode_path.read_text(encoding="utf-8")
mode = json.loads(mode_original)
mode.update(goal="success", planning="success", replanning="success",
            initialPlanSteps=initial_steps)
journal = root / ".local-test/planning-requests.jsonl"
journal_before = len(journal.read_text(encoding="utf-8").splitlines())
runtime = root / ".local-test/runtime/backend.jar"
target = root / "backend/target/airport-ai-app-1.0.0.jar"
assert hashlib.sha256(runtime.read_bytes()).digest() == hashlib.sha256(target.read_bytes()).digest()
secrets = local.secrets()
codes = [a["deviceCode"] for a in agents]
endpoints = {code: config("/devices/" + code)["accessEndpoint"] + "/device-api/v1"
             for code in codes}
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "runtimeJarSha256": hashlib.sha256(runtime.read_bytes()).hexdigest(),
      "sourceTaskId": source_id, "request": {key: source[key] for key in
                                     ("taskGoal", "taskFamily", "sceneParams")},
      "planVariant": variant, "sourcePlanSource": source_plan["source"],
      "initialPlanSteps": initial_steps, "fixtureBefore": json.loads(mode_original),
      "journalBeforeLines": journal_before, "restore": {}}
out = stage / "evidence" / ("TC-041-capability-validation-" + variant + "-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
fixture_started = False
backend_switched = False
task_id = None
delay_changed = []
disabled_codes = []


def port_open(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def stop_backend():
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


def rebind():
    api = local.API("配置管理员")
    current = [a for a in api("/device-agents?page=1&size=100")["content"]
               if a["deviceCode"].startswith("SIM_F2_")]
    for agent in current:
        code = agent["deviceCode"]
        local.request(endpoints[code] + "/agents/" + agent["agentId"] + "/binding", "POST", {
            "deviceCode": code, "agentCode": agent["agentId"],
            "reportUrl": "http://127.0.0.1:8080/device-api/v1/agents/" + agent["agentId"] + "/report",
            "heartbeatIntervalSeconds": 5, "heartbeatTimeoutSeconds": 30}, secrets[code])
        local.request(endpoints[code] + "/control/online?value=true", "POST", token=secrets[code])
        local.request(endpoints[code] + "/control/heartbeat?value=true", "POST", token=secrets[code])
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        latest = [a for a in api("/device-agents?page=1&size=100")["content"]
                  if a["deviceCode"].startswith("SIM_F2_")]
        if len(latest) == 6 and all(a["onlineStatus"] == "ONLINE" and
            a["workStatus"] == "IDLE" and a["currentTaskId"] is None for a in latest):
            return latest
        time.sleep(.5)
    raise RuntimeError("six simulators did not return ONLINE/IDLE")


def snapshot():
    return {"at": datetime.now(timezone.utc).isoformat(),
            "task": operator(f"/tasks/{task_id}"),
            "plans": operator(f"/tasks/{task_id}/plan-versions"),
            "assignments": operator(f"/tasks/{task_id}/step-assignments"),
            "events": operator(f"/tasks/{task_id}/events")}


try:
    assert not port_open(8099), "fixture port occupied; refuse unknown process"
    mode_path.write_text(json.dumps(mode, ensure_ascii=False), encoding="utf-8")
    local.launch("planning-fixture", [sys.executable, str(root / "scripts/planning-fault-server.py")], local.env())
    fixture_started = True
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and not port_open(8099):
        time.sleep(.2)
    assert port_open(8099)
    ev["originalBackendPid"] = stop_backend()
    environment = local.env()
    database = environment.get("DB_NAME", "airport_ai")
    environment.update(SPRING_DATASOURCE_URL="jdbc:postgresql://localhost:5432/" + database +
                       "?currentSchema=tip_stage2_v14",
                       SPRING_FLYWAY_SCHEMAS="tip_stage2_v14",
                       SPRING_FLYWAY_DEFAULT_SCHEMA="tip_stage2_v14",
                       DEMO_RESET_ENABLED="true", PLANNING_MODEL_PROVIDER="external",
                       PLANNING_MODEL_ENDPOINT="http://127.0.0.1:8099", PLANNING_MODEL_API_KEY="local-fixture")
    local.launch("backend", [shutil.which("java"), "-Xms128m", "-Xmx384m",
                             "-XX:+UseSerialGC", "-jar", str(runtime)], environment)
    backend_switched = True
    ev["fixtureBackendHealth"] = local.wait_health("http://127.0.0.1:8080/actuator/health")
    rebind()
    operator = local.API("运行操作员")
    config = local.API("配置管理员")
    if variant in ("no-online-candidate", "oversize-no-online-candidate"):
        target_codes = (("SIM_F2_BAGGAGE", "SIM_F2_BAGGAGE_B")
                        if variant == "oversize-no-online-candidate"
                        else ("SIM_F2_DISPLAY", "SIM_F2_FLIGHT"))
        for code in target_codes:
            agent = next(a for a in config("/device-agents?page=1&size=100")["content"]
                         if a["deviceCode"] == code)
            assert agent["workStatus"] == "IDLE" and agent["currentTaskId"] is None
            config("/device-agents/" + agent["agentId"] + "/disable", "POST", {"confirmed": True})
            disabled_codes.append(code)
            ev.setdefault("disabledAgents", {})[code] = config("/device-agents/" + agent["agentId"])
    elif variant == "unknown-capability":
        for code in codes:
            ev.setdefault("delayControls", {})[code] = local.request(
                endpoints[code] + "/control/delay?milliseconds=9000", "POST", token=secrets[code])
            delay_changed.append(code)
    submitted = operator("/tasks", "POST", ev["request"])
    task_id = submitted["id"]
    ev["submitted"] = submitted
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        assignments = operator(f"/tasks/{task_id}/step-assignments")
        events = operator(f"/tasks/{task_id}/events")
        if assignments and any(e["eventType"] == "STEP_DISPATCHED" for e in events):
            break
        if operator(f"/tasks/{task_id}")["status"] in ("FAILED", "PENDING_MANUAL", "COMPLETED"):
            break
        time.sleep(.25)
    ev["firstReceipt"] = snapshot()
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        events = operator(f"/tasks/{task_id}/events")
        if sum(e["eventType"] == "STEP_DISPATCHED" for e in events) >= 2:
            break
        if operator(f"/tasks/{task_id}")["status"] in ("FAILED", "PENDING_MANUAL", "COMPLETED"):
            break
        time.sleep(.25)
    ev["secondDispatch"] = snapshot()
    deadline = time.monotonic() + 100
    while time.monotonic() < deadline:
        task = operator(f"/tasks/{task_id}")
        if task["status"] in ("COMPLETED", "FAILED", "PENDING_MANUAL", "MANUAL_TERMINATED"):
            break
        time.sleep(.5)
    ev["finished"] = snapshot()
    ev["newModelRequests"] = [json.loads(line) for line in
                              journal.read_text(encoding="utf-8").splitlines()[journal_before:]]
except Exception as error:
    ev["error"] = str(error)
finally:
    mode_path.write_text(mode_original, encoding="utf-8")
    ev["restore"]["fixtureModeExact"] = mode_path.read_text(encoding="utf-8") == mode_original
    for code in delay_changed:
        try:
            ev["restore"].setdefault("delays", {})[code] = local.request(
                endpoints[code] + "/control/delay?milliseconds=1000", "POST", token=secrets[code])
        except Exception as error:
            ev["restore"].setdefault("delayErrors", {})[code] = str(error)
    if task_id is not None and port_open(8080):
        try:
            current = operator(f"/tasks/{task_id}")
            if current["status"] in ("PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT",
                                     "DOWNGRADING", "EXECUTING", "PENDING_MANUAL"):
                ev["restore"]["cleanup"] = operator(f"/tasks/{task_id}/terminate", "POST",
                    {"reason": "阶段3正式任务顺序执行取证后清理", "confirmed": True})["status"]
        except Exception as error:
            ev["restore"]["cleanupError"] = str(error)
    for code in disabled_codes:
        try:
            ev["restore"].setdefault("reenabledAgents", {})[code] = config(
                "/device-agents", "POST", {"deviceCode": code})
        except Exception as error:
            ev["restore"].setdefault("reenableErrors", {})[code] = str(error)
    if backend_switched and port_open(8080):
        try:
            ev["restore"]["stoppedFixtureBackendPid"] = stop_backend()
        except Exception as error:
            ev["restore"]["stopFixtureBackendError"] = str(error)
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
        ev["restore"]["fixtureStopped"] = result.returncode == 0 and "STOPPED_FIXTURE" in result.stdout
    try:
        ev["restore"]["backendHealth"] = local.request("http://127.0.0.1:8080/actuator/health")
        current = [a for a in local.API("配置管理员")(
            "/device-agents?page=1&size=100")["content"] if a["deviceCode"].startswith("SIM_F2_")]
        ev["restore"]["sixOnlineIdle"] = len(current) == 6 and all(
            a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE" and
            a["currentTaskId"] is None for a in current)
    except Exception as error:
        ev["restore"]["verificationError"] = str(error)
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": out.name, "taskId": task_id,
                  "firstStatus": ev.get("firstReceipt", {}).get("task", {}).get("status"),
                  "secondStatus": ev.get("secondDispatch", {}).get("task", {}).get("status"),
                  "finalStatus": ev.get("finished", {}).get("task", {}).get("status"),
                  "restore": {k: v for k, v in ev["restore"].items()
                              if k not in ("moonshotOutput", "backendHealth")},
                  "error": ev.get("error")}, ensure_ascii=False))
if ev.get("error"):
    raise RuntimeError(ev["error"])
