"""TC-094.S2: execute a fresh core baggage task after the manual backend restart."""
import importlib.util
import json
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
operator, config = local.API("运行操作员"), local.API("配置管理员")
source = operator("/tasks/19")
assert source["status"] == "COMPLETED" and source["taskFamily"] == "OVERSIZE_BAGGAGE_HANDLING"
restart = json.loads((stage / "evidence/TC-094-manual-restart-20261027T041012Z.json")
                     .read_text(encoding="utf-8"))
assert restart["stop"]["healthUnavailableAfterStop"]
assert restart["after"]["persistedExactly"]
mode_path = root / ".local-test/planning-fault.json"
original = mode_path.read_text(encoding="utf-8")
mode = json.loads(original)
mode.update(goal="success", planning="malformed", replanning="success")
mode.pop("initialPlanSteps", None)
request = {"taskGoal": source["taskGoal"], "taskFamily": source["taskFamily"],
           "sceneParams": source["sceneParams"]}
out = stage / "evidence" / ("TC-094-postrestart-core-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "sourceRestartEvidence":
      "TC-094-manual-restart-20261027T041012Z.json",
      "fixtureBefore": json.loads(original), "fixtureDuring": mode,
      "request": request, "restore": {}}
task_id = None
try:
    mode_path.write_text(json.dumps(mode, ensure_ascii=False), encoding="utf-8")
    response = operator("/tasks", "POST", request)
    task_id = response["id"]
    ev["submitted"] = {k: response.get(k) for k in ("id", "taskCode", "status", "createdAt")}
    deadline = time.monotonic() + 100
    while time.monotonic() < deadline:
        task = operator(f"/tasks/{task_id}")
        if task["status"] not in {"PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT",
                                  "DOWNGRADING", "EXECUTING"}:
            break
        time.sleep(1)
    ev["task"] = task
    ev["plans"] = operator(f"/tasks/{task_id}/plan-versions")
    ev["assignments"] = operator(f"/tasks/{task_id}/step-assignments")
    ev["events"] = operator(f"/tasks/{task_id}/events")
except Exception as error:
    ev["error"] = str(error)
finally:
    mode_path.write_text(original, encoding="utf-8")
    ev["restore"]["fixtureExact"] = mode_path.read_text(encoding="utf-8") == original
    if task_id is not None:
        final = operator(f"/tasks/{task_id}")
        if final["status"] in {"PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT",
                               "DOWNGRADING", "EXECUTING", "PENDING_MANUAL"}:
            try:
                ev["restore"]["cleanup"] = operator(f"/tasks/{task_id}/terminate", "POST",
                    {"reason": "阶段3人工重启后的核心任务检查已记录", "confirmed": True})["status"]
            except Exception as error:
                ev["restore"]["cleanupError"] = str(error)
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        agents = [a for a in config("/device-agents?page=1&size=100")["content"]
                  if a["deviceCode"].startswith("SIM_F2_")]
        if len(agents) == 6 and all(a["onlineStatus"] == "ONLINE" and
            a["workStatus"] == "IDLE" and a["currentTaskId"] is None for a in agents):
            break
        time.sleep(0.5)
    ev["restore"]["agents"] = agents
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": out.name, "taskId": task_id,
                  "status": ev.get("task", {}).get("status"),
                  "planSources": [p["source"] for p in ev.get("plans", [])],
                  "assignments": [a["stepStatus"] for a in ev.get("assignments", [])],
                  "fixtureRestored": ev["restore"]["fixtureExact"],
                  "allSixOnlineIdle": len(ev["restore"]["agents"]) == 6 and all(
                    a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE"
                    for a in ev["restore"]["agents"]), "error": ev.get("error")},
                 ensure_ascii=False))
if ev.get("error"):
    raise RuntimeError(ev["error"])
