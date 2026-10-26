"""TC-039: compare complete autonomous candidate with missing mandatory metadata."""
import copy
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
operator, config = local.API("运行操作员"), local.API("配置管理员")
source_mode = os.environ.get("STAGE3_PLAN_FAMILY", "oversize")
if source_mode == "flight":
    fixture = next(f for f in json.loads((root / "scripts/test-fixtures/baselines.json").read_text(
        encoding="utf-8")) if f["taskFamily"] == "FLIGHT_CHANGE_RESPONSE")
    params = {p["name"]: p.get("defaultValue") for p in fixture["inputParams"]}
    params.update(flightNumber="R08Z81", targetLocation="F2_TEST_GATE")
    request = {"taskGoal": "虚构航班R08Z81登机口由GATE_A05改至F2_TEST_GATE，更新航班信息屏，通知旅客并引导至新登机口。仅为测试。",
               "taskFamily": "FLIGHT_CHANGE_RESPONSE", "sceneParams": params}
else:
    source = operator("/tasks/19")
    request = {"taskGoal": source["taskGoal"], "taskFamily": source["taskFamily"],
               "sceneParams": source["sceneParams"]}
mode_path = root / ".local-test/planning-fault.json"
journal = root / ".local-test/planning-requests.jsonl"
old_mode = mode_path.read_text(encoding="utf-8")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "schema": "tip_stage2_v14", "fixtureModeBefore": json.loads(old_mode),
      "sourceMode": source_mode, "request": request, "cases": [],
      "fixtureModeRestored": False, "agentsAfter": None}
out = Path(__file__).parent / "evidence" / (
    "TC-039-plan-six-fields-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")

def run_case(label, override=None):
    mode = json.loads(old_mode)
    mode.update(goal="success", planning="success", replanning="success")
    mode.pop("initialPlanSteps", None)
    if override is not None:
        mode["initialPlanSteps"] = override
    mode_path.write_text(json.dumps(mode, ensure_ascii=False), encoding="utf-8")
    old_lines = len(journal.read_text(encoding="utf-8").splitlines())
    case = {"label": label, "fixtureModeDuring": mode,
            "beforeMaxTaskId": int(db.query(db.source,
                "SELECT max(id) FROM tip_stage2_v14.tasks")),
            "response": None, "submitError": None, "elapsedSeconds": None,
            "afterMaxTaskId": None, "task": None, "events": None,
            "contexts": None, "plans": None, "deviceCommands": None,
            "assignments": None, "modelRequests": None}
    ev["cases"].append(case)
    started = time.monotonic()
    try:
        case["response"] = operator("/tasks", "POST", request)
    except Exception as error:
        case["submitError"] = str(error)
    case["elapsedSeconds"] = time.monotonic() - started
    case["afterMaxTaskId"] = int(db.query(db.source,
        "SELECT max(id) FROM tip_stage2_v14.tasks"))
    if case["afterMaxTaskId"] > case["beforeMaxTaskId"]:
        task_id = case["afterMaxTaskId"]
        deadline = time.monotonic() + 50
        while time.monotonic() < deadline:
            case["task"] = operator(f"/tasks/{task_id}")
            if case["task"]["status"] not in ["PLANNING", "SUPERVISING", "PENDING_ASSIGNMENT",
                                               "DOWNGRADING", "EXECUTING"]:
                break
            time.sleep(1)
        case["events"] = operator(f"/tasks/{task_id}/events")
        case["contexts"] = operator(f"/tasks/{task_id}/context-snapshots")
        case["plans"] = operator(f"/tasks/{task_id}/plan-versions")
        case["deviceCommands"] = db.query(db.source,
            f"SELECT command_status,capability_type FROM tip_stage2_v14.device_commands WHERE task_id={task_id} ORDER BY id")
        case["assignments"] = db.query(db.source,
            f"SELECT step_seq,step_status FROM tip_stage2_v14.task_step_assignments WHERE task_id={task_id} ORDER BY id")
    case["modelRequests"] = [json.loads(line) for line in
        journal.read_text(encoding="utf-8").splitlines()[old_lines:]]
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return case

try:
    complete = run_case("complete_candidate")
    autonomous = next((p for p in complete["plans"] if p["source"] == "AUTONOMOUS"), None)
    if autonomous is None:
        raise RuntimeError("Complete fixture did not create an autonomous candidate")
    incomplete = copy.deepcopy(autonomous["planSteps"])
    for step in incomplete:
        step.pop("precondition", None)
        step.pop("failureHandling", None)
    run_case("missing_precondition_and_failure_handling", incomplete)
finally:
    mode_path.write_text(old_mode, encoding="utf-8")
    ev["fixtureModeRestored"] = mode_path.read_text(encoding="utf-8") == old_mode
    ev["agentsAfter"] = [a for a in config("/device-agents?page=1&size=100")["content"]
                         if a["deviceCode"].startswith("SIM_F2_")]
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"cases": [{"label": c["label"], "taskId": c["afterMaxTaskId"],
                             "status": c["task"]["status"] if c["task"] else None,
                             "plans": [(p["source"], p["structureCheckResult"],
                                        p["capabilityCheckResult"], p["constraintCheckResult"],
                                        bool(p["frozenAt"])) for p in c["plans"]]
                             if c["plans"] else []} for c in ev["cases"]],
                  "restored": ev["fixtureModeRestored"], "evidence": str(out)}, ensure_ascii=False))
