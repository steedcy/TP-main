"""Finish TC-068 extension lifecycle and preserve disable / history evidence."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
db_spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(db_spec)
db_spec.loader.exec_module(db)
first = json.loads((Path(__file__).parent / "evidence/TC-068-dynamic-definition-api.json").read_text(encoding="utf-8"))
submitted = json.loads((Path(__file__).parent / "evidence/TC-031-068-dynamic-submit.json").read_text(encoding="utf-8"))
config, operator = local.API("配置管理员"), local.API("运行操作员")
id_, code = first["observations"]["id"], first["observations"]["definitionCode"]
task_id = submitted["observations"]["afterMissingMaxTaskId"]
out = Path(__file__).parent / "evidence/TC-068-dynamic-disable.json"
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "definitionId": id_, "definitionCode": code, "historicalTaskId": task_id, "observations": {}}

def safe_sql(value):
    return value.replace("'", "''")

ev["observations"]["logsBeforeDisable"] = db.query(db.source,
    "SELECT operation_type,operation_target,operation_result FROM tip_stage2_v14.operation_logs "
    f"WHERE operation_target='{safe_sql(first['definitionName'])}' ORDER BY id").splitlines()
ev["observations"]["taskBeforeDisable"] = operator(f"/tasks/{task_id}")
config(f"/task-definitions/{id_}/disable", "POST")
ev["observations"]["detailAfterDisable"] = config(f"/task-definitions/{id_}")
ev["observations"]["historicalTaskAfterDisable"] = operator(f"/tasks/{task_id}")
ev["observations"]["logsAfterDisable"] = db.query(db.source,
    "SELECT operation_type,operation_target,operation_result FROM tip_stage2_v14.operation_logs "
    f"WHERE operation_target='{safe_sql(first['definitionName'])}' ORDER BY id").splitlines()
ev["observations"]["allListStillContains"] = any(d["id"] == id_ for d in config("/task-definitions"))
try:
    ev["observations"]["newSubmitAfterDisable"] = local.request(local.BASE + "/tasks", "POST",
        {"taskGoal": "测", "taskFamily": code, "sceneParams": {"sampleLocation": "F2虚构区"}}, operator.token)
except RuntimeError as error:
    ev["observations"]["newSubmitAfterDisableError"] = str(error)
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"disabled": ev["observations"]["detailAfterDisable"]["definitionStatus"],
                  "historicalTaskStatus": ev["observations"]["historicalTaskAfterDisable"]["status"],
                  "newSubmitError": ev["observations"].get("newSubmitAfterDisableError"),
                  "logs": ev["observations"]["logsAfterDisable"]}, ensure_ascii=False))
