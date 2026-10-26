"""Corroborate the operator-visible supervision and baseline fields for task 55."""
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
task = operator("/tasks/55")
versions = operator("/tasks/55/plan-versions")
events = operator("/tasks/55/events")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "taskId": 55,
      "task": {key: task.get(key) for key in
               ("id", "taskCode", "status", "currentPlanVersionId", "downgradeReason", "failureReason")},
      "versions": [{key: version.get(key) for key in
                    ("id", "versionNo", "source", "riskLevel", "riskReasonCode", "judgmentBasis",
                     "confidence", "ruleSetVersion", "frozenAt")}
                   for version in versions],
      "decisionEvents": [{"eventType": event["eventType"], "occurredAt": event["occurredAt"],
                          "detailSummary": event.get("detailSummary")}
                         for event in events if event["eventType"] in
                         ("SUPERVISION_DECIDED", "SUPERVISION_JUDGED", "BASELINE_DOWNGRADED",
                          "PLAN_SUPERVISED", "SUPERVISION_RESULT")]}
out = stage / "evidence/SRS_F020-R02-supervision-task55-api.json"
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"taskId": ev["taskId"], "status": ev["task"]["status"],
                  "versions": [(v["versionNo"], v["source"], v["riskReasonCode"]) for v in ev["versions"]],
                  "decisionEvents": [v["eventType"] for v in ev["decisionEvents"]]}, ensure_ascii=False))
