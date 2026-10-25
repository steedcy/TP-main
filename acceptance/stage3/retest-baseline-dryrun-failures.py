"""TC-029.S2: simulated device failure and timeout dry-runs; restore controls."""
import importlib.util
import json
import time
import urllib.error
import urllib.request
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
      "templateName": name, "beforeTaskCount": db.query(db.source, "SELECT count(*) FROM tip_stage2_v14.tasks"),
      "cases": [], "restore": {}}
out = Path(__file__).resolve().parent / "evidence/TC-029-baseline-dryrun-failures.json"


def enable_status(ident):
    request = urllib.request.Request(local.BASE + f"/baseline-templates/{ident}/enable", method="POST",
        headers={"Authorization": "Bearer " + api.token})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read()).get("message")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read()).get("message")


try:
    for scenario in ("FAILED", "TIMEOUT"):
        current = api(f"/baseline-templates/{template['id']}")
        updated = api(f"/baseline-templates/{template['id']}", "PUT",
                      {"inputParams": current["inputParams"], "steps": current["steps"]})
        control = local.request(simulator + "/control/scenario", "POST",
                                {"scenarioResult": scenario}, token=secret)
        started = api(f"/baseline-templates/{template['id']}/dry-run", "POST",
            {"inputParams": {}, "simulatedDevices": [{"stepSeq": 1, "agentId": agent["agentId"]}]})
        task_id = started["taskId"]
        result = started
        deadline = time.monotonic() + 30
        while result["result"] == "RUNNING" and time.monotonic() < deadline:
            time.sleep(0.5)
            result = api(f"/baseline-templates/{template['id']}/dry-runs/{task_id}")
        item = {"scenario": scenario, "controlResult": control["scenarioResult"],
                "templateVersion": updated["templateVersion"], "taskId": task_id,
                "result": result["result"], "failureReason": result.get("failureReason"),
                "stepResults": result["stepResults"],
                "events": [x["eventType"] for x in result["events"]],
                "afterTemplateStatus": api(f"/baseline-templates/{template['id']}")["templateStatus"],
                "enableAfterFailure": enable_status(template["id"])}
        item["commandStatus"] = db.query(db.source,
            "SELECT command_type,command_status FROM tip_stage2_v14.device_commands "
            "WHERE task_id=" + str(task_id) + " ORDER BY id").splitlines()
        item["dbTask"] = db.query(db.source,
            "SELECT status,is_dry_run,failure_reason IS NOT NULL FROM tip_stage2_v14.tasks "
            "WHERE id=" + str(task_id))
        ev["cases"].append(item)
        local.request(simulator + "/control/scenario", "POST", {"scenarioResult": "SUCCESS"}, token=secret)
finally:
    try:
        ev["restore"]["scenario"] = local.request(simulator + "/control/scenario", "POST",
            {"scenarioResult": "SUCCESS"}, token=secret)["scenarioResult"]
    except Exception as error:
        ev["restore"]["scenarioError"] = str(error)
    try:
        api(f"/baseline-templates/{template['id']}/disable", "POST")
        ev["restore"]["templateStatus"] = api(f"/baseline-templates/{template['id']}")["templateStatus"]
    except Exception as error:
        ev["restore"]["templateError"] = str(error)
    ev["restore"]["agent"] = db.query(db.source,
        "SELECT agent_status,online_status,work_status,coalesce(current_task_id,0) "
        "FROM tip_stage2_v14.device_agents WHERE agent_code='" + agent["agentId"] + "'")
    ev["afterTaskCount"] = db.query(db.source, "SELECT count(*) FROM tip_stage2_v14.tasks")
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(ev, ensure_ascii=False))
