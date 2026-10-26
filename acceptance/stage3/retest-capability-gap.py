"""TC-036.S1: reversible isolated-schema all-required-capabilities gap."""
import importlib.util
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
db_spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(db_spec)
db_spec.loader.exec_module(db)
operator = local.API("运行操作员")
config = local.API("配置管理员")
source = operator("/tasks/19")
assert source["status"] == "COMPLETED" and source["taskFamily"] == "OVERSIZE_BAGGAGE_HANDLING"
required = ["CAP_BAGGAGE_MEASURE", "CAP_OVERSIZE_ALERT", "CAP_NAVIGATION", "CAP_NOTIFICATION"]
query = ("SELECT c.id,d.device_code,c.capability_type,c.capability_status "
         "FROM tip_stage2_v14.device_capabilities c "
         "JOIN tip_stage2_v14.devices d ON d.id=c.device_id "
         "WHERE d.device_code LIKE 'SIM_F2_%' ORDER BY c.id")
rows = [line.split("|") for line in db.query(db.source, query).splitlines()]
target = [row for row in rows if row[2] in required and row[3] == "ENABLED"]
assert target and all(any(row[2] == cap for row in target) for cap in required)
assert any(row[2] not in required and row[3] == "ENABLED" for row in rows)
agents = [a for a in config("/device-agents?page=1&size=100")["content"]
          if a["deviceCode"].startswith("SIM_F2_")]
assert len(agents) == 6 and all(a["agentStatus"] == "ENABLED" and
                                a["onlineStatus"] == "ONLINE" and
                                a["workStatus"] == "IDLE" for a in agents)
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "schema": "tip_stage2_v14",
      "runtimeInput": "V1.5", "requiredCapabilities": required,
      "capabilitiesBefore": rows, "injectedCapabilityIds": [row[0] for row in target],
      "capabilitiesDuring": None, "task": {}, "snapshot": {}, "restore": {}}
journal = root / ".local-test/planning-requests.jsonl"
check_journal = os.environ.get("STAGE3_CHECK_MODEL_JOURNAL") == "1"
if check_journal:
    ev["modelFixture"] = {"beforeLines": len(journal.read_text(encoding="utf-8").splitlines())
                          if journal.exists() else 0}
out = Path(__file__).parent / "evidence" / (
    "TC-036-capability-gap-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
changed = False
task_id = None
ids = ",".join(row[0] for row in target)
try:
    db.query(db.source, "UPDATE tip_stage2_v14.device_capabilities "
             "SET capability_status='DISABLED' WHERE id IN (" + ids + ")")
    changed = True
    ev["capabilitiesDuring"] = [line.split("|") for line in db.query(db.source, query).splitlines()]
    assert all(next(r for r in ev["capabilitiesDuring"] if r[0] == row[0])[3] == "DISABLED"
               for row in target)
    before_id = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
    request = {"taskGoal": source["taskGoal"], "taskFamily": source["taskFamily"],
               "sceneParams": source["sceneParams"]}
    ev["task"]["request"] = request
    ev["task"]["beforeMaxId"] = before_id
    try:
        ev["task"]["submitResponse"] = operator("/tasks", "POST", request)
    except RuntimeError as error:
        ev["task"]["submitError"] = str(error)
    after_id = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
    ev["task"]["afterMaxId"] = after_id
    if after_id > before_id:
        task_id = after_id
        deadline = time.monotonic() + 45
        contexts = []
        while time.monotonic() < deadline:
            contexts = operator(f"/tasks/{task_id}/context-snapshots")
            if contexts:
                break
            time.sleep(0.5)
        ev["snapshot"]["raw"] = contexts
        if contexts:
            first = min(contexts, key=lambda c: c["id"])
            ev["snapshot"]["coverage"] = json.loads(first["capabilityCoverage"])
            ev["snapshot"]["agents"] = json.loads(first["agents"])
finally:
    if changed:
        cases = " ".join("WHEN " + row[0] + " THEN '" + row[3] + "'" for row in target)
        db.query(db.source, "UPDATE tip_stage2_v14.device_capabilities SET capability_status=CASE id " +
                 cases + " END WHERE id IN (" + ids + ")")
        ev["restore"]["capabilities"] = [line.split("|") for line in db.query(db.source, query).splitlines()]
        ev["restore"]["exact"] = ev["restore"]["capabilities"] == rows
    if task_id:
        task = operator(f"/tasks/{task_id}")
        ev["task"]["final"] = task
        ev["task"]["events"] = operator(f"/tasks/{task_id}/events")
        ev["task"]["planVersions"] = operator(f"/tasks/{task_id}/plan-versions")
    if check_journal:
        ev["modelFixture"]["newRequests"] = [json.loads(line) for line in
            journal.read_text(encoding="utf-8").splitlines()[ev["modelFixture"]["beforeLines"]:]]
    ev["restore"]["agents"] = [a for a in config("/device-agents?page=1&size=100")["content"]
                               if a["deviceCode"].startswith("SIM_F2_")]
    ev["restore"]["allSixOnlineIdle"] = len(ev["restore"]["agents"]) == 6 and all(
        a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE" and
        a["workStatus"] == "IDLE" for a in ev["restore"]["agents"])
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"taskId": task_id, "gap": ev["snapshot"].get("coverage"),
                  "status": ev["task"].get("final", {}).get("status"),
                  "eventErrors": [e.get("errorCode") for e in ev["task"].get("events", []) if e.get("errorCode")],
                  "restored": ev["restore"].get("exact"), "sixOnlineIdle": ev["restore"]["allSixOnlineIdle"],
                  "evidence": str(out)}, ensure_ascii=False))
