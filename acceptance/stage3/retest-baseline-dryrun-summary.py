"""Cross-check fresh stage-3 dry-run tasks, frozen plans, commands and dashboard totals."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
db_spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(db_spec)
db_spec.loader.exec_module(db)
life = json.loads((here / "evidence/TC-028-030-baseline-dryrun-lifecycle.json").read_text(encoding="utf-8"))
ui1 = json.loads((here / "evidence/TC-028-baseline-dryrun-ui-attempt1.json").read_text(encoding="utf-8"))
ui2 = json.loads((here / "evidence/TC-028-baseline-dryrun-ui.json").read_text(encoding="utf-8"))
ids = [x["taskId"] for x in life["runs"]] + [ui1["taskId"], ui2["taskId"]]
assert len(ids) == len(set(ids)) == 4
ids_sql = ",".join(map(str, ids))
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "stage3DryRunTaskIds": ids, "templateName": life["templateName"]}
ev["taskPlanRows"] = db.query(db.source,
    "SELECT t.id,t.status,t.is_dry_run,p.source,p.snapshot_id,p.frozen_at IS NOT NULL "
    "FROM tip_stage2_v14.tasks t JOIN tip_stage2_v14.plan_versions p ON p.id=t.current_plan_version_id "
    "WHERE t.id IN (" + ids_sql + ") ORDER BY t.id").splitlines()
ev["commandRows"] = db.query(db.source,
    "SELECT task_id,command_type,command_status,command_id, "
    "CASE WHEN response_payload IS NULL THEN 'N' ELSE 'Y' END "
    "FROM tip_stage2_v14.device_commands WHERE task_id IN (" + ids_sql + ") "
    "ORDER BY task_id,id").splitlines()
ev["eventCountByTask"] = db.query(db.source,
    "SELECT task_id,count(*) FROM tip_stage2_v14.task_events WHERE task_id IN (" + ids_sql + ") "
    "GROUP BY task_id ORDER BY task_id").splitlines()
ev["formalCompletedSql"] = int(db.query(db.source,
    "SELECT count(*) FROM tip_stage2_v14.tasks WHERE status='COMPLETED' AND is_dry_run=false"))
ev["dryRunCompletedSql"] = int(db.query(db.source,
    "SELECT count(*) FROM tip_stage2_v14.tasks WHERE status='COMPLETED' AND is_dry_run=true"))
ev["allCompletedSql"] = int(db.query(db.source,
    "SELECT count(*) FROM tip_stage2_v14.tasks WHERE status='COMPLETED'"))
operator = local.API("运行操作员")
dashboard = operator("/dashboard/overview?period=TODAY")
ev["dashboardCompleted"] = dashboard["metrics"]["statusCounts"]["COMPLETED"]
admin = local.API("配置管理员")
logs = admin("/operation-logs?page=1&size=100")["content"]
ev["templateAuditTypes"] = sorted({x["operationType"] for x in logs
    if life["templateName"] in str(x.get("operationTarget", ""))})
ev["templateFinalStatus"] = next(x["templateStatus"] for x in admin("/baseline-templates")
                                 if x["templateName"] == life["templateName"])
out = here / "evidence/TC-028-030-baseline-dryrun-summary.json"
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(ev, ensure_ascii=False))
