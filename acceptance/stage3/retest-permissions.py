"""Live TC-003 role and server authorization checks, with a real operator task."""
import datetime
import importlib.util
import json
import pathlib
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)
OUT = pathlib.Path(__file__).resolve().parent / "evidence/TC-003-permissions.json"
admin, config, operator = (env.API(role) for role in ("系统管理员", "配置管理员", "运行操作员"))


def raw(api, path, method="GET", data=None):
    request = urllib.request.Request(env.BASE + path,
        data=json.dumps(data, ensure_ascii=False).encode() if data is not None else None,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + api.token},
        method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = json.load(response)
            return {"status": response.status, "code": body.get("code")}
    except urllib.error.HTTPError as error:
        body = json.loads(error.read())
        return {"status": error.code, "code": body.get("code")}


def count(api):
    return api("/tasks?page=1&size=1")["totalElements"]


evidence = {"observedAt": env.stamp(), "gitHead": "0d798ceb53bc37498f353b4796f2081b92e2011b",
    "schema": "tip_stage2_v14", "negativeWrites": [], "positiveReads": {}, "audit": {}, "task": {}}
before = count(operator)
device_code = env.load(env.FIXTURES / "devices.json")[0]["deviceCode"]
checks = [
    ("operator-create-user", operator, "/users", "POST", {"username": "stage3-must-not-create"}),
    ("config-create-user", config, "/users", "POST", {"username": "stage3-must-not-create"}),
    ("operator-create-device", operator, "/devices", "POST", {"deviceCode": "STAGE3_DENIED"}),
    ("admin-create-device", admin, "/devices", "POST", {"deviceCode": "STAGE3_DENIED"}),
    ("config-submit-task", config, "/tasks", "POST", {"taskGoal": "阶段3越权测试：必须拒绝", "taskFamily": "FLIGHT_CHANGE_RESPONSE"}),
    ("admin-submit-task", admin, "/tasks", "POST", {"taskGoal": "阶段3越权测试：必须拒绝", "taskFamily": "FLIGHT_CHANGE_RESPONSE"}),
    ("config-terminate-task", config, "/tasks/16/terminate", "POST", {"reason": "阶段3越权检查", "confirmed": True}),
]
for label, api, path, method, body in checks:
    evidence["negativeWrites"].append({"check": label, **raw(api, path, method, body)})
evidence["tasksAfterDeniedWrites"] = count(operator)
evidence["positiveReads"] = {
    "adminUsers": len(admin("/users?page=1&size=100")["content"]),
    "configDevices": len(config("/devices?page=1&size=100")["content"]),
    "operatorTasks": operator("/tasks?page=1&size=1")["totalElements"],
}
evidence["connectionTest"] = config("/devices/" + device_code + "/connection-test", "POST")

source = json.loads((ROOT / "acceptance/stage2/evidence/smoke-flight-final.json").read_text(encoding="utf-8"))["task"]
request = {"taskGoal": source["taskGoal"].replace("R08Z81", "S3PERM"),
           "taskFamily": source["taskFamily"], "sceneParams": dict(source["sceneParams"])}
request["sceneParams"]["flightNumber"] = "S3PERM"
task = operator("/tasks", "POST", request)
evidence["task"] = {"id": task["id"], "createdAt": task["createdAt"], "submitStatus": task["status"]}
deadline = time.monotonic() + 120
while time.monotonic() < deadline:
    task = operator("/tasks/" + str(task["id"]))
    if task["status"] in {"COMPLETED", "FAILED", "MANUAL_INTERVENTION", "TERMINATED", "CANCELLED"}:
        break
    time.sleep(2)
evidence["task"].update(finalStatus=task["status"], updatedAt=task["updatedAt"],
                        eventCount=len(operator("/tasks/" + str(task["id"]) + "/events")),
                        planVersionCount=len(operator("/tasks/" + str(task["id"]) + "/plan-versions")),
                        stepAssignmentCount=len(operator("/tasks/" + str(task["id"]) + "/step-assignments")))
if task["status"] in {"PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT", "DOWNGRADING", "EXECUTING"}:
    operator("/tasks/" + str(task["id"]) + "/terminate", "POST",
             {"reason": "阶段3权限用例清场", "confirmed": True})
    evidence["task"]["cleanup"] = "TERMINATE_REQUESTED"

own = operator("/operation-logs?username=admin&page=1&size=100")["content"]
all_rows = admin("/operation-logs?page=1&size=100")["content"]
evidence["audit"] = {"operatorOnlyOwnRows": all(row.get("username") == env.account("运行操作员")[0] for row in own),
    "adminSeesMultipleRoles": len({row.get("role") for row in all_rows if row.get("role")}) >= 2,
    "denialRows": sum(row.get("operationType") == "ACCESS_DENIED" for row in all_rows),
    "containsAnyPassword": any(env.account(role)[1] in json.dumps(all_rows, ensure_ascii=False)
                              for role in ("系统管理员", "配置管理员", "运行操作员"))}
evidence["negativeWritesPass"] = (len(evidence["negativeWrites"]) == 7 and
    all(row["status"] == 403 for row in evidence["negativeWrites"]) and
    before == evidence["tasksAfterDeniedWrites"])
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"negativeWritesPass": evidence["negativeWritesPass"], "task": evidence["task"],
                  "audit": evidence["audit"], "evidence": str(OUT)}, ensure_ascii=False))
