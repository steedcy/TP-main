"""TC-028/030 one-step live simulator dry-runs and version/enable lifecycle."""
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
assert name not in {x["templateName"] for x in api("/baseline-templates")}
agent = next(x for x in api("/device-agents?page=1&size=100")["content"]
             if x["deviceCode"] == "SIM_F2_DISPLAY")
assert [agent["agentStatus"], agent["onlineStatus"], agent["workStatus"]] == ["ENABLED", "ONLINE", "IDLE"]
assert db.query(db.source, "SELECT count(*) FROM tip_stage2_v14.device_agents WHERE current_task_id IS NOT NULL") == "0"
inputs = [
    {"name": "contentType", "type": "String", "required": True, "defaultValue": "TEXT"},
    {"name": "contentData", "type": "String", "required": True, "defaultValue": "阶段三试运行信息"},
    {"name": "displayDuration", "type": "Integer", "required": True, "defaultValue": "60"},
]
steps = [{"capabilityType": "CAP_INFO_DISPLAY", "stepTimeout": 60,
          "completionCondition": "displayStatus=SUCCESS", "paramMapping": [
              {"target": x["name"], "source": "TEMPLATE_INPUT." + x["name"]} for x in inputs]}]
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "templateName": name, "deviceCode": "SIM_F2_DISPLAY", "runs": [], "lifecycle": {},
      "beforeTaskCount": db.query(db.source, "SELECT count(*) FROM tip_stage2_v14.tasks"),
      "beforeFormalCompleted": db.query(db.source,
          "SELECT count(*) FROM tip_stage2_v14.tasks WHERE status='COMPLETED' AND is_dry_run=false")}
out = Path(__file__).resolve().parent / "evidence/TC-028-030-baseline-dryrun-lifecycle.json"


def trial(template_id):
    result = api(f"/baseline-templates/{template_id}/dry-run", "POST",
        {"inputParams": {}, "simulatedDevices": [{"stepSeq": 1, "agentId": agent["agentId"]}]})
    task_id = result["taskId"]
    deadline = time.monotonic() + 45
    while result["result"] == "RUNNING" and time.monotonic() < deadline:
        time.sleep(1)
        result = api(f"/baseline-templates/{template_id}/dry-runs/{task_id}")
    summary = {"taskId": task_id, "taskCode": result["taskCode"], "result": result["result"],
               "stepResults": result["stepResults"], "events": [x["eventType"] for x in result["events"]],
               "failureReason": result.get("failureReason")}
    summary["database"] = db.query(db.source,
        "SELECT t.is_dry_run,t.status,p.source,p.snapshot_id,"
        "(SELECT count(*) FROM tip_stage2_v14.task_events e WHERE e.task_id=t.id) "
        "FROM tip_stage2_v14.tasks t JOIN tip_stage2_v14.plan_versions p "
        "ON p.id=t.current_plan_version_id WHERE t.id=" + str(task_id))
    return summary


ident = None
try:
    created = api("/baseline-templates", "POST", {"templateName": name,
        "templateIntent": "OVERSIZE_BAGGAGE_HANDLING", "inputParams": inputs, "steps": steps})
    ident = created["id"]
    ev["lifecycle"]["created"] = [created["templateVersion"], created["templateStatus"]]
    first = trial(ident)
    ev["runs"].append(first)
    ev["lifecycle"]["afterFirstTrial"] = [x for x in (api(f"/baseline-templates/{ident}")[k]
                                                 for k in ("templateVersion", "templateStatus"))]
    if first["result"] == "SUCCESS":
        api(f"/baseline-templates/{ident}/enable", "POST")
        ev["lifecycle"]["afterFirstEnable"] = api(f"/baseline-templates/{ident}")["templateStatus"]
        edited = api(f"/baseline-templates/{ident}", "PUT", {"inputParams": inputs, "steps": steps})
        ev["lifecycle"]["afterEdit"] = [edited["templateVersion"], edited["templateStatus"]]
        try:
            api(f"/baseline-templates/{ident}/enable", "POST")
            ev["lifecycle"]["enableEditedWithoutTrial"] = "ACCEPTED"
        except Exception as error:
            ev["lifecycle"]["enableEditedWithoutTrial"] = str(error)
        second = trial(ident)
        ev["runs"].append(second)
        ev["lifecycle"]["afterSecondTrial"] = [api(f"/baseline-templates/{ident}")[k]
                                                  for k in ("templateVersion", "templateStatus")]
        if second["result"] == "SUCCESS":
            api(f"/baseline-templates/{ident}/enable", "POST")
            ev["lifecycle"]["afterSecondEnable"] = api(f"/baseline-templates/{ident}")["templateStatus"]
    logs = api("/operation-logs?page=1&size=100")["content"]
    ev["lifecycle"]["auditTypes"] = sorted({x["operationType"] for x in logs
        if name in str(x.get("operationTarget", ""))})
finally:
    if ident is not None:
        try:
            api(f"/baseline-templates/{ident}/disable", "POST")
            ev["lifecycle"]["finalTemplateStatus"] = api(f"/baseline-templates/{ident}")["templateStatus"]
        except Exception as error:
            ev["lifecycle"]["disableError"] = str(error)
    ev["afterTaskCount"] = db.query(db.source, "SELECT count(*) FROM tip_stage2_v14.tasks")
    ev["afterFormalCompleted"] = db.query(db.source,
        "SELECT count(*) FROM tip_stage2_v14.tasks WHERE status='COMPLETED' AND is_dry_run=false")
    ev["agentAfter"] = db.query(db.source,
        "SELECT agent_status,online_status,work_status,coalesce(current_task_id,0) "
        "FROM tip_stage2_v14.device_agents WHERE agent_code='" + agent["agentId"] + "'")
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(ev, ensure_ascii=False))
