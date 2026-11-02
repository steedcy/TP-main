"""Independent F009 live dry-run probe on the GPT-owned schema and ports.

Writes new, redacted evidence. Existing stage-3 evidence is never overwritten.
"""
import importlib.util
import json
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "tip_gpt_f006_v118_20261030"
BASE = "http://127.0.0.1:18129/api/v1"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


local = module("local_f009", "scripts/local-test-environment.py")
local.BASE = BASE
db = module("db_f009", "acceptance/stage2/db-isolation.py")
config = local.API("配置管理员")
operator = local.API("运行操作员")


def query(sql):
    return db.query(db.source, sql).splitlines()


def count(sql):
    return int(query(sql)[0])


def snapshot():
    return {
        "formalCompleted": count(f"SELECT count(*) FROM {SCHEMA}.tasks WHERE status='COMPLETED' AND is_dry_run=FALSE"),
        "allCompleted": count(f"SELECT count(*) FROM {SCHEMA}.tasks WHERE status='COMPLETED'"),
        "formalCount": count(f"SELECT count(*) FROM {SCHEMA}.tasks WHERE is_dry_run=FALSE"),
        "dryRunCount": count(f"SELECT count(*) FROM {SCHEMA}.tasks WHERE is_dry_run=TRUE"),
        "dashboard": operator("/dashboard/overview")["metrics"]["statusCounts"],
    }


def wait_result(template_id, task_id):
    deadline = time.monotonic() + 55
    while time.monotonic() < deadline:
        result = config(f"/baseline-templates/{template_id}/dry-runs/{task_id}")
        if result["result"] != "RUNNING":
            return result
        time.sleep(0.5)
    return result


stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
out = ROOT / "acceptance/stage3/evidence" / f"SRS_F009-V1.132-live-{stamp}.json"
name = "G132F009" + uuid.uuid4().hex[:8].upper()
agent = next(a for a in config("/device-agents?page=1&size=100")["content"]
             if a["deviceCode"] == "G126_ROBOT")
assert (agent["agentStatus"], agent["onlineStatus"], agent["workStatus"]) == ("ENABLED", "ONLINE", "IDLE")
capability = next(c for c in config("/devices/G126_ROBOT/capabilities")
                  if c["capabilityType"] == "CAP_NAVIGATION")
assert capability["capabilityStatus"] == "ENABLED"
inputs = [{"name": "targetLocation", "type": "String", "required": True,
           "defaultValue": "F2_TEST_GATE"}]
steps = [{"capabilityType": "CAP_NAVIGATION", "stepTimeout": 60,
          "completionCondition": "routeGenerated=true and waypointCount reported",
          "paramMapping": [{"target": "targetLocation", "source": "TEMPLATE_INPUT.targetLocation"}]}]
evidence = {
    "requirement": "SRS_F009", "productTag": "V1.132",
    "productSha": subprocess.check_output(["git", "rev-parse", "V1.132"], cwd=ROOT, text=True).strip(),
    "observedAt": datetime.now(timezone.utc).isoformat(),
    "environment": {"schema": SCHEMA, "backend": 18129, "simulator": 18132,
                    "template": name, "agent": agent["agentId"]},
    "before": snapshot(), "observations": {},
}
template_id = None
try:
    template = config("/baseline-templates", "POST", {
        "templateName": name, "templateIntent": "EXT_D9B16B94",
        "inputParams": inputs, "steps": steps})
    template_id = template["id"]
    evidence["observations"]["created"] = {
        "templateId": template_id, "version": template["templateVersion"],
        "status": template["templateStatus"], "steps": template["steps"]}
    started = config(f"/baseline-templates/{template_id}/dry-run", "POST", {
        "inputParams": {}, "simulatedDevices": [{"stepSeq": 1, "agentId": agent["agentId"]}]})
    task_id = started["taskId"]
    result = wait_result(template_id, task_id)
    evidence["observations"]["run"] = {"taskId": task_id, "startedResult": started["result"],
        "result": result, "templateStatus": config(f"/baseline-templates/{template_id}")["templateStatus"]}
    evidence["observations"]["database"] = {
        "taskAndPlan": query(f"SELECT t.status,t.is_dry_run,p.source,p.snapshot_id FROM {SCHEMA}.tasks t "
                             f"JOIN {SCHEMA}.plan_versions p ON p.id=t.current_plan_version_id WHERE t.id={task_id}"),
        "commandTypesAndStatuses": query(f"SELECT command_type,command_status FROM {SCHEMA}.device_commands "
                                         f"WHERE task_id={task_id} ORDER BY id"),
        "assignment": query(f"SELECT step_seq,step_status,command_id,execute_command_id,reason_code "
                            f"FROM {SCHEMA}.task_step_assignments WHERE task_id={task_id}"),
        "operationLogs": query(f"SELECT operation_type,operation_result,operation_target,detail FROM {SCHEMA}.operation_logs "
                               f"WHERE operation_target LIKE '{name}%' ORDER BY id"),
    }
    if result["result"] == "SUCCESS":
        config(f"/baseline-templates/{template_id}/enable", "POST")
        evidence["observations"]["enabled"] = config(f"/baseline-templates/{template_id}")["templateStatus"]
        evidence["observations"]["database"]["operationLogsAfterEnable"] = query(
            f"SELECT operation_type,operation_result,operation_target FROM {SCHEMA}.operation_logs "
            f"WHERE operation_target LIKE '{name}%' ORDER BY id")
finally:
    evidence["after"] = snapshot()
    if template_id is not None:
        try:
            config(f"/baseline-templates/{template_id}/disable", "POST")
            evidence["cleanup"] = {"templateStatus": config(f"/baseline-templates/{template_id}")["templateStatus"]}
        except Exception as error:
            evidence["cleanup"] = {"error": str(error)}
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(out)
print(json.dumps({"before": evidence["before"], "after": evidence["after"],
                  "result": evidence["observations"].get("run", {}).get("result", {}).get("result"),
                  "logs": evidence["observations"].get("database", {}).get("operationLogsAfterEnable", [])},
                 ensure_ascii=False))
