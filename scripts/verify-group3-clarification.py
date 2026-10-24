"""Observe live Kimi clarification with fictional data and preserve each round."""
import importlib.util
import json
import pathlib
import time

spec = importlib.util.spec_from_file_location("localenv", pathlib.Path(__file__).with_name("local-test-environment.py"))
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)
api = env.API("运行操作员")
goal = "请协助一位需要轮椅服务的虚构旅客抵达登机口。"
task = api("/tasks", "POST", {"taskGoal": goal, "taskFamily": "SPECIAL_PASSENGER_SERVICE",
                                "sceneParams": {"assistanceType": "WHEELCHAIR"}})
task_id = task["id"]
record = {"recordedAt": env.stamp(), "case": "TC-032_LIVE_KIMI", "taskId": task_id, "rounds": [], "initial": task}
try:
    for round_number in range(1, 4):
        questions = task.get("missingInfoQuestions") or []
        if task["status"] != "PLANNING" or not questions:
            break
        answer = ("全部为虚构仿真场景：从F2_TEST_GATE旁的F2_TEST_SERVICE_POINT出发，"
                  "协助轮椅旅客到F2_TEST_GATE，优先无障碍路线；到达并通知现场服务人员即完成。")
        answers = {question: answer for question in questions}
        task = api(f"/tasks/{task_id}/clarify", "POST", {"answers": answers})
        record["rounds"].append({"number": round_number, "questions": questions,
                                 "answers": answers, "status": task["status"],
                                 "remainingQuestions": task.get("missingInfoQuestions"),
                                 "storedRounds": task.get("sceneParams", {}).get("clarificationAnswers")})
    record["final"] = api(f"/tasks/{task_id}")
    record["events"] = api(f"/tasks/{task_id}/events")
    assert all(len(item["storedRounds"]) == item["number"] for item in record["rounds"])
    assert record["final"]["status"] != "PLANNING" or len(record["rounds"]) < 3
    record["result"] = "PASS"
except Exception as error:
    record["result"] = "FAIL"
    record["error"] = str(error)
finally:
    path = env.EVIDENCE / ("20261024-group3-clarification-" + time.strftime("%H%M%S") + ".json")
    env.save(path, record)
    print(json.dumps({"result": record["result"], "taskId": task_id,
                      "rounds": len(record["rounds"]), "finalStatus": record.get("final", {}).get("status"),
                      "evidence": str(path)}, ensure_ascii=False), flush=True)
if record["result"] != "PASS":
    raise SystemExit(1)
