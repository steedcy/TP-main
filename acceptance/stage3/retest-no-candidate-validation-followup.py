"""Correlate task 91's context, validators, skipped channels, and final state."""
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
config = local.API("配置管理员")
task_id = 91
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "task": operator(f"/tasks/{task_id}"),
      "contextSnapshots": operator(f"/tasks/{task_id}/context-snapshots"),
      "plans": operator(f"/tasks/{task_id}/plan-versions"),
      "assignments": operator(f"/tasks/{task_id}/step-assignments"),
      "events": operator(f"/tasks/{task_id}/events"),
      "currentOriginalAgents": [x for x in config("/device-agents?page=1&size=100")["content"]
                                if x["deviceCode"].startswith("SIM_F2_")]}
out = stage / "evidence" / ("TC-041-no-candidate-validation-followup-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": out.name, "taskStatus": ev["task"]["status"],
                  "contextCount": len(ev["contextSnapshots"]),
                  "checks": [{k: p[k] for k in ("source", "structureCheckResult",
                      "capabilityCheckResult", "constraintCheckResult")} for p in ev["plans"]],
                  "assignmentStatuses": [x["stepStatus"] for x in ev["assignments"]]},
                 ensure_ascii=False))
