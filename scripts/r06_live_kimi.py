"""R06 live Moonshot/Kimi retest capture. Credentials are read in memory only."""
import importlib.util
import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)
operator = env.API("运行操作员")

goal = (
    "请为完全虚构的航班 TESTR06 执行登机口变更响应：航班原在 F2_TEST_GATE_A，现改至 "
    "F2_TEST_GATE_B，20:00 生效，原因是设备维护。现场有 6 名虚构旅客，均位于 "
    "F2_TEST_GATE_A，其中 2 名使用轮椅、需要无障碍陪同；其余 4 名可自行步行。"
    "请完成航班信息发布、向旅客通知变更、规划无障碍路线、安排轮椅旅客陪同，并确认发布与引导结果。"
    "所有人名、航班和旅客数据均为虚构，不包含真实个人信息。"
)
request = {
    "taskGoal": goal,
    "taskFamily": "FLIGHT_CHANGE_RESPONSE",
    "sceneParams": {
        "flightNumber": "TESTR06",
        "updateType": "GATE_CHANGE",
        "updateContent": "虚构航班 TESTR06 于 20:00 从 F2_TEST_GATE_A 变更至 F2_TEST_GATE_B，原因设备维护",
        "displayDuration": 60,
        "targetLocation": "F2_TEST_GATE_B",
        "routePreference": "BARRIER_FREE",
        "affectedPassengerCount": 6,
        "wheelchairPassengerCount": 2,
        "originLocation": "F2_TEST_GATE_A",
    },
}

def snapshot(task_id):
    task = operator(f"/tasks/{task_id}")
    events = operator(f"/tasks/{task_id}/events")
    plans = operator(f"/tasks/{task_id}/plan-versions")
    contexts = operator(f"/tasks/{task_id}/context-snapshots")
    assignments = operator(f"/tasks/{task_id}/step-assignments")
    return {"task": task, "events": events, "planVersions": plans,
            "contextSnapshots": contexts, "stepAssignments": assignments}

result = {"recordedAt": env.stamp(), "provider": "Moonshot/Kimi", "request": request,
          "clarificationRounds": [], "actions": []}
task = operator("/tasks", "POST", request)
task_id = task["id"]
result["submittedTaskId"] = task_id
deadline = time.monotonic() + 240
round_no = 0
while time.monotonic() < deadline:
    current = operator(f"/tasks/{task_id}")
    status = current.get("status")
    questions = current.get("missingInfoQuestions") or []
    if status == "PLANNING" and questions and round_no < 3:
        # Answer each exact returned question with concrete, anonymized scene facts.
        answers = {}
        for question in questions:
            q = question.lower()
            if any(k in q for k in ("旅客", "人数", "乘客", "受影响", "wheelchair", "passenger")):
                answer = "全部为虚构数据：共6名旅客，从F2_TEST_GATE_A前往F2_TEST_GATE_B，其中2名使用轮椅并需要无障碍陪同，另4名可自行步行；没有真实身份信息。"
            elif any(k in q for k in ("起点", "位置", "地点", "origin", "where")):
                answer = "虚构起点为F2_TEST_GATE_A，目的地为F2_TEST_GATE_B，生效时间20:00。"
            elif any(k in q for k in ("航班", "时间", "原因", "flight", "when", "why")):
                answer = "虚构航班TESTR06于20:00生效，登机口从F2_TEST_GATE_A改至F2_TEST_GATE_B，原因是设备维护。"
            else:
                answer = "全部信息为虚构场景：TESTR06，20:00由F2_TEST_GATE_A变更至F2_TEST_GATE_B；6名旅客，其中2名轮椅旅客需无障碍陪同；设备维护是变更原因。"
            answers[question] = answer
        round_no += 1
        clarified = operator(f"/tasks/{task_id}/clarify", "POST", {"answers": answers})
        result["clarificationRounds"].append({"round": round_no, "questions": questions,
                                               "answers": answers, "response": clarified})
        time.sleep(1)
        continue
    if status not in {"PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT", "EXECUTING", "DOWNGRADING"}:
        break
    time.sleep(2)
final = snapshot(task_id)
result["final"] = final
result["summary"] = {"status": final["task"].get("status"),
                     "reasonCode": next((e.get("reasonCode") for e in final["events"]
                                         if e.get("eventType") == "GOAL_CLARIFIED"), None),
                     "snapshotCount": len(final["contextSnapshots"]),
                     "planVersionCount": len(final["planVersions"]),
                     "eventTypes": [e.get("eventType") for e in final["events"]]}
out = ROOT / ("document/formal-test-evidence/R06-TC037-live-kimi-"
              + time.strftime("%Y%m%d-%H%M%S") + ".json")
env.save(out, result)
print(json.dumps({"taskId": task_id, "status": result["summary"]["status"],
                  "reasonCode": result["summary"]["reasonCode"],
                  "clarificationRounds": round_no,
                  "snapshots": result["summary"]["snapshotCount"],
                  "planVersions": result["summary"]["planVersionCount"],
                  "evidence": str(out)}, ensure_ascii=False))
