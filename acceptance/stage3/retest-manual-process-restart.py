"""TC-094: deliberately stop the isolated backend, manually restart, compare persisted data."""
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


local = module("local", root / "scripts/local-test-environment.py")
db = module("db", root / "acceptance/stage2/db-isolation.py")
config, operator = local.API("配置管理员"), local.API("运行操作员")
agents = [a for a in config("/device-agents?page=1&size=100")["content"]
          if a["deviceCode"].startswith("SIM_F2_")]
assert len(agents) == 6 and all(a["agentStatus"] == "ENABLED" and
    a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE" and
    a["currentTaskId"] is None for a in agents)
assert local.request("http://127.0.0.1:8080/actuator/health")["status"] == "UP"
assert operator("/tasks/73")["status"] == "COMPLETED"
process = json.loads((root / ".local-test/processes.json").read_text(encoding="utf-8"))["backend"]
pid = int(process["pid"])
assert pid > 0


def snapshot():
    task = db.query(db.source, "SELECT id,task_code,status,task_goal,current_plan_version_id "
                    "FROM tip_stage2_v14.tasks WHERE id IN (19,73) ORDER BY id")
    events = db.query(db.source, "SELECT task_id,id,event_type,occurred_at,coalesce(reason_code,''),"
                      "coalesce(detail_summary,'') FROM tip_stage2_v14.task_events "
                      "WHERE task_id IN (19,73) ORDER BY task_id,id")
    return {"taskRowsSha256": hashlib.sha256(task.encode()).hexdigest(),
            "eventRowsSha256": hashlib.sha256(events.encode()).hexdigest(),
            "taskRows": task.splitlines(), "eventCount": len(events.splitlines()),
            "task73Status": operator("/tasks/73")["status"],
            "task73EventCount": len(operator("/tasks/73/events"))}


before = snapshot()
out = stage / "evidence" / ("TC-094-manual-restart-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "backendRecordedPid": pid,
      "backendRecordedStart": process["startedAt"], "before": before,
      "stop": {}, "restart": {}, "after": {}}
started = time.monotonic()
try:
    ps = (f"$targetPid={pid}; "
          "$proc=Get-CimInstance Win32_Process -Filter \"ProcessId=$targetPid\"; "
          "$listener=Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction Stop; "
          "if ($null -eq $proc -or $proc.Name -ne 'java.exe' -or "
          "$proc.CommandLine -notlike '*.local-test*runtime*backend.jar*' -or "
          "$listener.OwningProcess -ne $targetPid) { throw 'backend identity mismatch' }; "
          "Stop-Process -Id $targetPid -Force; 'STOPPED_VERIFIED_RUNTIME_BACKEND'")
    stopped = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=25)
    ev["stop"] = {"exitCode": stopped.returncode,
                  "verified": stopped.returncode == 0 and
                      "STOPPED_VERIFIED_RUNTIME_BACKEND" in stopped.stdout,
                  "error": stopped.stderr[-500:] if stopped.returncode else None,
                  "elapsedSeconds": time.monotonic() - started}
    assert ev["stop"]["verified"]
    deadline = time.monotonic() + 15
    down = False
    while time.monotonic() < deadline:
        try:
            local.request("http://127.0.0.1:8080/actuator/health", timeout=1)
        except Exception:
            down = True
            break
        time.sleep(0.2)
    ev["stop"]["healthUnavailableAfterStop"] = down
    assert down
    restart = subprocess.run([sys.executable, str(stage / "restart-stage3-services.py")],
                             cwd=root, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=180)
    ev["restart"] = {"exitCode": restart.returncode,
                     "output": restart.stdout.strip() if restart.returncode == 0 else restart.stderr[-1000:],
                     "elapsedSecondsToServicesReady": time.monotonic() - started}
    assert restart.returncode == 0
    ev["after"]["backendHealth"] = local.request("http://127.0.0.1:8080/actuator/health")
    with urllib.request.urlopen("http://127.0.0.1:5173/", timeout=5) as response:
        ev["after"]["frontendHttpStatus"] = response.status
    ev["after"]["snapshot"] = snapshot()
    ev["after"]["agents"] = [a for a in local.API("配置管理员")(
        "/device-agents?page=1&size=100")["content"] if a["deviceCode"].startswith("SIM_F2_")]
    ev["after"]["elapsedSecondsToCoreReads"] = time.monotonic() - started
    ev["after"]["persistedExactly"] = all(before[k] == ev["after"]["snapshot"][k]
        for k in ("taskRowsSha256", "eventRowsSha256", "eventCount", "task73Status",
                  "task73EventCount"))
except Exception as error:
    ev["error"] = str(error)
    # Recover the environment even if a verification assertion failed.
    if ev["stop"].get("verified") and not ev["restart"].get("exitCode") == 0:
        try:
            retry = subprocess.run([sys.executable, str(stage / "restart-stage3-services.py")],
                                   cwd=root, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", timeout=180)
            ev["restart"]["recoveryRetryExitCode"] = retry.returncode
            ev["restart"]["recoveryRetryOutput"] = retry.stdout[-1000:] if retry.returncode == 0 else retry.stderr[-1000:]
        except Exception as retry_error:
            ev["restart"]["recoveryRetryError"] = str(retry_error)
finally:
    ev["finishedAt"] = datetime.now(timezone.utc).isoformat()
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": out.name, "stop": ev["stop"],
                  "restart": ev["restart"], "persistedExactly": ev["after"].get("persistedExactly"),
                  "error": ev.get("error")}, ensure_ascii=False))
if ev.get("error"):
    raise RuntimeError(ev["error"])
