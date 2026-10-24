"""Ensure an absent smart-display channel cannot produce a completed flight task."""
import importlib.util
import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)
api = env.API("运行操作员")
task_id = None
try:
    env.control("SIM_F2_DISPLAY", "offline")
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        agent = next(a for a in api("/device-agents?page=1&size=100")["content"] if a["deviceCode"] == "SIM_F2_DISPLAY")
        if agent["onlineStatus"] == "OFFLINE": break
        time.sleep(1)
    else: raise AssertionError("smart display did not become offline")
    scene = {"eventSource": "MANUAL_FORM", "flightNumber": "R08OFF", "changeType": "GATE_CHANGE",
             "originalTime": "2026-10-25T20:00:00", "originalGate": "GATE_A05", "newGate": "F2_TEST_GATE",
             "changeDescription": "虚构航班R08OFF由GATE_A05变更至F2_TEST_GATE，原因设备维护",
             "updateType": "GATE_CHANGE", "updateContent": "虚构航班R08OFF改至F2_TEST_GATE",
             "displayDuration": 60, "originLocation": "GATE_A05", "targetLocation": "F2_TEST_GATE",
             "routePreference": "BARRIER_FREE", "contentType": "TEXT", "contentData": "R08OFF改至F2_TEST_GATE",
             "notificationType": "BOTH", "notificationContent": "R08OFF新登机口F2_TEST_GATE", "repeatCount": 1}
    goal = "为虚构航班R08OFF处理登机口变更：从已标定仿真位置GATE_A05改至F2_TEST_GATE，2026-10-25 20:00生效，原因设备维护。请更新航延屏，在智慧航显展示新登机口与路线，并由机器人通知现场旅客改道。"
    task = api("/tasks", "POST", {"taskGoal": goal, "taskFamily": "FLIGHT_CHANGE_RESPONSE", "sceneParams": scene})
    task_id = task["id"]
    deadline = time.monotonic() + 150
    rounds = 0
    while task["status"] not in {"COMPLETED", "FAILED", "PENDING_MANUAL", "MANUAL_TERMINATED"} and time.monotonic() < deadline:
        questions = task.get("missingInfoQuestions") or []
        if task["status"] == "PLANNING" and questions and rounds < 5:
            answer = "全部为虚构数据：R08OFF原计划2026-10-25 20:00，从GATE_A05改至F2_TEST_GATE；在F2_TEST_GATE区域由航延屏和智慧航显发布，机器人通知该区域旅客并引导改道。"
            task = api(f"/tasks/{task_id}/clarify", "POST", {"answers": {q: answer for q in questions}})
            rounds += 1
            continue
        time.sleep(2)
        task = api(f"/tasks/{task_id}")
    plans = api(f"/tasks/{task_id}/plan-versions")
    assignments = api(f"/tasks/{task_id}/step-assignments")
    events = api(f"/tasks/{task_id}/events")
    destination = env.EVIDENCE / ("20261024-group2-missing-channel-" + time.strftime("%H%M%S") + ".json")
    env.save(destination, {"recordedAt": env.stamp(), "case": "GROUP2_SMART_DISPLAY_OFFLINE",
                           "task": task, "planVersions": plans, "assignments": assignments, "events": events})
    assert task["status"] != "COMPLETED", "missing display channel was reported as complete"
    assert any(p["capabilityCheckResult"] == "FAIL" for p in plans), "missing channel was not caught by capability validation"
    print(json.dumps({"taskId": task_id, "status": task["status"], "failureReason": task.get("failureReason"), "evidence": str(destination)}, ensure_ascii=False))
finally:
    env.control("SIM_F2_DISPLAY", "online")
