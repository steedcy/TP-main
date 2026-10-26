"""TC-035.S1: build context while a simulator is truly BUSY in a dry-run."""
import importlib.util
import json
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
db_spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(db_spec)
db_spec.loader.exec_module(db)
config, operator = local.API("配置管理员"), local.API("运行操作员")
template = next(t for t in config("/baseline-templates") if t["templateName"] == "S3_TC028_DISPLAY_DRYRUN")
assert template["templateStatus"] == "DISABLED"
agent = next(a for a in config("/device-agents?page=1&size=100")["content"]
             if a["deviceCode"] == "SIM_F2_DISPLAY")
assert agent["agentStatus"] == "ENABLED" and agent["onlineStatus"] == "ONLINE" and agent["workStatus"] == "IDLE"
device = config("/devices/SIM_F2_DISPLAY")
simulator = device["accessEndpoint"] + "/device-api/v1"
secret = local.secrets()["SIM_F2_DISPLAY"]
source = operator("/tasks/19")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "schema": "tip_stage2_v14", "templateBefore": template, "displayAgentBefore": agent,
      "dryRun": {}, "task": {}, "snapshot": {}, "restore": {}}
out = Path(__file__).parent / "evidence/TC-035-context-busy-availability.json"
dry_id = task_id = None
delay_changed = False
try:
    updated = config(f"/baseline-templates/{template['id']}", "PUT",
                     {"inputParams": template["inputParams"], "steps": template["steps"]})
    ev["dryRun"]["draftVersion"] = updated["templateVersion"]
    ev["dryRun"]["draftStatus"] = updated["templateStatus"]
    delay = local.request(simulator + "/control/delay?milliseconds=45000", "POST", token=secret)
    delay_changed = True
    ev["dryRun"]["delayMs"] = delay["milliseconds"]
    started = config(f"/baseline-templates/{template['id']}/dry-run", "POST",
        {"inputParams": {}, "simulatedDevices": [{"stepSeq": 1, "agentId": agent["agentId"]}]})
    dry_id = started["taskId"]
    ev["dryRun"]["started"] = started
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        current = next(a for a in config("/device-agents?page=1&size=100")["content"]
                       if a["deviceCode"] == "SIM_F2_DISPLAY")
        if current["workStatus"] == "BUSY":
            break
        time.sleep(0.2)
    ev["dryRun"]["displayAtBusy"] = current
    assert current["workStatus"] == "BUSY"
    ev["dryRun"]["taskStatusAtBusy"] = config(f"/baseline-templates/{template['id']}/dry-runs/{dry_id}")["result"]
    before = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
    request = {"taskGoal": source["taskGoal"], "taskFamily": source["taskFamily"],
               "sceneParams": source["sceneParams"]}
    ev["task"]["request"] = request
    try:
        ev["task"]["submitResponse"] = operator("/tasks", "POST", request)
    except RuntimeError as error:
        ev["task"]["submitError"] = str(error)
    after = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
    assert after > before
    task_id = after
    ev["task"]["id"] = task_id
    current = operator(f"/tasks/{task_id}")
    ev["task"]["clarifications"] = []
    for round_no in range(1, 3):
        if current["status"] != "PLANNING" or not current.get("missingInfoQuestions"):
            break
        answers = {q: "F2_BAGGAGE_POINT是预置虚构行李当前位置，尺寸80乘55乘35厘米、重35千克；目标F2_TEST_GATE，无需先引导到其他点。"
                   for q in current["missingInfoQuestions"]}
        item = {"round": round_no, "questions": current["missingInfoQuestions"], "answers": answers}
        try:
            item["response"] = operator(f"/tasks/{task_id}/clarify", "POST", {"answers": answers})
        except RuntimeError as error:
            item["error"] = str(error)
        current = operator(f"/tasks/{task_id}")
        item["afterStatus"] = current["status"]
        ev["task"]["clarifications"].append(item)
    deadline = time.monotonic() + 20
    contexts = []
    while time.monotonic() < deadline:
        contexts = operator(f"/tasks/{task_id}/context-snapshots")
        if contexts:
            break
        time.sleep(0.3)
    ev["snapshot"]["raw"] = contexts
    ev["dryRun"]["statusAtSnapshot"] = config(f"/baseline-templates/{template['id']}/dry-runs/{dry_id}")["result"]
    ev["dryRun"]["agentAtSnapshot"] = next(a for a in config("/device-agents?page=1&size=100")["content"]
                                                  if a["deviceCode"] == "SIM_F2_DISPLAY")
    if contexts:
        initial = min(contexts, key=lambda c: c["id"])
        ev["snapshot"]["initial"] = initial
        ev["snapshot"]["agents"] = json.loads(initial["agents"])
finally:
    if dry_id:
        try:
            ev["restore"]["dryRunCancel"] = config(
                f"/baseline-templates/{template['id']}/dry-runs/{dry_id}/cancel", "POST")
        except Exception as error:
            ev["restore"]["dryRunCancelError"] = str(error)
    if delay_changed:
        try:
            ev["restore"]["delayMs"] = local.request(simulator + "/control/delay?milliseconds=1000",
                                                      "POST", token=secret)["milliseconds"]
        except Exception as error:
            ev["restore"]["delayError"] = str(error)
    try:
        config(f"/baseline-templates/{template['id']}/disable", "POST")
        ev["restore"]["templateStatus"] = config(f"/baseline-templates/{template['id']}")["templateStatus"]
    except Exception as error:
        ev["restore"]["templateError"] = str(error)
    if task_id:
        task = operator(f"/tasks/{task_id}")
        if task["status"] in ["PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT", "DOWNGRADING", "EXECUTING"]:
            try:
                task = operator(f"/tasks/{task_id}/terminate", "POST",
                    {"confirmed": True, "reason": "阶段3忙碌代理上下文复测清场"})
            except Exception as error:
                ev["restore"]["taskTerminateError"] = str(error)
        ev["task"]["final"] = task
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        current = [a for a in config("/device-agents?page=1&size=100")["content"]
                   if a["deviceCode"].startswith("SIM_F2_")]
        if len(current) == 6 and all(a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE"
                                     and a["workStatus"] == "IDLE" for a in current):
            break
        time.sleep(0.5)
    ev["restore"]["allSixOnlineIdle"] = len(current) == 6 and all(
        a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE"
        for a in current)
    ev["restore"]["dryRunFinal"] = config(f"/baseline-templates/{template['id']}/dry-runs/{dry_id}") if dry_id else None
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
busy = next((a for a in ev["snapshot"].get("agents", []) if a["deviceCode"] == "SIM_F2_DISPLAY"), None)
print(json.dumps({"dryRunTaskId": dry_id, "taskId": task_id,
                  "snapshotCount": len(ev["snapshot"].get("raw", [])),
                  "displayWorkload": busy.get("workload") if busy else None,
                  "availableUntil": busy.get("availableUntil") if busy else None,
                  "agentBusyAtSnapshot": ev["dryRun"].get("agentAtSnapshot", {}).get("workStatus"),
                  "allSixOnlineIdle": ev["restore"]["allSixOnlineIdle"]}, ensure_ascii=False))
