"""TC-027.S1: edit baseline while a delayed dry-run executes, verify frozen plan."""
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
api = local.API("配置管理员")
name = "S3_TC028_DISPLAY_DRYRUN"
template = next(x for x in api("/baseline-templates") if x["templateName"] == name)
assert template["templateStatus"] == "DISABLED"
agent = next(x for x in api("/device-agents?page=1&size=100")["content"]
             if x["deviceCode"] == "SIM_F2_DISPLAY")
assert agent["onlineStatus"] == "ONLINE" and agent["workStatus"] == "IDLE"
device = api("/devices/SIM_F2_DISPLAY")
simulator = device["accessEndpoint"] + "/device-api/v1"
secret = local.secrets()["SIM_F2_DISPLAY"]
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "templateName": name, "deviceCode": "SIM_F2_DISPLAY", "observations": {}, "restore": {}}
out = Path(__file__).resolve().parent / "evidence/TC-027-baseline-running-version.json"
task_id = None
try:
    draft = api(f"/baseline-templates/{template['id']}", "PUT",
                {"inputParams": template["inputParams"], "steps": template["steps"]})
    ev["observations"]["runVersion"] = draft["templateVersion"]
    ev["observations"]["delayMs"] = local.request(simulator + "/control/delay?milliseconds=8000",
        "POST", token=secret)["milliseconds"]
    started = api(f"/baseline-templates/{template['id']}/dry-run", "POST",
        {"inputParams": {}, "simulatedDevices": [{"stepSeq": 1, "agentId": agent["agentId"]}]})
    task_id = started["taskId"]
    deadline = time.monotonic() + 8
    dispatched = False
    while time.monotonic() < deadline:
        dispatched = db.query(db.source,
            "SELECT count(*) FROM tip_stage2_v14.task_events WHERE task_id=" + str(task_id) +
            " AND event_type='STEP_DISPATCHED'") == "1"
        if dispatched:
            break
        time.sleep(0.2)
    ev["observations"]["dispatchedBeforeEdit"] = dispatched
    ev["observations"]["taskStatusAtEdit"] = db.query(db.source,
        "SELECT status FROM tip_stage2_v14.tasks WHERE id=" + str(task_id))
    old_snapshot = db.query(db.source,
        "SELECT snapshot_id FROM tip_stage2_v14.plan_versions WHERE task_id=" + str(task_id))
    ev["observations"]["snapshotBeforeEdit"] = old_snapshot
    edited = api(f"/baseline-templates/{template['id']}", "PUT",
        {"inputParams": draft["inputParams"], "steps": draft["steps"]})
    ev["observations"]["editedVersion"] = edited["templateVersion"]
    ev["observations"]["statusAfterEdit"] = edited["templateStatus"]
    ev["observations"]["snapshotImmediatelyAfterEdit"] = db.query(db.source,
        "SELECT snapshot_id FROM tip_stage2_v14.plan_versions WHERE task_id=" + str(task_id))
    result = started
    deadline = time.monotonic() + 25
    while result["result"] == "RUNNING" and time.monotonic() < deadline:
        time.sleep(0.5)
        result = api(f"/baseline-templates/{template['id']}/dry-runs/{task_id}")
    ev["observations"]["result"] = result["result"]
    ev["observations"]["stepResults"] = result["stepResults"]
    ev["observations"]["snapshotAfterResult"] = db.query(db.source,
        "SELECT snapshot_id FROM tip_stage2_v14.plan_versions WHERE task_id=" + str(task_id))
    ev["observations"]["templateStatusAfterOldRun"] = api(f"/baseline-templates/{template['id']}")["templateStatus"]
    ev["observations"]["taskStatusAfterResult"] = db.query(db.source,
        "SELECT status FROM tip_stage2_v14.tasks WHERE id=" + str(task_id))
    ev["observations"]["events"] = db.query(db.source,
        "SELECT event_type FROM tip_stage2_v14.task_events WHERE task_id=" + str(task_id) + " ORDER BY id").splitlines()
finally:
    try:
        ev["restore"]["delayMs"] = local.request(simulator + "/control/delay?milliseconds=1000",
            "POST", token=secret)["milliseconds"]
    except Exception as error:
        ev["restore"]["delayError"] = str(error)
    try:
        api(f"/baseline-templates/{template['id']}/disable", "POST")
        ev["restore"]["templateStatus"] = api(f"/baseline-templates/{template['id']}")["templateStatus"]
    except Exception as error:
        ev["restore"]["templateError"] = str(error)
    ev["restore"]["agent"] = db.query(db.source,
        "SELECT agent_status,online_status,work_status,coalesce(current_task_id,0) "
        "FROM tip_stage2_v14.device_agents WHERE agent_code='" + agent["agentId"] + "'")
    if task_id is not None:
        ev["taskId"] = task_id
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(ev, ensure_ascii=False))
