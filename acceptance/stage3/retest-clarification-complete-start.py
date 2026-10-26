"""TC-032.S1 phase 1: submit a known-good fictional baggage goal with location omitted."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
db_spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(db_spec)
db_spec.loader.exec_module(db)
api = local.API("运行操作员")
source = api("/tasks/19")
assert source["status"] == "COMPLETED" and "F2_BAGGAGE_POINT" in source["taskGoal"]
goal = source["taskGoal"].replace("在F2_BAGGAGE_POINT测量", "在待补充的地点测量", 1)
assert goal != source["taskGoal"] and len(goal) <= 500
params = dict(source["sceneParams"])
params.pop("baggageLocation", None)
request = {"taskGoal": goal, "taskFamily": "OVERSIZE_BAGGAGE_HANDLING", "sceneParams": params}
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "sourceTaskId": 19, "request": request, "observations": {}}
before = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
try:
    ev["observations"]["submitResponse"] = api("/tasks", "POST", request)
except RuntimeError as error:
    ev["observations"]["submitError"] = str(error)
after = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
ev["observations"]["beforeMaxTaskId"] = before
ev["observations"]["afterMaxTaskId"] = after
if after > before:
    ev["observations"]["task"] = api(f"/tasks/{after}")
    ev["observations"]["events"] = api(f"/tasks/{after}/events")
(Path(__file__).parent / "evidence/TC-032-complete-start.json").write_text(
    json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"taskId": after if after > before else None,
                  "status": ev["observations"].get("task", {}).get("status"),
                  "questions": ev["observations"].get("task", {}).get("missingInfoQuestions")}, ensure_ascii=True))
