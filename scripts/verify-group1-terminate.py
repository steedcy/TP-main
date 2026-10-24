"""Check formal task termination and device cancellation in local simulation."""
import importlib.util
import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)
operator = env.API("运行操作员")
codes = ("SIM_F2_FLIGHT", "SIM_F2_DISPLAY")
task_id = None
try:
    for code in codes:
        env.control(code, "delay:10000")
    request = {
        "taskGoal": "虚构航班TEST1022原定20:00起飞，现预计20:20起飞，延误20分钟。请在航班信息屏发布延误信息、在智慧航显展示并通知F2_TEST虚构测试区旅客；登机口不变，无需导航。",
        "taskFamily": "FLIGHT_CHANGE_RESPONSE",
        "sceneParams": {"flightNumber": "TEST1022", "updateType": "DELAY",
                        "updateContent": "虚构航班TEST1022延误20分钟", "displayDuration": 60,
                        "contentType": "TEXT", "contentData": "虚构航班TEST1022延误20分钟",
                        "notificationType": "BOTH", "notificationContent": "虚构航班TEST1022延误20分钟",
                        "repeatCount": 1},
    }
    task = operator("/tasks", "POST", request)
    task_id = task["id"]
    deadline = time.monotonic() + 45
    rounds = 0
    while task["status"] != "EXECUTING" and time.monotonic() < deadline:
        questions = task.get("missingInfoQuestions") or []
        if task["status"] == "PLANNING" and questions and rounds < 3:
            answer = "全部为虚构测试：航班TEST1022，类型DELAY，原定20:00起飞、现预计20:20起飞；F2_TEST是已配置的虚构测试区域，通知该区域旅客；登机口不变，无需导航。"
            task = operator(f"/tasks/{task_id}/clarify", "POST",
                            {"answers": {question: answer for question in questions}})
            rounds += 1
            continue
        if task["status"] in {"COMPLETED", "FAILED", "PENDING_MANUAL", "MANUAL_TERMINATED"}:
            break
        time.sleep(.25)
        task = operator(f"/tasks/{task_id}")
    if task["status"] != "EXECUTING":
        raise AssertionError(f"task {task_id} did not reach EXECUTING: {task['status']}")
    result = operator(f"/tasks/{task_id}/terminate", "POST",
                      {"reason": "首组取消确认回归", "confirmed": True})
    if result["status"] != "MANUAL_TERMINATED":
        raise AssertionError("termination did not retain the terminal state")
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        agents = env.API()("/device-agents?page=1&size=100")["content"]
        events = operator(f"/tasks/{task_id}/events")
        if any(e["eventType"] == "TASK_CANCEL_CONFIRMED_IDLE" for e in events):
            break
        time.sleep(1)
    else:
        raise AssertionError("no correlated idle confirmation after cancellation")
    task = operator(f"/tasks/{task_id}")
    if task["status"] != "MANUAL_TERMINATED":
        raise AssertionError("late feedback changed the terminal task state")
    result = {"recordedAt": env.stamp(), "scope": "GROUP1_TERMINATE_SIMULATION",
              "taskId": task_id, "status": task["status"],
              "eventTypes": [event["eventType"] for event in events],
              "agents": [{key: agent.get(key) for key in ("deviceCode", "workStatus", "currentTaskId")}
                         for agent in agents if agent["deviceCode"] in codes],
              "result": "PASS"}
    out = env.EVIDENCE / ("20261024-group1-terminate-" + time.strftime("%H%M%S") + ".json")
    env.save(out, result)
    print(json.dumps({"result": "PASS", "taskId": task_id, "evidence": str(out)}, ensure_ascii=False))
finally:
    for code in codes:
        env.control(code, "delay:1000")
