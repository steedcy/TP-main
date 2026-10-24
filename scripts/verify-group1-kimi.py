"""Exercise a valid, fictional Kimi plan without overwriting prior evidence."""
import importlib.util
import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)
operator = env.API("运行操作员")

request = {
    "taskGoal": "虚构航班TEST1022延误20分钟。请在航班信息屏发布延误信息、在智慧航显展示并通知F2_TEST区域旅客；全部是虚构测试数据。",
    "taskFamily": "FLIGHT_CHANGE_RESPONSE",
    "sceneParams": {
        "flightNumber": "TEST1022",
        "updateType": "DELAY",
        "updateContent": "虚构航班TEST1022延误20分钟，请关注后续通知",
        "displayDuration": 60,
        "contentType": "TEXT",
        "contentData": "虚构航班TEST1022延误20分钟",
        "notificationType": "BOTH",
        "notificationContent": "虚构航班TEST1022延误20分钟，请留意航班信息屏",
        "repeatCount": 1,
    },
}
task = operator("/tasks", "POST", request)
task_id = task["id"]
deadline = time.monotonic() + 90
while task["status"] in {"PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT", "EXECUTING", "DOWNGRADING"} and time.monotonic() < deadline:
    time.sleep(2)
    task = operator(f"/tasks/{task_id}")

plans = operator(f"/tasks/{task_id}/plan-versions")
events = operator(f"/tasks/{task_id}/events")
assignments = operator(f"/tasks/{task_id}/step-assignments")
result = {"recordedAt": env.stamp(), "scope": "GROUP1_VALID_KIMI_CANDIDATE",
          "taskId": task_id, "taskStatus": task["status"], "taskFailureReason": task.get("failureReason"),
          "planVersions": plans, "events": events, "assignments": assignments}
destination = env.EVIDENCE / ("20261024-group1-kimi-" + time.strftime("%H%M%S") + ".json")
env.save(destination, result)
print(json.dumps({"taskId": task_id, "taskStatus": task["status"],
                  "planChecks": [(p["source"], p["structureCheckResult"],
                                  p["capabilityCheckResult"], p["constraintCheckResult"])
                                 for p in plans], "evidence": str(destination)}, ensure_ascii=False))
