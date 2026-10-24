"""Exercise a fictional structured flight event through all three physical channels."""
import importlib.util
import json
import pathlib
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)
api = env.API("运行操作员")
scene = {
    "eventSource": "MANUAL_FORM", "flightNumber": "R08Z81", "changeType": "GATE_CHANGE",
    "originalTime": "2026-10-25T20:00:00", "originalGate": "GATE_A05", "newGate": "F2_TEST_GATE",
    "changeDescription": "虚构航班R08Z81由GATE_A05变更至F2_TEST_GATE，原因设备维护",
    "updateType": "GATE_CHANGE", "updateContent": "虚构航班R08Z81改至F2_TEST_GATE",
    "displayDuration": 60, "originLocation": "GATE_A05", "targetLocation": "F2_TEST_GATE",
    "routePreference": "BARRIER_FREE", "contentType": "TEXT",
    "contentData": "R08Z81改至F2_TEST_GATE，请按提示前往新登机口",
    "notificationType": "BOTH", "notificationContent": "R08Z81新登机口F2_TEST_GATE",
    "repeatCount": 1,
}
goal = "为虚构航班R08Z81处理登机口变更：从已标定仿真位置GATE_A05改至F2_TEST_GATE，2026-10-25 20:00生效，原因设备维护。请更新航延屏，在智慧航显展示新登机口与路线，并由机器人通知现场旅客改道。"
before = api("/tasks?page=1&size=1")["totalElements"]
bad = dict(scene)
bad.pop("newGate")
request = urllib.request.Request(env.BASE + "/tasks", json.dumps({"taskGoal": goal, "taskFamily": "FLIGHT_CHANGE_RESPONSE", "sceneParams": bad}, ensure_ascii=False).encode(),
    {"Content-Type": "application/json", "Authorization": "Bearer " + api.token}, method="POST")
try:
    urllib.request.urlopen(request, timeout=15)
    invalid_status = 200
except urllib.error.HTTPError as error:
    invalid_status = error.code
assert invalid_status == 400 and api("/tasks?page=1&size=1")["totalElements"] == before, "invalid gate was accepted"

task = api("/tasks", "POST", {"taskGoal": goal, "taskFamily": "FLIGHT_CHANGE_RESPONSE", "sceneParams": scene})
task_id = task["id"]
rounds = 0
deadline = time.monotonic() + 150
while time.monotonic() < deadline:
    questions = task.get("missingInfoQuestions") or []
    if task["status"] == "PLANNING" and questions and rounds < 3:
        answer = "全部为虚构测试数据：R08Z81 原计划2026-10-25 20:00，登机口从GATE_A05变更至F2_TEST_GATE；原因设备维护；旅客需获知新登机口并改道。"
        task = api(f"/tasks/{task_id}/clarify", "POST", {"answers": {question: answer for question in questions}})
        rounds += 1
        continue
    if task["status"] in {"COMPLETED", "FAILED", "PENDING_MANUAL", "MANUAL_TERMINATED"}:
        break
    time.sleep(2)
    task = api(f"/tasks/{task_id}")
plans = api(f"/tasks/{task_id}/plan-versions")
assignments = api(f"/tasks/{task_id}/step-assignments")
agents = {a["agentId"]: a for a in api("/device-agents?page=1&size=100")["content"]}
steps = next((p["planSteps"] for p in plans if p["id"] == task.get("currentPlanVersionId")), [])
channels = []
for assignment in assignments:
    step = next((s for s in steps if s["stepSeq"] == assignment["stepSeq"]), {})
    agent = agents.get(assignment.get("deviceAgentCode"), {})
    channels.append({"capability": step.get("capabilityType"), "deviceCode": agent.get("deviceCode"),
                     "status": assignment["stepStatus"], "output": assignment.get("outputParams")})
evidence = {"recordedAt": env.stamp(), "case": "GROUP2_FLIGHT_THREE_CHANNELS", "taskId": task_id,
            "task": task, "invalidGateHttpStatus": invalid_status, "planVersions": plans,
            "assignments": assignments, "channels": channels, "events": api(f"/tasks/{task_id}/events")}
destination = env.EVIDENCE / ("20261024-group2-flight-" + time.strftime("%H%M%S") + ".json")
env.save(destination, evidence)
expected = {"CAP_FLIGHT_UPDATE": "SIM_F2_FLIGHT", "CAP_INFO_DISPLAY": "SIM_F2_DISPLAY"}
for capability, device in expected.items():
    assert any(c["capability"] == capability and c["deviceCode"] == device and c["status"] == "COMPLETED" for c in channels), f"{capability} did not complete on {device}"
assert any(c["capability"] in {"CAP_NOTIFICATION", "CAP_NAVIGATION"} and c["deviceCode"] in {"SIM_F2_ROBOT", "SIM_F2_ROBOT_B"} and c["status"] == "COMPLETED" for c in channels), "robot channel missing"
assert task["status"] == "COMPLETED", f"task ended {task['status']}"
print(json.dumps({"taskId": task_id, "status": task["status"], "channels": channels, "evidence": str(destination)}, ensure_ascii=False))
