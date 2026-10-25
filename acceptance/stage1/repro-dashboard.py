"""Read-only directed comparison of dashboard metrics against list endpoints."""
import importlib.util
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)

operator = env.API("运行操作员")
config = env.API("配置管理员")
today = operator("/dashboard/overview?period=TODAY")
week = operator("/dashboard/overview?period=LAST_7_DAYS")
statuses = ("PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT", "DOWNGRADING", "EXECUTING",
            "COMPLETED", "FAILED", "PENDING_MANUAL", "MANUAL_TERMINATED")
counts = {status: operator(f"/tasks?status={status}&page=1&size=1")["totalElements"] for status in statuses}
metrics = today["metrics"]
assert metrics["statusCounts"] == counts
assert metrics["pendingManual"] == counts["PENDING_MANUAL"]
assert metrics["taskInProgress"] == sum(counts[s] for s in ("PENDING_ASSIGNMENT", "DOWNGRADING", "EXECUTING"))
assert metrics["agentOnline"] == operator("/device-agents?agentStatus=ENABLED&onlineStatus=ONLINE&page=1&size=1")["totalElements"]
assert week["metrics"]["statusCounts"] == counts
assert "statusCounts" not in config("/dashboard/overview")["metrics"]

evidence = {"observedAt": datetime.now(timezone.utc).isoformat(), "scope": "read-only live API",
            "statusCounts": counts, "agentOnline": metrics["agentOnline"],
            "pendingManual": metrics["pendingManual"], "todayReplans": metrics["replanningCount"],
            "weekReplans": week["metrics"]["replanningCount"], "result": "PASS"}
target = Path(__file__).parent / "evidence" / "dashboard-directed.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"result": "PASS", "evidence": str(target)}, ensure_ascii=False))
