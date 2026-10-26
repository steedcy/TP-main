"""TC-035.S1: inject three non-enabled capability states, build live context, restore."""
import importlib.util
import json
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
config, operator = local.API("配置管理员"), local.API("运行操作员")
targets = {"SIM_F2_FLIGHT": "UNTESTED", "SIM_F2_ROBOT_B": "TESTED_FAILED",
           "SIM_F2_DISPLAY": "DISABLED"}
query = ("SELECT c.id,d.device_code,c.capability_code,c.capability_status "
         "FROM tip_stage2_v14.device_capabilities c JOIN tip_stage2_v14.devices d ON d.id=c.device_id "
         "WHERE c.capability_type='CAP_INFO_DISPLAY' ORDER BY d.device_code")
before_rows = [line.split("|") for line in db.query(db.source, query).splitlines()]
selected = {row[1]: row for row in before_rows if row[1] in targets}
assert len(selected) == 3 and all(row[2] == "CAP_INFO_DISPLAY" and row[3] == "ENABLED"
                                  for row in selected.values())
agents = [a for a in config("/device-agents?page=1&size=100")["content"]
          if a["deviceCode"].startswith("SIM_F2_")]
assert len(agents) == 6 and all(a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE"
                                and a["workStatus"] == "IDLE" for a in agents)
source = operator("/tasks/19")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "schema": "tip_stage2_v14", "capabilitiesBefore": before_rows,
      "injectedStates": targets, "capabilitiesDuring": [], "task": {}, "snapshot": {}, "restore": {}}
out = Path(__file__).parent / "evidence/TC-035-context-capability-status.json"
changed = False
task_id = None
try:
    cases = " ".join("WHEN " + selected[code][0] + " THEN '" + status + "'"
                     for code, status in targets.items())
    ids = ",".join(selected[code][0] for code in targets)
    db.query(db.source, "UPDATE tip_stage2_v14.device_capabilities SET capability_status=CASE id " +
             cases + " END WHERE id IN (" + ids + ")")
    changed = True
    ev["capabilitiesDuring"] = [line.split("|") for line in db.query(db.source, query).splitlines()]
    assert all(next(row for row in ev["capabilitiesDuring"] if row[1] == code)[3] == status
               for code, status in targets.items())
    before_id = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
    ev["task"]["request"] = {"taskGoal": source["taskGoal"], "taskFamily": source["taskFamily"],
                              "sceneParams": source["sceneParams"]}
    try:
        ev["task"]["submitResponse"] = operator("/tasks", "POST", ev["task"]["request"])
    except RuntimeError as error:
        ev["task"]["submitError"] = str(error)
    after_id = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
    ev["task"]["beforeMaxId"] = before_id
    ev["task"]["afterMaxId"] = after_id
    assert after_id > before_id
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
        initial = min(contexts, key=lambda item: item["id"])
        ev["snapshot"]["initialId"] = initial["id"]
        ev["snapshot"]["agents"] = json.loads(initial["agents"])
        ev["snapshot"]["coverage"] = json.loads(initial["capabilityCoverage"])
        ev["snapshot"]["failed"] = json.loads(initial["failedAgentCodes"])
finally:
    if changed:
        ids = ",".join(selected[code][0] for code in targets)
        db.query(db.source, "UPDATE tip_stage2_v14.device_capabilities SET capability_status='ENABLED' "
                 "WHERE id IN (" + ids + ")")
        ev["restore"]["capabilities"] = [line.split("|") for line in db.query(db.source, query).splitlines()]
        ev["restore"]["allOriginalStatuses"] = all(
            next(row for row in ev["restore"]["capabilities"] if row[0] == original[0])[3] == original[3]
            for original in before_rows)
    if task_id:
        deadline = time.monotonic() + 35
        task = operator(f"/tasks/{task_id}")
        while task["status"] in ["PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT", "DOWNGRADING", "EXECUTING"] \
                and time.monotonic() < deadline:
            time.sleep(1)
            task = operator(f"/tasks/{task_id}")
        if task["status"] in ["PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT", "DOWNGRADING", "EXECUTING"]:
            try:
                task = operator(f"/tasks/{task_id}/terminate", "POST",
                    {"confirmed": True, "reason": "阶段3能力状态快照复测清场"})
            except Exception as error:
                ev["restore"]["taskTerminateError"] = str(error)
        ev["task"]["final"] = task
        ev["task"]["events"] = operator(f"/tasks/{task_id}/events")
    current_agents = [a for a in config("/device-agents?page=1&size=100")["content"]
                      if a["deviceCode"].startswith("SIM_F2_")]
    ev["restore"]["allSixOnlineIdle"] = len(current_agents) == 6 and all(
        a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE"
        for a in current_agents)
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"taskId": task_id, "snapshotAgents": len(ev["snapshot"].get("agents", [])),
                  "targetCapsInSnapshot": {code: next((a for a in ev["snapshot"].get("agents", [])
                      if a["deviceCode"] == code), {}).get("capabilities") for code in targets},
                  "restored": ev["restore"].get("allOriginalStatuses"),
                  "allSixOnlineIdle": ev["restore"].get("allSixOnlineIdle")}, ensure_ascii=False))
