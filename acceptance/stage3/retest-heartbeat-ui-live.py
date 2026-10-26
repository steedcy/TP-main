"""TC-014.S2: live offline/recovery API and Chrome evidence with safe heartbeat restore."""
import importlib.util
import json
import os
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
code = "SIM_F2_DISPLAY"
device = api("/devices/" + code)
secret = local.secrets()[code]
endpoint = device["accessEndpoint"] + "/device-api/v1/control/heartbeat"
agent = next(a for a in api("/device-agents?page=1&size=100")["content"]
             if a["deviceCode"] == code)
assert agent["onlineStatus"] == "ONLINE" and agent["workStatus"] == "IDLE"
assert agent["currentTaskId"] is None
out = stage / "evidence" / ("TC-014-heartbeat-ui-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")


def snapshot():
    response = api("/situation/snapshot")
    return next(item for item in response["agents"] if item["deviceCode"] == code)


def events():
    return api("/simulators/" + code + "/events")


def browser(phase):
    env = os.environ.copy()
    env["PLAYWRIGHT_CORE_PATH"] = ("C:/Users/savy/.cache/codex-runtimes/"
                                   "codex-primary-runtime/dependencies/node/node_modules/playwright-core")
    node = "C:/Users/savy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
    run = subprocess.run([node, str(stage / "retest-heartbeat-ui.cjs"), phase],
        cwd=root, env=env, capture_output=True, encoding="utf-8", errors="replace", timeout=90)
    return {"exitCode": run.returncode,
            "output": (run.stdout if run.returncode == 0 else run.stderr)[-1000:].strip()}


ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "deviceCode": code,
      "agentCode": agent["agentId"], "before": {"agent": agent,
      "situation": snapshot(), "events": events()}, "restore": {}}
stopped = False
began = time.monotonic()
try:
    ev["controlOff"] = local.request(endpoint + "?value=false", "POST", token=secret)
    stopped = True
    deadline = time.monotonic() + 55
    while time.monotonic() < deadline:
        current = api("/device-agents/" + agent["agentId"])
        if current["onlineStatus"] == "OFFLINE":
            break
        time.sleep(1)
    ev["offlineElapsedSeconds"] = round(time.monotonic() - began, 2)
    ev["offline"] = {"agent": current, "situation": snapshot(), "events": events(),
                     "onlineFilterContains": any(a["deviceCode"] == code for a in
                         api("/device-agents?onlineStatus=ONLINE&page=1&size=100")["content"])}
    if current["onlineStatus"] == "OFFLINE":
        ev["offline"]["browser"] = browser("offline")
finally:
    if stopped:
        ev["restore"]["controlOn"] = local.request(endpoint + "?value=true", "POST", token=secret)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            recovered = api("/device-agents/" + agent["agentId"])
            if recovered["onlineStatus"] == "ONLINE":
                break
            time.sleep(1)
        ev["restore"]["agent"] = recovered
        ev["restore"]["situation"] = snapshot()
        ev["restore"]["events"] = events()
        if recovered["onlineStatus"] == "ONLINE":
            ev["restore"]["browser"] = browser("recovered")
    ev["finishedAt"] = datetime.now(timezone.utc).isoformat()
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": out.name,
                  "offlineElapsedSeconds": ev.get("offlineElapsedSeconds"),
                  "offlineStatus": ev.get("offline", {}).get("agent", {}).get("onlineStatus"),
                  "offlineBrowser": ev.get("offline", {}).get("browser", {}).get("exitCode"),
                  "recoveredStatus": ev.get("restore", {}).get("agent", {}).get("onlineStatus"),
                  "recoveredBrowser": ev.get("restore", {}).get("browser", {}).get("exitCode")},
                 ensure_ascii=False))
