"""F009 invalid persisted draft and five-step in-execution cancellation."""
import importlib.util
import json
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "tip_gpt_f006_v118_20261030"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


local = load("local_f009c", "scripts/local-test-environment.py")
local.BASE = "http://127.0.0.1:18129/api/v1"
db = load("db_f009c", "acceptance/stage2/db-isolation.py")
api = local.API("配置管理员")
agent = next(a for a in api("/device-agents?page=1&size=100")["content"]
             if a["deviceCode"] == "G126_ROBOT")
secret = json.loads(local.protect((ROOT / ".local-test/gpt-f007-v126-robot.dpapi").read_bytes(), True))["token"]
control = "http://127.0.0.1:18132/device-api/v1/control"


def q(sql):
    return db.query(db.source, sql).splitlines()


def raw(path, payload):
    request = urllib.request.Request(local.BASE + path,
        json.dumps(payload).encode(), method="POST",
        headers={"Authorization": "Bearer " + api.token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            obj = json.loads(response.read())
            return {"http": response.status, "code": obj.get("code"), "message": obj.get("message")}
    except urllib.error.HTTPError as error:
        obj = json.loads(error.read())
        return {"http": error.code, "code": obj.get("code"), "message": obj.get("message")}


stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
out = ROOT / "acceptance/stage3/evidence" / f"SRS_F009-V1.132-cancel-{stamp}.json"
evidence = {"requirement": "SRS_F009", "productTag": "V1.132",
    "productSha": subprocess.check_output(["git", "rev-parse", "V1.132"], cwd=ROOT, text=True).strip(),
    "observedAt": datetime.now(timezone.utc).isoformat(),
    "environment": {"schema": SCHEMA, "backend": 18129, "simulator": 18132,
                    "agent": agent["agentId"]}, "invalidDraft": {}, "cancel": {}, "cleanup": {}}

template = api("/baseline-templates/1")
assert template["templateStatus"] == "DRAFT" and template["steps"] == []
before = int(q(f"SELECT count(*) FROM {SCHEMA}.tasks")[0])
evidence["invalidDraft"] = {"templateId": 1, "status": "DRAFT", "steps": 0,
    "result": raw("/baseline-templates/1/dry-run", {"inputParams": {"baggageLocation": "F2_TEST_GATE"},
        "simulatedDevices": [{"stepSeq": 1, "agentId": agent["agentId"]}]}),
    "taskCountBefore": before, "taskCountAfter": int(q(f"SELECT count(*) FROM {SCHEMA}.tasks")[0])}

# Reuse the newest GPT-owned five-step template created by the boundary probe.
five = max((t for t in api("/baseline-templates")
            if t["templateName"].startswith("G132F009B") and t["templateName"].endswith("FIVE")
            and len(t["steps"]) == 5), key=lambda t: t["id"])
template_id = five["id"]
try:
    local.request(control + "/scenario", "POST", {"scenarioResult": "SUCCESS"}, token=secret)
    local.request(control + "/delay?milliseconds=8000", "POST", token=secret)
    edited = api(f"/baseline-templates/{template_id}", "PUT",
                 {"inputParams": five["inputParams"], "steps": five["steps"]})
    evidence["cancel"]["templateVersion"] = edited["templateVersion"]
    started = api(f"/baseline-templates/{template_id}/dry-run", "POST", {
        "inputParams": {"targetLocation": "F2_TEST_GATE"},
        "simulatedDevices": [{"stepSeq": seq, "agentId": agent["agentId"]} for seq in range(1, 6)]})
    task_id = started["taskId"]
    evidence["cancel"]["taskId"] = task_id
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        current = api(f"/baseline-templates/{template_id}/dry-runs/{task_id}")
        if any(x["eventType"] == "STEP_DISPATCHED" for x in current["events"]):
            break
        time.sleep(0.2)
    evidence["cancel"]["beforeCancelResult"] = current["result"]
    evidence["cancel"]["dispatchedBeforeCancel"] = any(x["eventType"] == "STEP_DISPATCHED" for x in current["events"])
    cancelled = api(f"/baseline-templates/{template_id}/dry-runs/{task_id}/cancel", "POST")
    time.sleep(1)
    final = api(f"/baseline-templates/{template_id}/dry-runs/{task_id}")
    evidence["cancel"]["cancelResult"] = cancelled["result"]
    evidence["cancel"]["finalResult"] = final
    evidence["cancel"]["task"] = q(f"SELECT status,is_dry_run FROM {SCHEMA}.tasks WHERE id={task_id}")
    evidence["cancel"]["commands"] = q(f"SELECT command_type,command_status,command_id FROM {SCHEMA}.device_commands "
                                       f"WHERE task_id={task_id} ORDER BY id")
    evidence["cancel"]["agentAfter"] = api("/device-agents?page=1&size=100")["content"]
finally:
    local.request(control + "/delay?milliseconds=500", "POST", token=secret)
    local.request(control + "/scenario", "POST", {"scenarioResult": "SUCCESS"}, token=secret)
    api(f"/baseline-templates/{template_id}/disable", "POST")
    evidence["cleanup"] = {"delayMs": 500, "scenario": "SUCCESS",
                           "templateStatus": api(f"/baseline-templates/{template_id}")["templateStatus"]}
    # Keep only the test agent's non-secret state in tracked evidence.
    evidence["cancel"].pop("agentAfter", None)
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(out)
print(json.dumps({"invalidDraft": evidence["invalidDraft"],
    "cancel": {"dispatched": evidence["cancel"].get("dispatchedBeforeCancel"),
               "before": evidence["cancel"].get("beforeCancelResult"),
               "after": evidence["cancel"].get("cancelResult"),
               "commands": [x.split("|")[0:2] for x in evidence["cancel"].get("commands", [])]},
    "cleanup": evidence["cleanup"]}, ensure_ascii=False))
