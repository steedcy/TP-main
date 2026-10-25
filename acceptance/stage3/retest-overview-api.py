"""TC-004 live dashboard/API/DB comparison; records missing fixture states."""
import datetime
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


env = module("localenv", ROOT / "scripts/local-test-environment.py")
db = module("isodb", ROOT / "acceptance/stage2/db-isolation.py")
OUT = pathlib.Path(__file__).resolve().parent / "evidence/TC-004-overview-api.json"
operator = env.API("运行操作员")
config = env.API("配置管理员")
admin = env.API("系统管理员")
today = operator("/dashboard/overview?period=TODAY")
week = operator("/dashboard/overview?period=LAST_7_DAYS")
admin_today = admin("/dashboard/overview?period=TODAY")
config_today = config("/dashboard/overview?period=TODAY")
schema = db.schema
sql = {
    "agentTotal": f"SELECT count(*) FROM {schema}.device_agents WHERE agent_status <> 'ARCHIVED'",
    "agentOnline": f"SELECT count(*) FROM {schema}.device_agents WHERE agent_status='ENABLED' AND online_status='ONLINE'",
    "taskInProgress": f"SELECT count(*) FROM {schema}.tasks WHERE status IN ('PENDING_ASSIGNMENT','DOWNGRADING','EXECUTING')",
    "pendingManual": f"SELECT count(*) FROM {schema}.tasks WHERE status='PENDING_MANUAL'",
    "unhandledExceptions": f"SELECT count(*) FROM {schema}.task_exceptions WHERE exception_status='PENDING'",
}
independent = {name: int(db.query(db.source, statement)) for name, statement in sql.items()}
status_counts = {row.split("|")[0]: int(row.split("|")[1]) for row in db.query(db.source,
    f"SELECT status,count(*) FROM {schema}.tasks WHERE is_dry_run=false GROUP BY status").splitlines()}
dry_run_counts = {row.split("|")[0]: int(row.split("|")[1]) for row in db.query(db.source,
    f"SELECT status,count(*) FROM {schema}.tasks WHERE is_dry_run=true GROUP BY status").splitlines()}
today_start = datetime.date.today().isoformat() + " 00:00:00"
week_start = (datetime.date.today() - datetime.timedelta(days=6)).isoformat() + " 00:00:00"
independent["todayReplanningCount"] = int(db.query(db.source,
    f"SELECT count(*) FROM {schema}.task_events WHERE event_type='REPLANNING_TRIGGERED' AND occurred_at >= '{today_start}'"))
independent["weekReplanningCount"] = int(db.query(db.source,
    f"SELECT count(*) FROM {schema}.task_events WHERE event_type='REPLANNING_TRIGGERED' AND occurred_at >= '{week_start}'"))
metrics = today["metrics"]
checks = {name: metrics[name] == value for name, value in independent.items() if name in metrics}
checks["todayReplans"] = metrics["replanningCount"] == independent["todayReplanningCount"]
checks["weekReplans"] = week["metrics"]["replanningCount"] == independent["weekReplanningCount"]
checks["adminMatchesOperator"] = admin_today["metrics"] == metrics
checks["configNoTaskMetrics"] = all(name not in config_today["metrics"] for name in
    ("taskInProgress", "pendingManual", "unhandledExceptions", "replanningCount", "statusCounts"))
checks["nineStatusFields"] = len(metrics["statusCounts"]) == 9
checks["availableStatusCountsMatch"] = all(metrics["statusCounts"].get(status) == count
    for status, count in status_counts.items())
evidence = {"observedAt": env.stamp(), "runtimeInput": "V1.5", "schema": schema,
    "independent": independent, "apiMetrics": {"today": metrics, "week": week["metrics"],
                                     "config": config_today["metrics"]},
    "statusFixture": status_counts, "dryRunStates": dry_run_counts,
    "latestExceptions": today.get("latestExceptions"),
    "checks": checks, "observedStatusCount": len([v for v in status_counts.values() if v > 0]),
    "requiredStatusFixtureCount": 9}
OUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"checks": checks, "observedStatusCount": evidence["observedStatusCount"],
                  "latestExceptions": len(evidence["latestExceptions"]), "evidence": str(OUT)}, ensure_ascii=False))
