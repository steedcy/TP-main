"""Capture the operator API values behind TC-048.S2 downgrade detail views."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
operator = local.API("运行操作员")
evidence = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
            "isolatedSchema": "tip_stage2_v14", "tasks": []}
for task_id in (19, 83):
    task = operator(f"/tasks/{task_id}")
    plans = operator(f"/tasks/{task_id}/plan-versions")
    baseline = next(plan for plan in plans if plan["source"] == "BASELINE_TEMPLATE")
    template = operator(f"/baseline-templates/{baseline['baselineTemplateId']}")
    evidence["tasks"].append({
        "taskId": task_id,
        "task": {key: task.get(key) for key in
                 ("id", "taskCode", "taskGoal", "status", "downgradeReason",
                  "failureReason", "currentPlanVersionId")},
        "plans": [{key: plan.get(key) for key in
                   ("id", "versionNo", "source", "baselineTemplateId", "frozenAt",
                    "structureCheckResult", "capabilityCheckResult", "constraintCheckResult")}
                  for plan in plans],
        "baselineTemplate": {key: template.get(key) for key in
                             ("id", "templateName", "name", "version", "templateVersion",
                              "status", "enabled", "taskFamily")},
    })
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
name = f"TC-048-downgrade-detail-api-{stamp}.json"
out = stage / "evidence" / name
out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": name, "tasks": [
    {"taskId": item["taskId"], "baselineTemplate": item["baselineTemplate"],
     "plans": [(p["versionNo"], p["source"]) for p in item["plans"]]}
    for item in evidence["tasks"]]}, ensure_ascii=False))
