"""Check the live preset capability set against two V1.5 planning outcomes."""
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
definition = next(item for item in config("/task-definitions")
                  if item["definitionCode"] == "OVERSIZE_BAGGAGE_HANDLING")
plans = {str(task_id): operator(f"/tasks/{task_id}/plan-versions") for task_id in (19, 86, 87)}
display_caps = config("/devices/SIM_F2_DISPLAY/capabilities")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "definition": definition,
      "displayCapabilities": display_caps,
      "tasks": {str(task_id): {"task": operator(f"/tasks/{task_id}"), "plans": plans[str(task_id)]}
                for task_id in (19, 86, 87)}}
name = ("TC-054-oversize-capability-contradiction-" +
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out = stage / "evidence" / name
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": name, "definitionCapabilities": definition["availableCapabilityTypes"],
                  "taskErrors": {key: plans[key][0]["validationErrors"] for key in plans}},
                 ensure_ascii=False))
