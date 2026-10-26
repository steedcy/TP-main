"""Run a delayed real dry-run for F020.R09, then restore the six simulators."""
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
config = local.API("配置管理员")
operator = local.API("运行操作员")
code = "SIM_F2_DISPLAY"
template = next(t for t in config("/baseline-templates")
                if t["templateName"] == "S3_TC028_DISPLAY_DRYRUN")
assert template["templateStatus"] == "DISABLED" and len(template["steps"]) == 1
agents = [a for a in config("/device-agents?page=1&size=100")["content"]
          if a["deviceCode"].startswith("SIM_F2_")]
assert len(agents) == 6 and all(a["agentStatus"] == "ENABLED" and
    a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE" and
    a["currentTaskId"] is None for a in agents)
agent = next(a for a in agents if a["deviceCode"] == code)
base = config("/devices/" + code)["accessEndpoint"] + "/device-api/v1"
secret = local.secrets()[code]
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "templateId": template["id"],
      "agentId": agent["agentId"], "restore": {}}
out = stage / "evidence" / ("SRS_F020-R09-refresh-live-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
task_id = None
try:
    updated = config(f"/baseline-templates/{template['id']}", "PUT",
                     {"inputParams": template["inputParams"], "steps": template["steps"]})
    ev["draftVersion"] = updated["templateVersion"]
    ev["delayMs"] = local.request(base + "/control/delay?milliseconds=60000",
                                  "POST", token=secret)["milliseconds"]
    started = config(f"/baseline-templates/{template['id']}/dry-run", "POST",
                     {"inputParams": {}, "simulatedDevices": [
                         {"stepSeq": 1, "agentId": agent["agentId"]}]})
    task_id = started["taskId"]
    ev["started"] = started
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        busy = config("/device-agents/" + agent["agentId"])
        if busy["workStatus"] == "BUSY" and busy["currentTaskId"] == task_id:
            break
        time.sleep(.2)
    ev["agentAtBusy"] = busy
    assert busy["workStatus"] == "BUSY" and busy["currentTaskId"] == task_id
    ev["taskBeforeBrowser"] = operator(f"/tasks/{task_id}")["status"]
    node = "C:/Users/savy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
    environment = os.environ.copy()
    environment["PLAYWRIGHT_CORE_PATH"] = (
        "C:/Users/savy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright-core")
    browser = subprocess.run([node, str(stage / "retest-task-detail-refresh-ui.cjs"), str(task_id)],
                             cwd=root, env=environment, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=55)
    ev["browserExitCode"] = browser.returncode
    ev["browserOutput"] = browser.stdout.strip() if browser.returncode == 0 else browser.stderr.strip()[-500:]
    ev["taskAfterBrowser"] = operator(f"/tasks/{task_id}")["status"]
finally:
    if task_id is not None:
        try:
            if operator(f"/tasks/{task_id}")["status"] in (
                "PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT", "DOWNGRADING", "EXECUTING"):
                ev["restore"]["cancel"] = config(
                    f"/baseline-templates/{template['id']}/dry-runs/{task_id}/cancel", "POST")
        except Exception as error:
            ev["restore"]["cancelError"] = str(error)
    try:
        ev["restore"]["delayMs"] = local.request(
            base + "/control/delay?milliseconds=1000", "POST", token=secret)["milliseconds"]
    except Exception as error:
        ev["restore"]["delayError"] = str(error)
    try:
        config(f"/baseline-templates/{template['id']}/disable", "POST")
        ev["restore"]["templateStatus"] = config(
            f"/baseline-templates/{template['id']}")["templateStatus"]
    except Exception as error:
        ev["restore"]["templateError"] = str(error)
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        agents = [a for a in config("/device-agents?page=1&size=100")["content"]
                  if a["deviceCode"].startswith("SIM_F2_")]
        if len(agents) == 6 and all(a["agentStatus"] == "ENABLED" and
            a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE" and
            a["currentTaskId"] is None for a in agents):
            break
        time.sleep(.5)
    ev["restore"]["allSixOnlineIdle"] = len(agents) == 6 and all(
        a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE"
        and a["workStatus"] == "IDLE" and a["currentTaskId"] is None for a in agents)
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "taskId": task_id,
                  "browserExitCode": ev.get("browserExitCode"),
                  "taskBeforeBrowser": ev.get("taskBeforeBrowser"),
                  "taskAfterBrowser": ev.get("taskAfterBrowser"),
                  "allSixOnlineIdle": ev["restore"]["allSixOnlineIdle"]}, ensure_ascii=False))
