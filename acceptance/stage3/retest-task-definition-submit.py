"""Fresh boundary and dynamic required-parameter submission for TC-031/068."""
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
definition_ev = json.loads((Path(__file__).parent / "evidence/TC-068-dynamic-definition-api.json").read_text(encoding="utf-8"))
code = definition_ev["observations"]["definitionCode"]
api = local.API("运行操作员")
out = Path(__file__).parent / "evidence/TC-031-068-dynamic-submit.json"
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "definitionCode": code, "requests": {}, "observations": {}}

def submit(label, payload):
    try:
        response = local.request(local.BASE + "/tasks", "POST", payload, api.token)
        ev["requests"][label] = {"request": payload, "http": 200, "response": response}
    except RuntimeError as error:
        ev["requests"][label] = {"request": payload, "error": str(error)}

before = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
ev["observations"]["beforeMaxTaskId"] = before
submit("blankGoal", {"taskGoal": "", "taskFamily": code})
submit("longGoal", {"taskGoal": "测" * 501, "taskFamily": code})
ev["observations"]["afterInvalidMaxTaskId"] = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
assert ev["observations"]["afterInvalidMaxTaskId"] == before

# The definition marks sampleLocation required; the submitted payload omits it.
# It should be rejected before task creation and before a model call.
submit("missingRequiredSceneParam", {"taskGoal": "测", "taskFamily": code, "sceneParams": {}})
after = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
ev["observations"]["afterMissingMaxTaskId"] = after
if after > before:
    task = api(f"/tasks/{after}")
    ev["observations"]["createdTask"] = task
    ev["observations"]["events"] = api(f"/tasks/{after}/events")
    if task["status"] == "PLANNING":
        ev["observations"]["cleanupCancel"] = api(f"/tasks/{after}/cancel", "POST", {"reason": "阶段3动态必填参数缺失提交复测清场"})
    ev["observations"]["finalTask"] = api(f"/tasks/{after}")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"before": before, "afterInvalid": ev["observations"]["afterInvalidMaxTaskId"],
                  "afterMissing": after, "missingRequest": ev["requests"]["missingRequiredSceneParam"].get("error", "HTTP 200"),
                  "createdStatus": ev["observations"].get("createdTask", {}).get("status")}, ensure_ascii=False))
