"""TC-035.S1 retry: answer model clarifications before archived-agent snapshot."""
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
operator = local.API("运行操作员")
config = local.API("配置管理员")
agent = next(a for a in config("/device-agents?page=1&size=100")["content"]
             if a["deviceCode"] == "SIM_F2_ROBOT_B")
assert agent["agentStatus"] == "ENABLED" and agent["onlineStatus"] == "ONLINE" and agent["workStatus"] == "IDLE"
code = agent["agentId"]
source = operator("/tasks/19")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "schema": "tip_stage2_v14", "injectionAgent": agent, "task": {}, "snapshot": {}, "restore": {}}
out = Path(__file__).parent / "evidence/TC-035-context-archived-agent-retry.json"
injected = False
task_id = None
try:
    db.query(db.source, "UPDATE tip_stage2_v14.device_agents SET agent_status='ARCHIVED',online_status='OFFLINE' "
             "WHERE agent_code='" + code + "' AND agent_status='ENABLED'")
    injected = True
    ev["injectedState"] = db.query(db.source, "SELECT agent_status,online_status FROM tip_stage2_v14.device_agents "
                                    "WHERE agent_code='" + code + "'")
    assert ev["injectedState"] == "ARCHIVED|OFFLINE"
    before = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
    request = {"taskGoal": source["taskGoal"], "taskFamily": source["taskFamily"],
               "sceneParams": source["sceneParams"]}
    ev["task"]["request"] = request
    try:
        ev["task"]["submitResponse"] = operator("/tasks", "POST", request)
    except RuntimeError as error:
        ev["task"]["submitError"] = str(error)
    after = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
    assert after > before
    task_id = after
    ev["task"]["id"] = task_id
    ev["task"]["clarifications"] = []
    current = operator(f"/tasks/{task_id}")
    for round_no in range(1, 3):
        if current["status"] != "PLANNING" or not current.get("missingInfoQuestions"):
            break
        answers = {q: "F2_BAGGAGE_POINT是阶段3预置的虚构行李当前位置编码，可直接测量；无需先引导到其他地点。目标地点是F2_TEST_GATE，均为预置虚构测试点。"
                   for q in current["missingInfoQuestions"]}
        row = {"round": round_no, "questions": current["missingInfoQuestions"], "answers": answers}
        try:
            row["response"] = operator(f"/tasks/{task_id}/clarify", "POST", {"answers": answers})
        except RuntimeError as error:
            row["error"] = str(error)
        current = operator(f"/tasks/{task_id}")
        row["afterStatus"] = current["status"]
        ev["task"]["clarifications"].append(row)
    deadline = time.monotonic() + 45
    contexts = []
    while time.monotonic() < deadline:
        contexts = operator(f"/tasks/{task_id}/context-snapshots")
        if contexts:
            break
        time.sleep(0.5)
    ev["snapshot"]["raw"] = contexts
    if contexts:
        initial = min(contexts, key=lambda c: c["id"])
        ev["snapshot"]["agents"] = json.loads(initial["agents"])
        ev["snapshot"]["coverage"] = json.loads(initial["capabilityCoverage"])
finally:
    if injected:
        db.query(db.source, "UPDATE tip_stage2_v14.device_agents SET agent_status='ENABLED',online_status='ONLINE' "
                 "WHERE agent_code='" + code + "' AND agent_status='ARCHIVED'")
        ev["restore"]["agentState"] = db.query(db.source, "SELECT agent_status,online_status FROM "
            "tip_stage2_v14.device_agents WHERE agent_code='" + code + "'")
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
                    {"confirmed": True, "reason": "阶段3归档代理快照复测清场"})
            except Exception as error:
                ev["restore"]["taskTerminateError"] = str(error)
        ev["task"]["final"] = task
        ev["task"]["events"] = operator(f"/tasks/{task_id}/events")
    current = [a for a in config("/device-agents?page=1&size=100")["content"]
               if a["deviceCode"].startswith("SIM_F2_")]
    ev["restore"]["allSixOnlineIdle"] = len(current) == 6 and all(
        a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE"
        for a in current)
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"taskId": task_id, "archivedExcluded": all(a["agentId"] != code for a in ev["snapshot"].get("agents", [])),
                  "snapshotAgents": len(ev["snapshot"].get("agents", [])),
                  "restored": ev["restore"].get("agentState"),
                  "allSixOnlineIdle": ev["restore"].get("allSixOnlineIdle")}, ensure_ascii=False))
