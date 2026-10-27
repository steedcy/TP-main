"""Inspect current V1.5 task-detail candidates without changing task state."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("运行操作员")
page = api("/tasks?page=1&size=100")
assert isinstance(page["content"], list)
rows = []
for item in page["content"]:
    task = api(f"/tasks/{item['id']}")
    rows.append({key: task.get(key) for key in (
        "id", "taskCode", "status", "taskFamily", "replanUsed", "replanningReason",
        "downgradeReason", "failureReason", "currentPlanVersionId")})
out = stage / "evidence" / ("TC-063-task-detail-candidates-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps({"observedAt": datetime.now(timezone.utc).isoformat(),
                           "runtimeInput": "V1.5", "isolatedSchema": "tip_stage2_v14",
                           "totalElements": page["totalElements"], "rows": rows},
                          ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "taskCount": len(rows),
                  "replanned": [r for r in rows if r["replanUsed"] or r["replanningReason"]]},
                 ensure_ascii=False))
