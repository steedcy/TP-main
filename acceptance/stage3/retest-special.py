"""Check fictional special-passenger meeting display, notification and escort channels."""
import importlib.util
import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)
api = env.API("运行操作员")
scene = {"serviceId": "SP-R08-077", "assistanceType": "轮椅协助", "originLocation": "F2_SERVICE_POINT",
         "targetLocation": "F2_TEST_GATE", "notificationType": "BOTH", "repeatCount": 1,
         "escortMode": "LEAD", "maxDuration": 600, "contentType": "TEXT", "displayDuration": 60,
         "contentData": "虚构轮椅旅客请在F2_SERVICE_POINT会合并陪同至F2_TEST_GATE"}
goal = "为虚构服务编号SP-R08-077安排轮椅协助，从F2_SERVICE_POINT会合并陪同至F2_TEST_GATE，并在智慧航显发布会合提示，由机器人通知现场人员。SP-R08-077是本测试唯一会合确认编号，不需虚构姓名，不记录真实身份。"
task = api("/tasks", "POST", {"taskGoal": goal, "taskFamily": "SPECIAL_PASSENGER_SERVICE", "sceneParams": scene})
task_id = task["id"]
rounds = 0
deadline = time.monotonic() + 150
while time.monotonic() < deadline:
    questions = task.get("missingInfoQuestions") or []
    if task["status"] == "PLANNING" and questions and rounds < 3:
        answer = "全部为虚构服务：轮椅协助，起点F2_SERVICE_POINT，目的地F2_TEST_GATE；由机器人通知并陪同。SP-R08-077是唯一会合确认编号，不需任何姓名或其他身份标识。"
        task = api(f"/tasks/{task_id}/clarify", "POST", {"answers": {q: answer for q in questions}})
        rounds += 1
        continue
    if task["status"] in {"COMPLETED", "FAILED", "PENDING_MANUAL", "MANUAL_TERMINATED"}:
        break
    time.sleep(2)
    task = api(f"/tasks/{task_id}")
plans = api(f"/tasks/{task_id}/plan-versions")
assignments = api(f"/tasks/{task_id}/step-assignments")
steps = next((p["planSteps"] for p in plans if p["id"] == task.get("currentPlanVersionId")), [])
agents = {a["agentId"]: a for a in api("/device-agents?page=1&size=100")["content"]}
channels = []
for assignment in assignments:
    step = next((s for s in steps if s["stepSeq"] == assignment["stepSeq"]), {})
    channels.append({"capability": step.get("capabilityType"),
                     "deviceCode": agents.get(assignment.get("deviceAgentCode"), {}).get("deviceCode"),
                     "status": assignment["stepStatus"], "output": assignment.get("outputParams")})
destination = pathlib.Path(__file__).resolve().parent / "evidence" / ("TC-077-special-" + time.strftime("%H%M%S") + ".json")
destination.parent.mkdir(exist_ok=True)
env.save(destination, {"recordedAt": env.stamp(), "runtimeInput": "V1.5", "case": "TC-077-NORMAL",
                       "task": task, "plans": plans, "assignments": assignments, "channels": channels,
                       "events": api(f"/tasks/{task_id}/events")})
assert task["status"] == "COMPLETED", f"task ended {task['status']}"
assert any(c["capability"] == "CAP_INFO_DISPLAY" and c["deviceCode"] == "SIM_F2_DISPLAY" and c["status"] == "COMPLETED" for c in channels)
for capability in ("CAP_NOTIFICATION", "CAP_ESCORT"):
    assert any(c["capability"] == capability and c["deviceCode"] in {"SIM_F2_ROBOT", "SIM_F2_ROBOT_B"}
               and c["status"] == "COMPLETED" for c in channels), f"{capability} missing"
print(json.dumps({"taskId": task_id, "status": task["status"], "channels": channels, "evidence": str(destination)}, ensure_ascii=False))
