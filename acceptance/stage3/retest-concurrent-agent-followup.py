"""Read persistent command/event order and cleanup after the concurrent claim test."""
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
api = local.API("配置管理员")
operator = local.API("运行操作员")
first = json.loads((stage / "evidence/TC-052-concurrent-claim-20261027T040409Z.json")
                   .read_text(encoding="utf-8"))
ids = (first["first"]["start"]["taskId"], first["backup"]["start"]["taskId"])
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "sourceEvidence": "TC-052-concurrent-claim-20261027T040409Z.json",
      "tasks": {}, "template": api(f"/baseline-templates/{first['templateId']}"),
      "agents": [a for a in api("/device-agents?page=1&size=100")["content"]
                 if a["deviceCode"].startswith("SIM_F2_")]}
for task_id in ids:
    ev["tasks"][str(task_id)] = {"task": operator(f"/tasks/{task_id}"),
                                 "assignments": operator(f"/tasks/{task_id}/step-assignments"),
                                 "events": operator(f"/tasks/{task_id}/events")}
out = stage / "evidence" / ("TC-052-concurrent-followup-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": out.name, "templateStatus": ev["template"]["templateStatus"],
                  "taskStatuses": {k: v["task"]["status"] for k, v in ev["tasks"].items()},
                  "events": {k: [e["eventType"] for e in v["events"]] for k, v in ev["tasks"].items()},
                  "allSixOnlineIdle": len(ev["agents"]) == 6 and all(
                      a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE"
                      and a["currentTaskId"] is None for a in ev["agents"])}, ensure_ascii=False))
