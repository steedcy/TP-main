"""TC-031.S2: submit synthetic identity-field canaries; inspect what is persisted."""
import importlib.util
import json
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
db_spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(db_spec)
db_spec.loader.exec_module(db)
operator = local.API("运行操作员")
source = operator("/tasks/19")
assert source["status"] == "COMPLETED"
canaries = {"passengerName": "S3_FAKE_NAME_DO_NOT_STORE",
            "identityDocumentNumber": "S3_FAKE_DOCUMENT_DO_NOT_STORE"}
assert all(marker not in source["taskGoal"] for marker in canaries.values())
params = dict(source["sceneParams"])
params.update(canaries)
request = {"taskGoal": source["taskGoal"], "taskFamily": source["taskFamily"],
           "sceneParams": params}
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "schema": "tip_stage2_v14", "canaries": canaries, "request": request,
      "beforeMaxTaskId": int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks")),
      "submit": None, "submitError": None, "afterMaxTaskId": None, "task": None,
      "contexts": None, "planVersions": None, "events": None}
out = Path(__file__).parent / "evidence" / (
    "TC-031-identity-canary-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
try:
    ev["submit"] = operator("/tasks", "POST", request)
except Exception as error:
    ev["submitError"] = str(error)
finally:
    ev["afterMaxTaskId"] = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
    if ev["afterMaxTaskId"] > ev["beforeMaxTaskId"]:
        task_id = ev["afterMaxTaskId"]
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            ev["task"] = operator(f"/tasks/{task_id}")
            if ev["task"]["status"] not in ["PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT",
                                            "DOWNGRADING", "EXECUTING"]:
                break
            time.sleep(1)
        ev["contexts"] = operator(f"/tasks/{task_id}/context-snapshots")
        ev["planVersions"] = operator(f"/tasks/{task_id}/plan-versions")
        ev["events"] = operator(f"/tasks/{task_id}/events")
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"taskId": ev["afterMaxTaskId"] if ev["afterMaxTaskId"] > ev["beforeMaxTaskId"] else None,
                  "submitError": ev["submitError"], "status": ev["task"]["status"] if ev["task"] else None,
                  "persistedCanaries": {key: ev["task"]["sceneParams"].get(key) == value
                                        for key, value in canaries.items()} if ev["task"] else None,
                  "evidence": str(out)}, ensure_ascii=False))
