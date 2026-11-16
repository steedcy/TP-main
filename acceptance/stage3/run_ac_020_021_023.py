"""Supplemental branch checks for AC-020, AC-021, and AC-023 against live local services."""
import importlib.util
import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_PATH = ROOT / "acceptance/stage3/evidence/AC-020-021-023-supplemental-20261116.json"

spec = importlib.util.spec_from_file_location("le", ROOT / "scripts/local-test-environment.py")
le = importlib.util.module_from_spec(spec)
spec.loader.exec_module(le)

cfg = le.API("配置管理员")
op = le.API("运行操作员")

AGENTS = {
    "FLIGHT": ["SIM_F2_FLIGHT"],
    "DISPLAY": ["SIM_F2_DISPLAY", "SIM_F2_DISPLAY_B"],
    "ROBOT": ["SIM_F2_ROBOT", "SIM_F2_ROBOT_B"],
}
ALL_AGENTS = [a for group in AGENTS.values() for a in group]


def set_disabled(device_codes, disabled: bool):
    target_status = "OFFLINE" if disabled else "ONLINE"
    for code in device_codes:
        cfg(f"/simulators/{code}/online", "POST", {"onlineStatus": target_status})
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        agents = {a["deviceCode"]: a["onlineStatus"] for a in cfg("/device-agents?size=50")["content"]}
        if all(agents.get(c) == target_status for c in device_codes):
            return
        time.sleep(0.5)


def raw_post(api_obj, path, body):
    try:
        data = api_obj(path, "POST", body)
        return {"ok": True, "http": 200, "data": data}
    except Exception as ex:
        return {"ok": False, "error": str(ex)}


def wait_task_settled(task_id, timeout=90):
    deadline = time.monotonic() + timeout
    t = op(f"/tasks/{task_id}")
    while t["status"] in ("SUBMITTED", "PLANNING", "VALIDATING", "EXECUTING", "REPLANNING", "PENDING_DISPATCH") and time.monotonic() < deadline:
        # Stop early if PLANNING has pending clarification questions
        if t["status"] == "PLANNING" and t.get("missingInfoQuestions"):
            break
        time.sleep(2)
        t = op(f"/tasks/{task_id}")
    return t


def wait_task_terminal(task_id, timeout=120):
    deadline = time.monotonic() + timeout
    t = op(f"/tasks/{task_id}")
    while t["status"] not in ("COMPLETED", "FAILED", "PENDING_MANUAL", "MANUAL_TERMINATED") and time.monotonic() < deadline:
        time.sleep(2)
        t = op(f"/tasks/{task_id}")
    return t


def terminate_if_needed(task_id):
    if not task_id:
        return
    try:
        t = op(f"/tasks/{task_id}")
        if t["status"] not in ("COMPLETED", "FAILED", "MANUAL_TERMINATED"):
            op(f"/tasks/{task_id}/terminate", "POST", {"confirmed": True, "reason": "AC supplemental check cleanup"})
    except Exception:
        pass


def clarify_all(task_id, questions, answer_value):
    answers = {q: answer_value for q in questions}
    return raw_post(op, f"/tasks/{task_id}/clarify", {"answers": answers})


def get_tid(resp):
    d = resp.get("data") or {}
    return d.get("id") or d.get("taskId")


def run_ac_020():
    results = {}

    # 1. Missing assistanceType
    r1 = raw_post(op, "/tasks", {
        "taskFamily": "SPECIAL_PASSENGER_SERVICE",
        "taskGoal": "请为虚构特殊旅客在T2值机区安排会合并前往GATE_A05。",
        "sceneParams": {"origin": "T2值机区", "destination": "GATE_A05"},
    })
    tid1 = get_tid(r1)
    t1_before = wait_task_settled(tid1, timeout=45)
    plans1_before = op(f"/tasks/{tid1}/plan-versions")
    q1 = t1_before.get("missingInfoQuestions") or []
    c1 = clarify_all(tid1, q1, "轮椅陪同") if q1 else {"ok": False, "error": "no questions"}
    t1_after = wait_task_terminal(tid1, timeout=120)
    results["missing_assistanceType"] = {
        "taskId": tid1,
        "statusBeforeClarify": t1_before["status"],
        "questions": q1,
        "planCountBeforeClarify": len(plans1_before),
        "clarifyOk": c1["ok"],
        "statusAfterClarify": t1_after["status"],
        "passed": t1_before["status"] == "PLANNING" and len(plans1_before) == 0 and len(q1) > 0 and c1["ok"] and t1_after["status"] == "COMPLETED",
    }
    terminate_if_needed(tid1)

    # 2. Missing origin
    r2 = raw_post(op, "/tasks", {
        "taskFamily": "SPECIAL_PASSENGER_SERVICE",
        "taskGoal": "请为虚构轮椅陪同旅客安排会合并前往GATE_A05。",
        "sceneParams": {"assistanceType": "轮椅陪同", "destination": "GATE_A05"},
    })
    tid2 = get_tid(r2)
    t2_before = wait_task_settled(tid2, timeout=45)
    plans2_before = op(f"/tasks/{tid2}/plan-versions")
    q2 = t2_before.get("missingInfoQuestions") or []
    c2 = clarify_all(tid2, q2, "T2值机区") if q2 else {"ok": False, "error": "no questions"}
    t2_after = wait_task_terminal(tid2, timeout=120)
    results["missing_origin"] = {
        "taskId": tid2,
        "statusBeforeClarify": t2_before["status"],
        "questions": q2,
        "planCountBeforeClarify": len(plans2_before),
        "clarifyOk": c2["ok"],
        "statusAfterClarify": t2_after["status"],
        "passed": t2_before["status"] == "PLANNING" and len(plans2_before) == 0 and len(q2) > 0 and c2["ok"] and t2_after["status"] == "COMPLETED",
    }
    terminate_if_needed(tid2)

    # 3. Missing destination
    r3 = raw_post(op, "/tasks", {
        "taskFamily": "SPECIAL_PASSENGER_SERVICE",
        "taskGoal": "请为虚构轮椅陪同旅客在T2值机区安排会合陪同。",
        "sceneParams": {"assistanceType": "轮椅陪同", "origin": "T2值机区"},
    })
    tid3 = get_tid(r3)
    t3_before = wait_task_settled(tid3, timeout=45)
    plans3_before = op(f"/tasks/{tid3}/plan-versions")
    q3 = t3_before.get("missingInfoQuestions") or []
    c3 = clarify_all(tid3, q3, "GATE_A05") if q3 else {"ok": False, "error": "no questions"}
    t3_after = wait_task_terminal(tid3, timeout=120)
    results["missing_destination"] = {
        "taskId": tid3,
        "statusBeforeClarify": t3_before["status"],
        "questions": q3,
        "planCountBeforeClarify": len(plans3_before),
        "clarifyOk": c3["ok"],
        "statusAfterClarify": t3_after["status"],
        "passed": t3_before["status"] == "PLANNING" and len(plans3_before) == 0 and len(q3) > 0 and c3["ok"] and t3_after["status"] == "COMPLETED",
    }
    terminate_if_needed(tid3)

    # 4. No mobile robots vs normal escort
    try:
        set_disabled(AGENTS["ROBOT"], True)
        time.sleep(1)
        r4 = raw_post(op, "/tasks", {
            "taskFamily": "SPECIAL_PASSENGER_SERVICE",
            "taskGoal": "请为虚构轮椅旅客在T2值机区通过智慧航显显示会合提示、通知现场人员，并安排服务机器人前往会合后陪同旅客前往GATE_A05。",
            "sceneParams": {"assistanceType": "轮椅陪同", "origin": "T2值机区", "destination": "GATE_A05"},
        })
        tid4 = get_tid(r4)
        t4 = wait_task_terminal(tid4, timeout=90)
        steps4 = op(f"/tasks/{tid4}/step-assignments")
        events4 = op(f"/tasks/{tid4}/events")
        display_done = any(s.get("capabilityType") == "CAP_INFO_DISPLAY" and s.get("assignmentStatus") == "COMPLETED" for s in steps4)
        escort_done = any(s.get("capabilityType") == "CAP_ESCORT" and s.get("assignmentStatus") == "COMPLETED" for s in steps4)
        results["no_mobile_robot_downgrade"] = {
            "taskId": tid4,
            "finalStatus": t4["status"],
            "displayDone": display_done,
            "escortDone": escort_done,
            "eventReasonCodes": [e.get("reasonCode") for e in events4],
            "passed": t4["status"] != "COMPLETED" and display_done and not escort_done,
        }
        terminate_if_needed(tid4)
    finally:
        set_disabled(AGENTS["ROBOT"], False)
        time.sleep(2)

    return results


def run_ac_021():
    results = {"structured_valid": {}, "structured_invalid": {}, "nl_valid": {}, "nl_missing_conditional": {}}

    # Structured valid 4 types via /tasks/flight-change-event
    structured_cases = {
        "DELAY": {
            "flightNumber": "CA1234", "changeType": "DELAY",
            "originalTime": "2026-11-16T22:30:00", "newTime": "2026-11-16T23:00:00",
            "newGate": "GATE_A05", "changeDescription": "虚构航班CA1234延误30分钟至23:00，登机口GATE_A05"
        },
        "EARLY": {
            "flightNumber": "MU5678", "changeType": "EARLY",
            "originalTime": "2026-11-16T20:00:00", "newTime": "2026-11-16T19:30:00",
            "newGate": "GATE_A05", "changeDescription": "虚构航班MU5678提前30分钟至19:30，登机口GATE_A05"
        },
        "GATE_CHANGE": {
            "flightNumber": "CZ3311", "changeType": "GATE_CHANGE",
            "originalTime": "2026-11-16T21:00:00",
            "newGate": "GATE_A05", "changeDescription": "虚构航班CZ3311登机口变更为GATE_A05"
        },
        "CANCEL": {
            "flightNumber": "HU7788", "changeType": "CANCEL",
            "originalTime": "2026-11-16T18:00:00",
            "changeDescription": "虚构航班HU7788因天气原因取消"
        },
    }
    for ctype, payload in structured_cases.items():
        res = raw_post(op, "/tasks/flight-change-event", payload)
        tid = get_tid(res) if res["ok"] and isinstance(res["data"], dict) else None
        t = wait_task_terminal(tid, timeout=90) if tid else None
        results["structured_valid"][ctype] = {
            "ok": res["ok"],
            "taskId": tid,
            "finalStatus": t["status"] if t else None,
            "passed": res["ok"] and t is not None and t["status"] == "COMPLETED",
        }
        terminate_if_needed(tid)

    # Structured invalid missing conditional / base required fields
    invalid_cases = {
        "DELAY_missing_newTime": {
            "flightNumber": "CA1234", "changeType": "DELAY",
            "originalTime": "2026-11-16T22:30:00", "changeDescription": "延误未填新时间"
        },
        "EARLY_missing_newTime": {
            "flightNumber": "MU5678", "changeType": "EARLY",
            "originalTime": "2026-11-16T20:00:00", "changeDescription": "提前未填新时间"
        },
        "GATE_CHANGE_missing_newGate": {
            "flightNumber": "CZ3311", "changeType": "GATE_CHANGE",
            "originalTime": "2026-11-16T21:00:00", "changeDescription": "登机口变更未填新登机口"
        },
        "missing_flightNumber": {
            "changeType": "CANCEL", "originalTime": "2026-11-16T18:00:00", "changeDescription": "缺航班号"
        },
    }
    for name, payload in invalid_cases.items():
        res = raw_post(op, "/tasks/flight-change-event", payload)
        results["structured_invalid"][name] = {
            "rejected": not res["ok"],
            "error": res.get("error"),
            "passed": not res["ok"],
        }

    # Natural language valid 4 types via /tasks (no sceneParams)
    nl_valid_cases = {
        "DELAY": "虚构航班CA1234原计划22:30，延误30分钟至23:00，请通过航延屏发布变更、智慧航显发布提示，并由机器人引导旅客前往GATE_A05。",
        "EARLY": "虚构航班MU5678原计划20:00，提前30分钟至19:30，请通过航延屏发布变更、智慧航显发布提示，并由机器人引导旅客前往GATE_A05。",
        "GATE_CHANGE": "虚构航班CZ3311原计划21:00，登机口变更为GATE_A05，请通过航延屏发布变更、智慧航显发布提示，并由机器人引导旅客前往GATE_A05。",
        "CANCEL": "虚构航班HU7788原计划18:00，现已取消，请通过航延屏发布变更、智慧航显发布提示，并由机器人通知旅客前往GATE_A05。",
    }
    for ctype, goal in nl_valid_cases.items():
        res = raw_post(op, "/tasks", {"taskFamily": "FLIGHT_CHANGE_RESPONSE", "taskGoal": goal})
        tid = get_tid(res) if res["ok"] else None
        t = wait_task_terminal(tid, timeout=90) if tid else None
        results["nl_valid"][ctype] = {
            "taskId": tid,
            "finalStatus": t["status"] if t else None,
            "passed": res["ok"] and t is not None and t["status"] == "COMPLETED",
        }
        terminate_if_needed(tid)

    # Natural language missing conditional required field + clarify
    nl_missing_cases = [
        ("DELAY_missing_newTime", "虚构航班CA1234原计划22:30，发生延误，登机口GATE_A05不变，请发布变更提示。", "23:00"),
        ("EARLY_missing_newTime", "虚构航班MU5678原计划20:00，航班提前起飞，登机口GATE_A05，请发布变更提示。", "19:30"),
        ("GATE_CHANGE_missing_newGate", "虚构航班CZ3311原计划21:00，发生登机口变更，请发布变更提示。", "GATE_A05"),
    ]
    for name, goal, answer in nl_missing_cases:
        res = raw_post(op, "/tasks", {"taskFamily": "FLIGHT_CHANGE_RESPONSE", "taskGoal": goal})
        tid = get_tid(res)
        t_before = wait_task_settled(tid, timeout=45)
        plans_before = op(f"/tasks/{tid}/plan-versions")
        q = t_before.get("missingInfoQuestions") or []
        c = clarify_all(tid, q, answer) if q else {"ok": False}
        t_after = wait_task_terminal(tid, timeout=90)
        results["nl_missing_conditional"][name] = {
            "taskId": tid,
            "statusBeforeClarify": t_before["status"],
            "questions": q,
            "planCountBeforeClarify": len(plans_before),
            "clarifyOk": c["ok"],
            "statusAfterClarify": t_after["status"],
            "passed": t_before["status"] == "PLANNING" and len(plans_before) == 0 and len(q) > 0 and c["ok"] and t_after["status"] == "COMPLETED",
        }
        terminate_if_needed(tid)

    return results


def run_ac_023():
    results = {}
    channel_groups = [
        ("FLIGHT_DELAY_BOARD_unavailable", AGENTS["FLIGHT"], "CAP_FLIGHT_UPDATE", ["CAP_INFO_DISPLAY", "CAP_NOTIFICATION"]),
        ("SMART_DISPLAY_unavailable", AGENTS["DISPLAY"], "CAP_INFO_DISPLAY", ["CAP_FLIGHT_UPDATE", "CAP_NOTIFICATION"]),
        ("MOBILE_ROBOT_unavailable", AGENTS["ROBOT"], "CAP_NOTIFICATION", ["CAP_FLIGHT_UPDATE", "CAP_INFO_DISPLAY"]),
    ]
    for name, disable_ids, disabled_cap, expected_available_caps in channel_groups:
        try:
            set_disabled(disable_ids, True)
            time.sleep(1)
            res = raw_post(op, "/tasks/flight-change-event", {
                "flightNumber": "CA1234", "changeType": "DELAY",
                "originalTime": "2026-11-16T22:30:00", "newTime": "2026-11-16T23:00:00",
                "newGate": "GATE_A05", "changeDescription": f"虚构航班CA1234延误30分钟至23:00（{name}）"
            })
            tid = get_tid(res)
            t = wait_task_terminal(tid, timeout=90)
            steps = op(f"/tasks/{tid}/step-assignments")
            events = op(f"/tasks/{tid}/events")
            completed_caps = sorted({s.get("capabilityType") for s in steps if s.get("assignmentStatus") == "COMPLETED"})
            disabled_cap_completed = disabled_cap in completed_caps
            available_executed = any(c in completed_caps for c in expected_available_caps)
            results[name] = {
                "taskId": tid,
                "finalStatus": t["status"],
                "completedCapabilities": completed_caps,
                "disabledCapabilityCompleted": disabled_cap_completed,
                "availableChannelExecuted": available_executed,
                "eventReasonCodes": [e.get("reasonCode") for e in events],
                "passed": t["status"] != "COMPLETED" and not disabled_cap_completed and available_executed,
            }
            terminate_if_needed(tid)
        finally:
            set_disabled(disable_ids, False)
            time.sleep(2)
    return results


def main():
    try:
        set_disabled(ALL_AGENTS, False)
        time.sleep(1)
        report = {
            "timestamp": le.stamp(),
            "AC-020": run_ac_020(),
            "AC-021": run_ac_021(),
            "AC-023": run_ac_023(),
        }
    finally:
        set_disabled(ALL_AGENTS, False)

    OUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Saved evidence to", OUT_PATH)
    for k in ("AC-020", "AC-021", "AC-023"):
        print("===", k, "===")
        print(json.dumps(report[k], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
