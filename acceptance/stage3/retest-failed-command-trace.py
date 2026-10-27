"""Read task 83's command attempts and the event timeline around its manual transition."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


local = module("local", root / "scripts/local-test-environment.py")
db = module("db", root / "acceptance/stage2/db-isolation.py")
operator = local.API("运行操作员")
pre = json.loads((stage / "evidence/TC-050-baseline-failure-20261027T042130Z.json")
                 .read_text(encoding="utf-8"))
assert pre["task"]["id"] == 83 and pre["task"]["status"] == "PENDING_MANUAL"
sql = ("SELECT command_id,agent_code,command_type,attempt_no,command_status,step_seq "
       "FROM tip_stage2_v14.device_commands WHERE task_id=83 ORDER BY id")
rows = [line.split("|") for line in db.query(db.source, sql).splitlines()]
after = operator("/tasks/83")
events_after = operator("/tasks/83/events")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "taskId": 83,
      "commands": rows, "beforeCleanupTaskStatus": pre["task"]["status"],
      "beforeCleanupEventTypes": [e["eventType"] for e in pre["events"]],
      "afterCleanupTaskStatus": after["status"],
      "afterCleanupEventTypes": [e["eventType"] for e in events_after],
      "sourceEvidence": "TC-050-baseline-failure-20261027T042130Z.json"}
out = stage / "evidence" / ("TC-050-failed-command-trace-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": out.name, "commandCount": len(rows),
                  "attempts": [(r[0], r[3], r[4]) for r in rows if r[2] == "EXECUTE_CAPABILITY"],
                  "beforeStatus": ev["beforeCleanupTaskStatus"],
                  "beforeTerminalStatusEvents": [t for t in ev["beforeCleanupEventTypes"]
                    if "MANUAL" in t or "STATUS" in t],
                  "afterStatus": ev["afterCleanupTaskStatus"]}, ensure_ascii=False))
