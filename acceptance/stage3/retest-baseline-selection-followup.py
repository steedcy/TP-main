"""Read the selected template and immutable original goal after task 83's controlled downgrade."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
operator, config = local.API("运行操作员"), local.API("配置管理员")
before = json.loads((stage / "evidence/TC-050-baseline-failure-20261027T042130Z.json")
                    .read_text(encoding="utf-8"))
task_id = before["task"]["id"]
task = operator(f"/tasks/{task_id}")
plans = operator(f"/tasks/{task_id}/plan-versions")
templates = [t for t in config("/baseline-templates")
             if t["templateIntent"] == "OVERSIZE_BAGGAGE_HANDLING" and t["templateStatus"] == "ENABLED"]
events = operator(f"/tasks/{task_id}/events")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "taskId": task_id,
      "originalRequestGoal": before["request"]["taskGoal"],
      "taskGoalAfterCleanup": task["taskGoal"], "taskStatusAfterCleanup": task["status"],
      "plans": plans, "enabledBaggageTemplates": templates,
      "downgradeEvents": [e for e in events if e["eventType"] == "BASELINE_DOWNGRADED"],
      "priorSourceEvidence": "TC-050-baseline-failure-20261027T042130Z.json"}
out = stage / "evidence" / ("TC-050-baseline-selection-followup-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": out.name, "originalGoalPreserved":
                  ev["originalRequestGoal"] == ev["taskGoalAfterCleanup"],
                  "enabledTemplateVersions": [t["templateVersion"] for t in templates],
                  "planSources": [p["source"] for p in plans],
                  "baselineChecks": [{k: p[k] for k in
                    ("structureCheckResult", "capabilityCheckResult", "constraintCheckResult")}
                    for p in plans if p["source"] == "BASELINE_TEMPLATE"],
                  "downgradeEvents": len(ev["downgradeEvents"])}, ensure_ascii=False))
