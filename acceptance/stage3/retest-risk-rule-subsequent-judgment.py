"""TC-043.S2: compare subsequent plans with a deterministic rule enabled/disabled."""
import importlib.util
import json
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
operator, config = local.API("运行操作员"), local.API("配置管理员")
source = operator("/tasks/55")
assert source["status"] == "COMPLETED"
request = {"taskGoal": source["taskGoal"], "taskFamily": source["taskFamily"],
           "sceneParams": source["sceneParams"]}
code = "RULE_RESOURCE_CRITICAL"
initial_rule = next(r for r in config("/risk-rules") if r["ruleCode"] == code)
assert initial_rule["enabled"]
agents = [a for a in config("/device-agents?page=1&size=100")["content"]
          if a["deviceCode"].startswith("SIM_F2_")]
assert len(agents) == 6 and all(a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE"
                                for a in agents)
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "sourceTaskId": 55, "request": request,
      "riskRuleBefore": initial_rule, "cases": [], "restore": {}}
out = stage / "evidence" / ("TC-043-risk-rule-subsequent-judgment-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")


def run_case(label):
    rule = next(r for r in config("/risk-rules") if r["ruleCode"] == code)
    case = {"label": label, "ruleAtSubmit": rule}
    ev["cases"].append(case)
    task_id = None
    try:
        response = operator("/tasks", "POST", request)
        task_id = response["id"]
        case["submitted"] = {key: response.get(key) for key in
                             ("id", "taskCode", "status", "createdAt")}
        deadline = time.monotonic() + 70
        while time.monotonic() < deadline:
            task = operator(f"/tasks/{task_id}")
            if task["status"] not in {"PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT",
                                       "DOWNGRADING", "EXECUTING"}:
                break
            time.sleep(1)
        case["task"] = {key: task.get(key) for key in
                        ("id", "taskCode", "status", "failureReason", "downgradeReason",
                         "currentPlanVersionId", "updatedAt")}
        case["plans"] = operator(f"/tasks/{task_id}/plan-versions")
        case["events"] = operator(f"/tasks/{task_id}/events")
    except Exception as error:
        case["error"] = str(error)
    finally:
        if task_id is not None:
            task = operator(f"/tasks/{task_id}")
            if task["status"] in {"PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT",
                                  "DOWNGRADING", "EXECUTING", "PENDING_MANUAL"}:
                try:
                    case["cleanup"] = operator(f"/tasks/{task_id}/terminate", "POST",
                                               {"reason": "阶段3风险规则启停对照已记录",
                                                "confirmed": True})["status"]
                except RuntimeError as error:
                    case["cleanupError"] = str(error)
        out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


try:
    run_case("enabled_before")
    ev["disabled"] = config("/risk-rules/" + code + "/update", "POST", {"enabled": False})
    run_case("disabled")
finally:
    current = next(r for r in config("/risk-rules") if r["ruleCode"] == code)
    if not current["enabled"]:
        ev["restore"]["enableResponse"] = config("/risk-rules/" + code + "/update",
                                                  "POST", {"enabled": True})
    ev["restore"]["rule"] = next(r for r in config("/risk-rules") if r["ruleCode"] == code)
    ev["restore"]["agents"] = [{key: a.get(key) for key in
                                ("deviceCode", "agentStatus", "onlineStatus", "workStatus", "currentTaskId")}
                               for a in config("/device-agents?page=1&size=100")["content"]
                               if a["deviceCode"].startswith("SIM_F2_")]
    ev["restore"]["audit"] = [r for r in
                              config("/operation-logs?operationType=RISK_RULE_CHANGE&page=1&size=100")["content"]
                              if r.get("operationTarget") == code]
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "cases": [{"label": c["label"],
    "taskId": c.get("submitted", {}).get("id"), "status": c.get("task", {}).get("status"),
    "plans": [(p["source"], p.get("riskLevel"), p.get("riskReasonCode"), p.get("ruleSetVersion"))
              for p in c.get("plans", [])], "error": c.get("error")}
    for c in ev["cases"]], "ruleRestored": ev["restore"]["rule"]["enabled"],
    "ruleVersion": ev["restore"]["rule"]["ruleVersion"]}, ensure_ascii=False))
