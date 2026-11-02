"""Independent V1.134 dry-run result regression on GPT-owned services."""
import importlib.util
import json
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "tip_gpt_f006_v118_20261030"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


local = load("local_f009_v134", "scripts/local-test-environment.py")
local.BASE = "http://127.0.0.1:18129/api/v1"
db = load("db_f009_v134", "acceptance/stage2/db-isolation.py")
admin = local.API("配置管理员")
operator = local.API("运行操作员")
agent = next(x for x in admin("/device-agents?page=1&size=100")["content"]
             if x["deviceCode"] == "G126_ROBOT")
assert (agent["agentStatus"], agent["onlineStatus"], agent["workStatus"]) == ("ENABLED", "ONLINE", "IDLE")
secret = json.loads(local.protect((ROOT / ".local-test/gpt-f007-v126-robot.dpapi").read_bytes(), True))["token"]
control = "http://127.0.0.1:18132/device-api/v1/control"


def query(sql):
    return db.query(db.source, sql).splitlines()


def snapshot():
    return {"formalCompleted": int(query(f"SELECT count(*) FROM {SCHEMA}.tasks "
                                          "WHERE status='COMPLETED' AND is_dry_run=FALSE")[0]),
            "allCompleted": int(query(f"SELECT count(*) FROM {SCHEMA}.tasks WHERE status='COMPLETED'")[0]),
            "dashboardCompleted": operator("/dashboard/overview")["metrics"]["statusCounts"]["COMPLETED"]}


def set_mode(mode):
    return local.request(control + "/scenario", "POST", {"scenarioResult": mode}, token=secret)["scenarioResult"]


def set_delay(ms):
    return local.request(control + f"/delay?milliseconds={ms}", "POST", token=secret)["milliseconds"]


def wait_result(template_id, task_id, seconds=40):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = admin(f"/baseline-templates/{template_id}/dry-runs/{task_id}")
        if result["result"] != "RUNNING":
            return result
        time.sleep(0.5)
    return result


def result_record(task_id):
    rows = query(f"SELECT operation_type,operation_result,detail::json->>'taskId',"
                 f"detail::json->>'templateVersion',detail::json->>'result' "
                 f"FROM {SCHEMA}.operation_logs WHERE operation_type='BASELINE_TEMPLATE_DRY_RUN_RESULT' "
                 f"AND detail::json->>'taskId'='{task_id}' ORDER BY id")
    return rows


def capture(template_id, task_id):
    result = admin(f"/baseline-templates/{template_id}/dry-runs/{task_id}")
    return {"taskId": task_id, "apiResult": result["result"], "failureReason": result.get("failureReason"),
            "stepResults": result["stepResults"],
            "events": [x["eventType"] for x in result["events"]],
            "taskStatus": query(f"SELECT status,is_dry_run FROM {SCHEMA}.tasks WHERE id={task_id}"),
            "plan": query(f"SELECT source,snapshot_id FROM {SCHEMA}.plan_versions WHERE task_id={task_id}"),
            "resultOperations": result_record(task_id),
            "commands": query(f"SELECT command_type,command_status,command_id,"
                              f"response_payload IS NOT NULL FROM {SCHEMA}.device_commands "
                              f"WHERE task_id={task_id} ORDER BY id"),
            "templateStatus": admin(f"/baseline-templates/{template_id}")["templateStatus"]}


stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
out = ROOT / "acceptance/stage3/evidence" / f"SRS_F009-V1.134-results-{stamp}.json"
name = "G134F009" + uuid.uuid4().hex[:8].upper()
inputs = [{"name": "targetLocation", "type": "String", "required": True,
           "defaultValue": "F2_TEST_GATE"}]
step = {"capabilityType": "CAP_NAVIGATION", "stepTimeout": 60,
        "completionCondition": "routeGenerated=true and waypointCount reported",
        "paramMapping": [{"target": "targetLocation", "source": "TEMPLATE_INPUT.targetLocation"}]}
payload = {"inputParams": {}, "simulatedDevices": [{"stepSeq": 1, "agentId": agent["agentId"]}]}
evidence = {"requirement": "SRS_F009", "productTag": "V1.134",
    "productSha": subprocess.check_output(["git", "rev-parse", "V1.134"], cwd=ROOT, text=True).strip(),
    "observedAt": datetime.now(timezone.utc).isoformat(),
    "environment": {"schema": SCHEMA, "backend": 18129, "simulator": 18132,
                    "templatePrefix": name, "agent": agent["agentId"]},
    "before": snapshot(), "success": {}, "failed": {}, "timeout": {}, "cancel": {},
    "after": {}, "cleanup": {}}
created = []
try:
    template = admin("/baseline-templates", "POST", {"templateName": name,
        "templateIntent": "EXT_D9B16B94", "inputParams": inputs, "steps": [step]})
    ident = template["id"]
    created.append(ident)
    set_mode("SUCCESS")
    started = admin(f"/baseline-templates/{ident}/dry-run", "POST", payload)
    wait_result(ident, started["taskId"])
    evidence["success"] = capture(ident, started["taskId"])
    assert evidence["success"]["apiResult"] == "SUCCESS"
    admin(f"/baseline-templates/{ident}/enable", "POST")
    evidence["success"]["enabledStatus"] = admin(f"/baseline-templates/{ident}")["templateStatus"]
    evidence["success"]["enableOperation"] = query(
        f"SELECT operation_type,operation_result FROM {SCHEMA}.operation_logs "
        f"WHERE operation_type='BASELINE_TEMPLATE_ENABLE' AND operation_target='{name}' ORDER BY id DESC LIMIT 1")
    for mode, key in (("FAILED", "failed"), ("TIMEOUT", "timeout")):
        updated = admin(f"/baseline-templates/{ident}", "PUT", {"inputParams": inputs, "steps": [step]})
        set_mode(mode)
        started = admin(f"/baseline-templates/{ident}/dry-run", "POST", payload)
        wait_result(ident, started["taskId"])
        evidence[key] = capture(ident, started["taskId"])
        evidence[key]["templateVersion"] = updated["templateVersion"]
        set_mode("SUCCESS")
    five = admin("/baseline-templates", "POST", {"templateName": name + "FIVE",
        "templateIntent": "EXT_D9B16B94", "inputParams": inputs, "steps": [step] * 5})
    five_id = five["id"]
    created.append(five_id)
    set_delay(8000)
    five_payload = {"inputParams": {}, "simulatedDevices": [
        {"stepSeq": seq, "agentId": agent["agentId"]} for seq in range(1, 6)]}
    started = admin(f"/baseline-templates/{five_id}/dry-run", "POST", five_payload)
    task_id = started["taskId"]
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        current = admin(f"/baseline-templates/{five_id}/dry-runs/{task_id}")
        if any(x["eventType"] == "STEP_DISPATCHED" for x in current["events"]):
            break
        time.sleep(0.2)
    evidence["cancel"]["dispatchedBeforeCancel"] = any(
        x["eventType"] == "STEP_DISPATCHED" for x in current["events"])
    evidence["cancel"]["apiCancelResponse"] = admin(
        f"/baseline-templates/{five_id}/dry-runs/{task_id}/cancel", "POST")["result"]
    time.sleep(1)
    evidence["cancel"].update(capture(five_id, task_id))
    evidence["cancel"]["agentAfter"] = next(x for x in admin("/device-agents?page=1&size=100")["content"]
                                              if x["agentId"] == agent["agentId"])["workStatus"]
    evidence["after"] = snapshot()
finally:
    try:
        evidence["cleanup"]["scenario"] = set_mode("SUCCESS")
        evidence["cleanup"]["delayMs"] = set_delay(500)
    except Exception as error:
        evidence["cleanup"]["simulatorError"] = str(error)
    for ident in created:
        try:
            admin(f"/baseline-templates/{ident}/disable", "POST")
            evidence["cleanup"][str(ident)] = admin(f"/baseline-templates/{ident}")["templateStatus"]
        except Exception as error:
            evidence["cleanup"][str(ident)] = str(error)
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(out)
print(json.dumps({key: {"api": evidence[key].get("apiResult"),
                        "events": evidence[key].get("events"),
                        "resultLogs": evidence[key].get("resultOperations"),
                        "commands": [x.split("|")[:2] for x in evidence[key].get("commands", [])]}
                  for key in ("success", "failed", "timeout", "cancel")}, ensure_ascii=False))
