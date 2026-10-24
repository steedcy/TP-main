"""Compare dashboard counts with the corresponding list endpoints by role."""
import importlib.util
import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)
operator = env.API("运行操作员")
config = env.API("配置管理员")
admin = env.API("系统管理员")
today = operator("/dashboard/overview?period=TODAY")
week = operator("/dashboard/overview?period=LAST_7_DAYS")
metrics = today["metrics"]
statuses = ("PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT", "DOWNGRADING", "EXECUTING",
            "COMPLETED", "FAILED", "PENDING_MANUAL", "MANUAL_TERMINATED")
task_counts = {status: operator(f"/tasks?status={status}&page=1&size=1")["totalElements"] for status in statuses}
assert metrics["statusCounts"] == task_counts, "dashboard status counts differ from task list"
assert metrics["taskInProgress"] == sum(task_counts[s] for s in ("PENDING_ASSIGNMENT", "DOWNGRADING", "EXECUTING"))
assert metrics["pendingManual"] == task_counts["PENDING_MANUAL"]
assert metrics["unhandledExceptions"] == operator("/task-exceptions/pending-count")
assert metrics["agentTotal"] == sum(operator(f"/device-agents?agentStatus={s}&page=1&size=1")["totalElements"] for s in ("ENABLED", "DISABLED"))
assert metrics["agentOnline"] == operator("/device-agents?agentStatus=ENABLED&onlineStatus=ONLINE&page=1&size=1")["totalElements"]
assert week["metrics"]["statusCounts"] == metrics["statusCounts"]
assert week["metrics"]["replanningCount"] >= metrics["replanningCount"]
assert admin("/dashboard/overview")["metrics"]["statusCounts"] == task_counts
config_data = config("/dashboard/overview")
assert "statusCounts" not in config_data["metrics"] and config_data["latestExceptions"] == []
assert config_data["metrics"]["agentTotal"] == metrics["agentTotal"]
destination = env.EVIDENCE / ("20261024-group3-overview-" + time.strftime("%H%M%S") + ".json")
env.save(destination, {"recordedAt": env.stamp(), "operatorToday": today, "operatorWeek": week,
                       "systemAdmin": admin("/dashboard/overview"), "configAdmin": config_data,
                       "listTaskCounts": task_counts})
print(json.dumps({"statusCounts": task_counts, "agentTotal": metrics["agentTotal"],
                  "agentOnline": metrics["agentOnline"], "pendingManual": metrics["pendingManual"],
                  "replanningToday": metrics["replanningCount"], "evidence": str(destination)}, ensure_ascii=False))
