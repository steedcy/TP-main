"""F009 failure, version, preflight and cancellation probes on GPT-owned resources."""
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


local = load("local_f009b", "scripts/local-test-environment.py")
local.BASE = "http://127.0.0.1:18129/api/v1"
db = load("db_f009b", "acceptance/stage2/db-isolation.py")
api = local.API("配置管理员")
agent = next(a for a in api("/device-agents?page=1&size=100")["content"]
             if a["deviceCode"] == "G126_ROBOT")
assert (agent["agentStatus"], agent["onlineStatus"], agent["workStatus"]) == ("ENABLED", "ONLINE", "IDLE")
device_secret = json.loads(local.protect((ROOT / ".local-test/gpt-f007-v126-robot.dpapi").read_bytes(), True))["token"]
control = "http://127.0.0.1:18132/device-api/v1/control"


def scenario(value):
    return local.request(control + "/scenario", "POST", {"scenarioResult": value}, token=device_secret)["scenarioResult"]


def delay(value):
    return local.request(control + f"/delay?milliseconds={value}", "POST", token=device_secret)["milliseconds"]


def q(sql):
    return db.query(db.source, sql).splitlines()


def raw(path, method="POST", payload=None):
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    request = urllib.request.Request(local.BASE + path, body, method=method,
        headers={"Authorization": "Bearer " + api.token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            obj = json.loads(response.read())
            return {"http": response.status, "code": obj.get("code"), "message": obj.get("message")}
    except urllib.error.HTTPError as error:
        obj = json.loads(error.read())
        return {"http": error.code, "code": obj.get("code"), "message": obj.get("message")}


def wait(template_id, task_id, seconds=35):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = api(f"/baseline-templates/{template_id}/dry-runs/{task_id}")
        if result["result"] != "RUNNING":
            return result
        time.sleep(0.5)
    return result


def operation_rows(name):
    return q(f"SELECT operation_type,operation_result,operation_target,detail "
             f"FROM {SCHEMA}.operation_logs WHERE operation_target LIKE '{name}%' ORDER BY id")


stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
out = ROOT / "acceptance/stage3/evidence" / f"SRS_F009-V1.132-boundaries-{stamp}.json"
name = "G132F009B" + uuid.uuid4().hex[:8].upper()
inputs = [{"name": "targetLocation", "type": "String", "required": True}]
step = {"capabilityType": "CAP_NAVIGATION", "stepTimeout": 60,
        "completionCondition": "routeGenerated=true and waypointCount reported",
        "paramMapping": [{"target": "targetLocation", "source": "TEMPLATE_INPUT.targetLocation"}]}
evidence = {"requirement": "SRS_F009", "productTag": "V1.132",
    "productSha": subprocess.check_output(["git", "rev-parse", "V1.132"], cwd=ROOT, text=True).strip(),
    "observedAt": datetime.now(timezone.utc).isoformat(),
    "environment": {"schema": SCHEMA, "backend": 18129, "simulator": 18132,
                    "templatePrefix": name, "agent": agent["agentId"]},
    "guards": {}, "runs": [], "version": {}, "cancel": {}, "cleanup": {}}
created_ids = []

try:
    base = {"templateName": name, "templateIntent": "EXT_D9B16B94",
            "inputParams": inputs, "steps": [step]}
    before = int(q(f"SELECT count(*) FROM {SCHEMA}.tasks")[0])
    evidence["guards"]["sixSteps"] = raw("/baseline-templates", payload={**base,
        "templateName": name + "SIX", "steps": [step] * 6})
    unsafe = {**step, "paramMapping": step["paramMapping"] +
              [{"target": "maxSpeed", "source": "TEMPLATE_INPUT.targetLocation"}]}
    evidence["guards"]["motionSafety"] = raw("/baseline-templates", payload={**base,
        "templateName": name + "UNSAFE", "steps": [unsafe]})
    evidence["guards"]["capabilityGap"] = raw("/baseline-templates", payload={**base,
        "templateName": name + "GAP", "steps": [{**step, "capabilityType": "CAP_NOT_PRESENT"}]})
    template = api("/baseline-templates", "POST", base)
    template_id = template["id"]
    created_ids.append(template_id)
    evidence["guards"]["created"] = {"id": template_id, "version": template["templateVersion"],
                                      "status": template["templateStatus"]}
    path = f"/baseline-templates/{template_id}"
    evidence["guards"]["enableWithoutTrial"] = raw(path + "/enable")
    evidence["guards"]["missingInput"] = raw(path + "/dry-run", payload={
        "inputParams": {}, "simulatedDevices": [{"stepSeq": 1, "agentId": agent["agentId"]}]})
    evidence["guards"]["missingDevice"] = raw(path + "/dry-run", payload={
        "inputParams": {"targetLocation": "F2_TEST_GATE"}, "simulatedDevices": []})
    evidence["guards"]["wrongAgent"] = raw(path + "/dry-run", payload={
        "inputParams": {"targetLocation": "F2_TEST_GATE"},
        "simulatedDevices": [{"stepSeq": 1, "agentId": "AGT-NONEXISTENT"}]})
    evidence["guards"]["taskCountBeforeAfter"] = [before,
        int(q(f"SELECT count(*) FROM {SCHEMA}.tasks")[0])]

    for mode in ("FAILED", "TIMEOUT"):
        scenario(mode)
        started = api(path + "/dry-run", "POST", {"inputParams": {"targetLocation": "F2_TEST_GATE"},
            "simulatedDevices": [{"stepSeq": 1, "agentId": agent["agentId"]}]})
        result = wait(template_id, started["taskId"])
        evidence["runs"].append({"mode": mode, "taskId": started["taskId"], "result": result,
            "template": api(path)["templateStatus"], "enable": raw(path + "/enable"),
            "task": q(f"SELECT status,is_dry_run,failure_reason FROM {SCHEMA}.tasks WHERE id={started['taskId']}"),
            "operations": operation_rows(name)})
        scenario("SUCCESS")
    # The old failure result must not let a changed version inherit approval.
    updated = api(path, "PUT", {"inputParams": inputs, "steps": [step]})
    evidence["version"]["edited"] = [updated["templateVersion"], updated["templateStatus"]]
    evidence["version"]["enableBeforeRetest"] = raw(path + "/enable")
    started = api(path + "/dry-run", "POST", {"inputParams": {"targetLocation": "F2_TEST_GATE"},
        "simulatedDevices": [{"stepSeq": 1, "agentId": agent["agentId"]}]})
    result = wait(template_id, started["taskId"])
    evidence["version"]["retest"] = {"taskId": started["taskId"], "result": result["result"],
        "status": api(path)["templateStatus"]}
    if result["result"] == "SUCCESS":
        api(path + "/enable", "POST")
    evidence["version"]["afterEnable"] = api(path)["templateStatus"]
    evidence["version"]["operations"] = operation_rows(name)

    # Five valid steps are accepted; cancellation during step 1 must terminate
    # the active business command. Six steps were rejected above.
    five = api("/baseline-templates", "POST", {**base,
        "templateName": name + "FIVE", "steps": [step] * 5})
    five_id = five["id"]
    created_ids.append(five_id)
    delay(5000)
    started = api(f"/baseline-templates/{five_id}/dry-run", "POST", {
        "inputParams": {"targetLocation": "F2_TEST_GATE"},
        "simulatedDevices": [{"stepSeq": seq, "agentId": agent["agentId"]} for seq in range(1, 6)]})
    task_id = started["taskId"]
    evidence["cancel"]["started"] = {"taskId": task_id, "result": started["result"]}
    cancelled = api(f"/baseline-templates/{five_id}/dry-runs/{task_id}/cancel", "POST")
    evidence["cancel"]["result"] = cancelled
    evidence["cancel"]["commands"] = q(f"SELECT command_type,command_status FROM {SCHEMA}.device_commands "
                                         f"WHERE task_id={task_id} ORDER BY id")
    evidence["cancel"]["task"] = q(f"SELECT status,is_dry_run FROM {SCHEMA}.tasks WHERE id={task_id}")
    evidence["cancel"]["templateStatus"] = api(f"/baseline-templates/{five_id}")["templateStatus"]
finally:
    try:
        evidence["cleanup"]["scenario"] = scenario("SUCCESS")
        evidence["cleanup"]["delayMs"] = delay(500)
    except Exception as error:
        evidence["cleanup"]["simulatorError"] = str(error)
    for template_id in created_ids:
        try:
            api(f"/baseline-templates/{template_id}/disable", "POST")
            evidence["cleanup"][str(template_id)] = api(f"/baseline-templates/{template_id}")["templateStatus"]
        except Exception as error:
            evidence["cleanup"][str(template_id)] = str(error)
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(out)
print(json.dumps({"guards": evidence["guards"],
    "runs": [{"mode": x["mode"], "result": x["result"]["result"], "template": x["template"]} for x in evidence["runs"]],
    "version": {k: v for k, v in evidence["version"].items() if k != "operations"},
    "cancel": {"result": evidence["cancel"].get("result", {}).get("result"),
               "commands": evidence["cancel"].get("commands")},
    "cleanup": evidence["cleanup"]}, ensure_ascii=False))
