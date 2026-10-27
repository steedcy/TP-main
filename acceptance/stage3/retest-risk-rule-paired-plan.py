"""TC-043.S2: use the same frozen candidate while toggling resource risk rule."""
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
prior = json.loads((stage / "evidence/TC-043-risk-rule-subsequent-judgment-20261027T034211Z.json")
                   .read_text(encoding="utf-8"))
reference = prior["cases"][1]["plans"][0]
assert reference["source"] == "AUTONOMOUS"
assert all(reference[key] == "PASS" for key in
           ("structureCheckResult", "capabilityCheckResult", "constraintCheckResult"))
mode_path = root / ".local-test/planning-fault.json"
journal = root / ".local-test/planning-requests.jsonl"
original_mode = mode_path.read_text(encoding="utf-8")
mode = json.loads(original_mode)
mode.update(goal="success", planning="success", replanning="success",
            initialPlanSteps=reference["planSteps"])
code = "RULE_RESOURCE_CRITICAL"
rule_before = next(r for r in config("/risk-rules") if r["ruleCode"] == code)
assert rule_before["enabled"]
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "referencePlanId": reference["id"],
      "sourceEvidence": "TC-043-risk-rule-subsequent-judgment-20261027T034211Z.json",
      "request": {**prior["request"], "taskGoal": prior["request"]["taskGoal"] +
                  "本次通知范围为全部旅客，均为虚构测试对象。"},
      "fixtureBefore": json.loads(original_mode),
      "fixtureDuring": mode, "ruleBefore": rule_before, "cases": [], "restore": {}}
out = stage / "evidence" / ("TC-043-risk-rule-paired-plan-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")


def run_case(label):
    rule = next(r for r in config("/risk-rules") if r["ruleCode"] == code)
    offset = len(journal.read_text(encoding="utf-8").splitlines())
    case = {"label": label, "ruleAtSubmit": rule, "clarifications": []}
    ev["cases"].append(case)
    task_id = None
    try:
        task = operator("/tasks", "POST", ev["request"])
        task_id = task["id"]
        case["submitted"] = {k: task.get(k) for k in ("id", "taskCode", "status")}
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            task = operator(f"/tasks/{task_id}")
            questions = task.get("missingInfoQuestions") or []
            if task["status"] == "PLANNING" and questions and len(case["clarifications"]) < 3:
                answer = ("请通知全部旅客；虚构航班R08Z81由GATE_A05改至F2_TEST_GATE，"
                          "更新航班信息屏并由机器人通知与引导至新登机口。")
                task = operator(f"/tasks/{task_id}/clarify", "POST",
                                {"answers": {question: answer for question in questions}})
                case["clarifications"].append({"questions": questions, "answer": answer,
                                               "returnedStatus": task["status"]})
                continue
            if task["status"] not in {"PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT",
                                       "DOWNGRADING", "EXECUTING"}:
                break
            time.sleep(1)
        case["task"] = {k: task.get(k) for k in
                        ("status", "downgradeReason", "failureReason", "currentPlanVersionId")}
        case["plans"] = operator(f"/tasks/{task_id}/plan-versions")
        case["events"] = operator(f"/tasks/{task_id}/events")
        case["modelRequests"] = [json.loads(line) for line in
                                 journal.read_text(encoding="utf-8").splitlines()[offset:]]
    except Exception as error:
        case["error"] = str(error)
    finally:
        if task_id is not None:
            task = operator(f"/tasks/{task_id}")
            if task["status"] in {"PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT",
                                  "DOWNGRADING", "EXECUTING", "PENDING_MANUAL"}:
                try:
                    case["cleanup"] = operator(f"/tasks/{task_id}/terminate", "POST",
                                               {"reason": "阶段3同计划风险规则对照已记录",
                                                "confirmed": True})["status"]
                except RuntimeError as error:
                    case["cleanupError"] = str(error)
        out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


try:
    mode_path.write_text(json.dumps(mode, ensure_ascii=False), encoding="utf-8")
    run_case("enabled")
    ev["disabled"] = config("/risk-rules/" + code + "/update", "POST", {"enabled": False})
    run_case("disabled")
finally:
    mode_path.write_text(original_mode, encoding="utf-8")
    ev["restore"]["fixtureExact"] = mode_path.read_text(encoding="utf-8") == original_mode
    current = next(r for r in config("/risk-rules") if r["ruleCode"] == code)
    if not current["enabled"]:
        config("/risk-rules/" + code + "/update", "POST", {"enabled": True})
    ev["restore"]["rule"] = next(r for r in config("/risk-rules") if r["ruleCode"] == code)
    ev["restore"]["agents"] = [{k: a.get(k) for k in
                                ("deviceCode", "agentStatus", "onlineStatus", "workStatus", "currentTaskId")}
                               for a in config("/device-agents?page=1&size=100")["content"]
                               if a["deviceCode"].startswith("SIM_F2_")]
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "cases": [{"label": c["label"],
    "taskId": c.get("submitted", {}).get("id"), "status": c.get("task", {}).get("status"),
    "plans": [(p["source"], p["structureCheckResult"], p["capabilityCheckResult"],
               p["constraintCheckResult"], p.get("riskLevel"), p.get("riskReasonCode"))
              for p in c.get("plans", [])], "modelPhases": [r.get("phase") for r in c.get("modelRequests", [])],
    "error": c.get("error")} for c in ev["cases"]],
    "restored": ev["restore"]["fixtureExact"] and ev["restore"]["rule"]["enabled"]},
    ensure_ascii=False))
