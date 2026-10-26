"""TC-070.S2: observe the live situation map during and after a delayed dry-run."""
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
template = next(t for t in api("/baseline-templates")
                if t["templateName"] == "S3_TC028_DISPLAY_DRYRUN")
assert template["templateStatus"] == "DISABLED"
agent = next(a for a in api("/device-agents?page=1&size=100")["content"]
             if a["deviceCode"] == code)
assert (agent["agentStatus"], agent["onlineStatus"], agent["workStatus"],
        agent["currentTaskId"]) == ("ENABLED", "ONLINE", "IDLE", None)
device = api("/devices/" + code)
base = device["accessEndpoint"] + "/device-api/v1"
secret = local.secrets()[code]
out = stage / "evidence" / (
    "TC-070-situation-live-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "templateId": template["id"],
      "agentBefore": agent, "restore": {}}
node = "C:/Users/savy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
environment = os.environ.copy()
environment["PLAYWRIGHT_CORE_PATH"] = (
    "C:/Users/savy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright-core")
dry_id = None
delay_changed = False

def browser(phase, task_id=None):
    command = [node, str(stage / "retest-situation-refresh.cjs"), phase]
    if task_id is not None:
        command.append(str(task_id))
    result = subprocess.run(command, cwd=root, env=environment,
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=38)
    return {"exitCode": result.returncode,
            "output": result.stdout.strip() if result.returncode == 0 else result.stderr.strip()[-1200:]}

try:
    updated = api(f"/baseline-templates/{template['id']}", "PUT",
                  {"inputParams": template["inputParams"], "steps": template["steps"]})
    ev["draftTemplate"] = {k: updated.get(k) for k in ("id", "templateVersion", "templateStatus")}
    response = local.request(base + "/control/delay?milliseconds=45000", "POST", token=secret)
    ev["delayMs"] = response["milliseconds"]
    delay_changed = True
    started = api(f"/baseline-templates/{template['id']}/dry-run", "POST",
                  {"inputParams": {}, "simulatedDevices": [
                      {"stepSeq": 1, "agentId": agent["agentId"]}]})
    dry_id = started["taskId"]
    ev["dryRunStarted"] = started
    deadline = time.monotonic() + 18
    while time.monotonic() < deadline:
        busy = api("/device-agents/" + agent["agentId"])
        if busy["workStatus"] == "BUSY" and busy["currentTaskId"] == dry_id:
            break
        time.sleep(0.2)
    ev["agentAtBusy"] = busy
    assert busy["workStatus"] == "BUSY" and busy["currentTaskId"] == dry_id
    ev["busyBrowser"] = browser("busy", dry_id)
    ev["dryRunAtBrowserEnd"] = api(f"/baseline-templates/{template['id']}/dry-runs/{dry_id}")
finally:
    if dry_id is not None:
        try:
            ev["restore"]["cancel"] = api(
                f"/baseline-templates/{template['id']}/dry-runs/{dry_id}/cancel", "POST")
        except Exception as error:
            ev["restore"]["cancelError"] = str(error)
    if delay_changed:
        try:
            ev["restore"]["delayMs"] = local.request(
                base + "/control/delay?milliseconds=1000", "POST", token=secret)["milliseconds"]
        except Exception as error:
            ev["restore"]["delayError"] = str(error)
    try:
        api(f"/baseline-templates/{template['id']}/disable", "POST")
        ev["restore"]["templateStatus"] = api(
            f"/baseline-templates/{template['id']}")["templateStatus"]
    except Exception as error:
        ev["restore"]["templateError"] = str(error)
    deadline = time.monotonic() + 24
    while time.monotonic() < deadline:
        agents = [a for a in api("/device-agents?page=1&size=100")["content"]
                  if a["deviceCode"].startswith("SIM_F2_")]
        if len(agents) == 6 and all(a["agentStatus"] == "ENABLED" and
            a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE" and
            a["currentTaskId"] is None for a in agents):
            break
        time.sleep(0.5)
    ev["restore"]["allSixOnlineIdle"] = len(agents) == 6 and all(
        a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE" and
        a["workStatus"] == "IDLE" and a["currentTaskId"] is None for a in agents)
    if dry_id is not None:
        ev["restore"]["dryRunFinal"] = api(
            f"/baseline-templates/{template['id']}/dry-runs/{dry_id}")
    try:
        ev["idleBrowser"] = browser("idle")
    except Exception as error:
        ev["idleBrowserError"] = str(error)
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(json.dumps({"evidence": str(out), "dryRunTaskId": dry_id,
                  "busyBrowser": ev.get("busyBrowser"),
                  "idleBrowser": ev.get("idleBrowser"),
                  "allSixOnlineIdle": ev["restore"]["allSixOnlineIdle"]}, ensure_ascii=False))
