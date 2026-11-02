"""Reproduce V1.133 cancellation failure with an isolated no-feedback trial."""
import importlib.util
import json
import subprocess
import time
import urllib.error
import urllib.request
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


local = load("local_f009_v133_cancel", "scripts/local-test-environment.py")
local.BASE = "http://127.0.0.1:18129/api/v1"
db = load("db_f009_v133_cancel", "acceptance/stage2/db-isolation.py")
admin = local.API("配置管理员")
operator = local.API("运行操作员")
agent = next(x for x in admin("/device-agents?page=1&size=100")["content"]
             if x["deviceCode"] == "G126_ROBOT")
assert (agent["agentStatus"], agent["onlineStatus"], agent["workStatus"]) == ("ENABLED", "ONLINE", "IDLE")
secret = json.loads(local.protect((ROOT / ".local-test/gpt-f007-v126-robot.dpapi").read_bytes(), True))["token"]


def query(sql):
    return db.query(db.source, sql).splitlines()


def control(mode):
    return local.request("http://127.0.0.1:18132/device-api/v1/control/scenario", "POST",
                         {"scenarioResult": mode}, token=secret)["scenarioResult"]


def cancel_raw(template_id, task_id):
    url = local.BASE + f"/baseline-templates/{template_id}/dry-runs/{task_id}/cancel"
    request = urllib.request.Request(url, method="POST",
        headers={"Authorization": "Bearer " + admin.token})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read())
            return {"http": response.status, "code": body.get("code"), "message": body.get("message"),
                    "apiResult": (body.get("data") or {}).get("result")}
    except urllib.error.HTTPError as error:
        body = json.loads(error.read())
        return {"http": error.code, "code": body.get("code"), "message": body.get("message")}


stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
out = ROOT / "acceptance/stage3/evidence" / f"SRS_F009-V1.133-cancel-constraint-{stamp}.json"
name = "G133F009C" + uuid.uuid4().hex[:8].upper()
inputs = [{"name": "targetLocation", "type": "String", "required": True,
           "defaultValue": "F2_TEST_GATE"}]
step = {"capabilityType": "CAP_NAVIGATION", "stepTimeout": 60,
        "completionCondition": "routeGenerated=true and waypointCount reported",
        "paramMapping": [{"target": "targetLocation", "source": "TEMPLATE_INPUT.targetLocation"}]}
evidence = {"requirement": "SRS_F009", "productTag": "V1.133",
    "productSha": subprocess.check_output(["git", "rev-parse", "V1.133"], cwd=ROOT, text=True).strip(),
    "observedAt": datetime.now(timezone.utc).isoformat(),
    "environment": {"schema": SCHEMA, "backend": 18129, "simulator": 18132,
                    "templateName": name, "agent": agent["agentId"]},
    "constraint": query("SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                        f"WHERE conname='chk_op_log_result' AND conrelid='{SCHEMA}.operation_logs'::regclass"),
    "probe": {}, "cleanup": {}}
ident = None
task_id = None
try:
    template = admin("/baseline-templates", "POST", {"templateName": name,
        "templateIntent": "EXT_D9B16B94", "inputParams": inputs, "steps": [step]})
    ident = template["id"]
    evidence["probe"]["simulatorMode"] = control("NO_FEEDBACK")
    started = admin(f"/baseline-templates/{ident}/dry-run", "POST", {
        "inputParams": {}, "simulatedDevices": [{"stepSeq": 1, "agentId": agent["agentId"]}]})
    task_id = started["taskId"]
    evidence["probe"]["taskId"] = task_id
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        current = admin(f"/baseline-templates/{ident}/dry-runs/{task_id}")
        if any(x["eventType"] == "STEP_DISPATCHED" for x in current["events"]):
            break
        time.sleep(0.2)
    evidence["probe"]["dispatchedBeforeCancel"] = any(
        x["eventType"] == "STEP_DISPATCHED" for x in current["events"])
    evidence["probe"]["beforeCancelResult"] = current["result"]
    evidence["probe"]["cancelHttp"] = cancel_raw(ident, task_id)
    evidence["probe"]["afterCancel"] = {
        "taskStatus": query(f"SELECT status,is_dry_run FROM {SCHEMA}.tasks WHERE id={task_id}"),
        "events": query(f"SELECT event_type FROM {SCHEMA}.task_events WHERE task_id={task_id} ORDER BY id"),
        "commands": query(f"SELECT command_type,command_status FROM {SCHEMA}.device_commands "
                          f"WHERE task_id={task_id} ORDER BY id"),
        "resultOperations": query(f"SELECT operation_type,operation_result FROM {SCHEMA}.operation_logs "
                                  f"WHERE operation_type='BASELINE_TEMPLATE_DRY_RUN_RESULT' "
                                  f"AND detail::json->>'taskId'='{task_id}'"),
    }
finally:
    try:
        evidence["cleanup"]["simulatorMode"] = control("SUCCESS")
    except Exception as error:
        evidence["cleanup"]["simulatorError"] = str(error)
    if task_id is not None:
        try:
            task_status = query(f"SELECT status FROM {SCHEMA}.tasks WHERE id={task_id}")[0]
            if task_status in ("EXECUTING", "PENDING_ASSIGNMENT", "DOWNGRADING"):
                operator(f"/tasks/{task_id}/terminate", "POST",
                         {"reason": "GPT F009 isolated fixture cleanup", "confirmed": True})
            evidence["cleanup"]["taskStatus"] = query(
                f"SELECT status FROM {SCHEMA}.tasks WHERE id={task_id}")
        except Exception as error:
            evidence["cleanup"]["taskError"] = str(error)
    if ident is not None:
        try:
            admin(f"/baseline-templates/{ident}/disable", "POST")
            evidence["cleanup"]["templateStatus"] = admin(f"/baseline-templates/{ident}")["templateStatus"]
        except Exception as error:
            evidence["cleanup"]["templateError"] = str(error)
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(out)
print(json.dumps({"probe": evidence["probe"], "cleanup": evidence["cleanup"]}, ensure_ascii=False))
