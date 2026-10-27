"""Capture current task 83 detail and timeline for TC-063.S2 after service restart."""
import hashlib
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
task = operator("/tasks/83")
events = operator("/tasks/83/events")
plans = operator("/tasks/83/plan-versions")
assignments = operator("/tasks/83/step-assignments")
assert task["id"] == 83 and isinstance(events, list) and isinstance(plans, list)
evidence = {
    "observedAt": datetime.now(timezone.utc).isoformat(),
    "runtimeInput": "V1.5",
    "isolatedSchema": "tip_stage2_v14",
    "task": {key: task.get(key) for key in
             ("id", "taskCode", "taskGoal", "status", "downgradeReason", "failureReason",
              "currentPlanVersionId")},
    "planVersions": [{key: plan.get(key) for key in
                      ("id", "versionNo", "source", "frozenAt", "baselineTemplateId")}
                     for plan in plans],
    "assignments": [{key: row.get(key) for key in
                     ("id", "stepSeq", "agentId", "status", "retryCount", "executionResult")}
                    for row in assignments],
    "events": events,
    "eventsSha256": hashlib.sha256(json.dumps(events, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
}
name = "TC-063-task83-detail-api-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json"
out = stage / "evidence" / name
out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": name, "taskStatus": task["status"],
                  "eventCount": len(events), "planCount": len(plans),
                  "assignmentCount": len(assignments)}, ensure_ascii=False))
