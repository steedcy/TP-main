"""TC-050/059: fail both navigation simulators during baseline downgrade execution."""
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
agents = {a["deviceCode"]: a for a in config("/device-agents?page=1&size=100")["content"]
          if a["deviceCode"].startswith("SIM_F2_")}
assert len(agents) == 6 and all(a["agentStatus"] == "ENABLED" and
    a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE" and
    a["currentTaskId"] is None for a in agents.values())
robots = ["SIM_F2_ROBOT", "SIM_F2_ROBOT_B"]
endpoints = {code: config("/devices/" + code)["accessEndpoint"] + "/device-api/v1"
             for code in robots}
secrets = local.secrets()
mode_path = root / ".local-test/planning-fault.json"
original = mode_path.read_text(encoding="utf-8")
mode = json.loads(original)
mode.update(goal="success", planning="malformed", replanning="success")
mode.pop("initialPlanSteps", None)
request = {"taskGoal": source["taskGoal"], "taskFamily": source["taskFamily"],
           "sceneParams": source["sceneParams"]}
out = stage / "evidence" / ("TC-050-baseline-failure-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "sourceTaskId": 19,
      "request": request, "fixtureBefore": json.loads(original), "fixtureDuring": mode,
      "robotAgentsBefore": {c: agents[c] for c in robots}, "scenarioControls": {},
      "clarifications": [], "restore": {}}
changed = []
task_id = None
try:
    mode_path.write_text(json.dumps(mode, ensure_ascii=False), encoding="utf-8")
    for code in robots:
        ev["scenarioControls"][code] = local.request(
            endpoints[code] + "/control/scenario", "POST",
            {"scenarioResult": "FAILED"}, token=secrets[code])
        changed.append(code)
    response = operator("/tasks", "POST", request)
    task_id = response["id"]
    ev["submitted"] = {k: response.get(k) for k in ("id", "taskCode", "status", "createdAt")}
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        task = operator(f"/tasks/{task_id}")
        questions = task.get("missingInfoQuestions") or []
        if task["status"] == "PLANNING" and questions and len(ev["clarifications"]) < 3:
            answer = ("全部为虚构测试数据：行李及旅客当前均位于F2_BAGGAGE_POINT；先在此完成测量和超规上报，"
                      "再由智慧航显提示并引导至唯一目的地F2_TEST_GATE。额外场景参数仅为设备能力输入，"
                      "不改变原始目标、完成条件或行李当前位置。")
            task = operator(f"/tasks/{task_id}/clarify", "POST",
                            {"answers": {question: answer for question in questions}})
            ev["clarifications"].append({"questions": questions, "answer": answer,
                                         "returnedStatus": task["status"]})
            continue
        if task["status"] not in {"PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT",
                                  "DOWNGRADING", "EXECUTING"}:
            break
        time.sleep(1)
    ev["task"] = task
    ev["plans"] = operator(f"/tasks/{task_id}/plan-versions")
    ev["assignments"] = operator(f"/tasks/{task_id}/step-assignments")
    ev["events"] = operator(f"/tasks/{task_id}/events")
    ev["exceptions"] = operator(f"/task-exceptions")
except Exception as error:
    ev["error"] = str(error)
finally:
    mode_path.write_text(original, encoding="utf-8")
    ev["restore"]["fixtureExact"] = mode_path.read_text(encoding="utf-8") == original
    for code in changed:
        try:
            ev["restore"][code] = local.request(endpoints[code] + "/control/scenario",
                "POST", {"scenarioResult": "SUCCESS"}, token=secrets[code])
        except Exception as error:
            ev["restore"][code + "Error"] = str(error)
    if task_id is not None:
        final = operator(f"/tasks/{task_id}")
        if final["status"] in {"PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT",
                               "DOWNGRADING", "EXECUTING", "PENDING_MANUAL"}:
            try:
                ev["restore"]["cleanup"] = operator(f"/tasks/{task_id}/terminate", "POST",
                    {"reason": "阶段3基线执行失败路径已取证", "confirmed": True})["status"]
            except Exception as error:
                ev["restore"]["cleanupError"] = str(error)
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        current = [a for a in config("/device-agents?page=1&size=100")["content"]
                   if a["deviceCode"].startswith("SIM_F2_")]
        if len(current) == 6 and all(a["onlineStatus"] == "ONLINE" and
            a["workStatus"] == "IDLE" and a["currentTaskId"] is None for a in current):
            break
        time.sleep(0.5)
    ev["restore"]["agents"] = current
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": out.name, "taskId": task_id,
                  "status": ev.get("task", {}).get("status"),
                  "planSources": [p["source"] for p in ev.get("plans", [])],
                  "eventTypes": [e["eventType"] for e in ev.get("events", [])],
                  "restore": {k: v for k, v in ev["restore"].items() if k != "agents"},
                  "error": ev.get("error")}, ensure_ascii=False))
if ev.get("error"):
    raise RuntimeError(ev["error"])
