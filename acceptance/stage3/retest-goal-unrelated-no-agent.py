"""TC-033.S1: unrelated goal and zero enabled-online agent guard, with restoration."""
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
agents = [a for a in config("/device-agents?page=1&size=100")["content"]
          if a["deviceCode"].startswith("SIM_F2_")]
assert len(agents) == 6 and all(a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE"
                                and a["workStatus"] == "IDLE" for a in agents)
active = int(db.query(db.source, "SELECT count(*) FROM tip_stage2_v14.device_agents "
                      "WHERE agent_status='ENABLED' AND online_status='ONLINE'"))
assert active == 6
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "beforeAgents": agents, "beforeTaskId": int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks")),
      "unrelated": {}, "noAgent": {}, "restore": {}}
out = Path(__file__).parent / "evidence/TC-033-unrelated-no-agent.json"
disabled = []
try:
    goal = "请预测虚构上市公司明日股价；这与机场旅客服务、设备操作及航班信息均无关。"
    ev["unrelated"]["request"] = {"taskGoal": goal}
    try:
        ev["unrelated"]["response"] = local.request(local.BASE + "/tasks", "POST", {"taskGoal": goal}, operator.token)
    except RuntimeError as error:
        ev["unrelated"]["error"] = str(error)
    task_id = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
    ev["unrelated"]["afterTaskId"] = task_id
    if task_id > ev["beforeTaskId"]:
        ev["unrelated"]["task"] = operator(f"/tasks/{task_id}")
        ev["unrelated"]["events"] = operator(f"/tasks/{task_id}/events")
        ev["unrelated"]["planVersions"] = operator(f"/tasks/{task_id}/plan-versions")

    for agent in agents:
        config(f"/device-agents/{agent['agentId']}/disable", "POST", {"confirmed": True})
        disabled.append(agent)
    ev["noAgent"]["enabledOnlineCount"] = int(db.query(db.source,
        "SELECT count(*) FROM tip_stage2_v14.device_agents WHERE agent_status='ENABLED' AND online_status='ONLINE'"))
    assert ev["noAgent"]["enabledOnlineCount"] == 0
    before = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
    ev["noAgent"]["request"] = {"taskGoal": "请在虚构F2测试区显示一条协助提示。"}
    try:
        ev["noAgent"]["response"] = local.request(local.BASE + "/tasks", "POST", ev["noAgent"]["request"], operator.token)
    except RuntimeError as error:
        ev["noAgent"]["error"] = str(error)
    ev["noAgent"]["taskIdBefore"] = before
    ev["noAgent"]["taskIdAfter"] = int(db.query(db.source, "SELECT max(id) FROM tip_stage2_v14.tasks"))
finally:
    ev["restore"]["reenable"] = []
    for agent in disabled:
        try:
            restored = config("/device-agents", "POST", {"deviceCode": agent["deviceCode"]})
            ev["restore"]["reenable"].append({"deviceCode": agent["deviceCode"],
                                              "agentId": restored["agentId"],
                                              "agentStatus": restored["agentStatus"],
                                              "onlineStatus": restored["onlineStatus"]})
        except Exception as error:
            ev["restore"]["reenable"].append({"deviceCode": agent["deviceCode"], "error": str(error)})
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        now = [a for a in config("/device-agents?page=1&size=100")["content"]
               if a["deviceCode"].startswith("SIM_F2_")]
        if len(now) == 6 and all(a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE"
                                 and a["workStatus"] == "IDLE" for a in now):
            break
        time.sleep(1)
    ev["restore"]["agents"] = now
    ev["restore"]["allSixOnlineIdle"] = len(now) == 6 and all(
        a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE"
        for a in now)
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"unrelatedError": ev["unrelated"].get("error"),
                  "unrelatedStatus": ev["unrelated"].get("task", {}).get("status"),
                  "unrelatedPlans": len(ev["unrelated"].get("planVersions", [])),
                  "noAgentError": ev["noAgent"].get("error"),
                  "noAgentCreated": ev["noAgent"].get("taskIdAfter") != ev["noAgent"].get("taskIdBefore"),
                  "allSixOnlineIdle": ev["restore"]["allSixOnlineIdle"]}, ensure_ascii=False))
