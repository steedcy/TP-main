"""TC-029 fresh dry-run preflight rejection checks without launching tasks."""
import importlib.util
import json
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
name = "S3_TC029_DRYRUN_GUARD"
assert name not in {x["templateName"] for x in api("/baseline-templates")}
agents = {x["deviceCode"]: x["agentId"] for x in api("/device-agents?page=1&size=100")["content"]}
input_defs = [
    {"name": "contentType", "type": "String", "required": True, "defaultValue": "TEXT"},
    {"name": "contentData", "type": "String", "required": True},
    {"name": "displayDuration", "type": "Integer", "required": True, "defaultValue": "60"},
]
step = {"capabilityType": "CAP_INFO_DISPLAY", "stepTimeout": 60,
        "completionCondition": "displayStatus=SUCCESS", "paramMapping": [
            {"target": x["name"], "source": "TEMPLATE_INPUT." + x["name"]} for x in input_defs]}
before_tasks = db.query(db.source, "SELECT count(*) FROM tip_stage2_v14.tasks")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "templateName": name, "beforeTaskCount": before_tasks, "guards": {}, "cleanup": {}}


def raw(path, method="POST", payload=None):
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    request = urllib.request.Request(local.BASE + path, method=method, data=body,
        headers={"Authorization": "Bearer " + api.token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read()).get("message")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read()).get("message")


ident = None
try:
    created = api("/baseline-templates", "POST", {"templateName": name,
        "templateIntent": "OVERSIZE_BAGGAGE_HANDLING", "inputParams": input_defs, "steps": [step]})
    ident = created["id"]
    ev["createdStatus"] = created["templateStatus"]
    ev["guards"]["enableWithoutTrial"] = raw(f"/baseline-templates/{ident}/enable")
    path = f"/baseline-templates/{ident}/dry-run"
    cases = {
        "emptySelections": {"inputParams": {"contentData": "stage3"}, "simulatedDevices": []},
        "missingRequiredInput": {"inputParams": {},
            "simulatedDevices": [{"stepSeq": 1, "agentId": agents["SIM_F2_DISPLAY"]}]},
        "missingSelectedAgent": {"inputParams": {"contentData": "stage3"},
            "simulatedDevices": [{"stepSeq": 1, "agentId": None}]},
        "mismatchedAgent": {"inputParams": {"contentData": "stage3"},
            "simulatedDevices": [{"stepSeq": 1, "agentId": agents["SIM_F2_BAGGAGE"]}]},
    }
    for label, payload in cases.items():
        ev["guards"][label] = raw(path, payload=payload)
    ev["afterGuardTaskCount"] = db.query(db.source, "SELECT count(*) FROM tip_stage2_v14.tasks")
    ev["afterGuardStatus"] = api("/baseline-templates/" + str(ident))["templateStatus"]
finally:
    if ident is not None:
        try:
            api("/baseline-templates/" + str(ident), "DELETE")
        except Exception as error:
            ev["cleanup"]["deleteError"] = str(error)
    ev["cleanup"]["nameAbsent"] = name not in {x["templateName"] for x in api("/baseline-templates")}
    out = Path(__file__).resolve().parent / "evidence/TC-029-baseline-dryrun-guards.json"
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(ev, ensure_ascii=False))
