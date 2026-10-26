"""Read-only evidence for the core oversize capability/definition mismatch."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
config, operator = local.API("配置管理员"), local.API("运行操作员")
definitions = config("/task-definitions")
oversize = next(d for d in definitions if d["definitionCode"] == "OVERSIZE_BAGGAGE_HANDLING")
flight = next(d for d in definitions if d["definitionCode"] == "FLIGHT_CHANGE_RESPONSE")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "schema": "tip_stage2_v14", "oversizeDefinition": oversize,
      "flightDefinition": flight,
      "task53": {"task": operator("/tasks/53"), "plans": operator("/tasks/53/plan-versions"),
                 "events": operator("/tasks/53/events")},
      "task55": {"task": operator("/tasks/55"), "plans": operator("/tasks/55/plan-versions"),
                 "events": operator("/tasks/55/events")}}
out = Path(__file__).parent / "evidence" / (
    "TC-039-task-definition-coverage-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"oversizeAvailableCapabilityTypes": oversize["availableCapabilityTypes"],
                  "flightAvailableCapabilityTypes": flight["availableCapabilityTypes"],
                  "task53AutonomousConstraint": next(p for p in ev["task53"]["plans"]
                      if p["source"] == "AUTONOMOUS")["constraintCheckResult"],
                  "task55AutonomousConstraint": next(p for p in ev["task55"]["plans"]
                      if p["source"] == "AUTONOMOUS")["constraintCheckResult"],
                  "evidence": str(out)}, ensure_ascii=False))
