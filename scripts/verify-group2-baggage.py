"""Run both documented fictional baggage samples and preserve timestamped evidence."""
import importlib.util
import json
import pathlib
import time
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)
api = env.API("运行操作员")
scanners = [d for d in env.load(env.FIXTURES / "devices.json") if d["simulatedDeviceType"] == "BAGGAGE_SCANNER"]
tokens = env.secrets()

def sample(name):
    return [env.request(d["accessEndpoint"] + "/device-api/v1/control/baggage-sample",
                        "POST", {"sample": name}, token=tokens[d["deviceCode"]]) for d in scanners]

def run(name, dimensions, weight):
    length, width, height = dimensions
    goal = (f"请为虚构旅客P-R08-{name}的行李R08-{name}在F2_BAGGAGE_POINT测量，尺寸为{length}×{width}×{height}厘米、"
            f"重量{weight}千克。按附录F阈值：长宽高之和超过158厘米或重量超过32千克即为超规；"
            "超规时上报事件，在智慧航显提示并由机器人引导至唯一目的地F2_TEST_GATE。全部是虚构测试对象。")
    scene = {"baggageId": f"R08-{name}", "baggageLocation": "F2_BAGGAGE_POINT",
             "length": length, "width": width, "height": height, "weight": weight,
             "targetLocation": "F2_TEST_GATE",
             "routePreference": "BARRIER_FREE", "measureMode": "AUTO", "timeout": 30,
             "alertLevel": "WARNING", "contentType": "TEXT", "displayDuration": 60,
             "contentData": "虚构超规行李请前往F2_TEST_GATE办理"}
    task = api("/tasks", "POST", {"taskGoal": goal, "taskFamily": "OVERSIZE_BAGGAGE_HANDLING", "sceneParams": scene})
    task_id = task["id"]
    rounds = 0
    deadline = time.monotonic() + 150
    while time.monotonic() < deadline:
        questions = task.get("missingInfoQuestions") or []
        if task["status"] == "PLANNING" and questions and rounds < 3:
            answer = (f"虚构旅客P-R08-{name}与行李R08-{name}均位于F2_BAGGAGE_POINT；尺寸{length}×{width}×{height}厘米、"
                      f"重量{weight}千克。按附录F，长宽高之和超过158厘米或重量超过32千克为超规；"
                      "自动测量无需人工复核，唯一目的地F2_TEST_GATE。")
            task = api(f"/tasks/{task_id}/clarify", "POST", {"answers": {q: answer for q in questions}})
            rounds += 1
            continue
        if task["status"] in {"COMPLETED", "FAILED", "PENDING_MANUAL", "MANUAL_TERMINATED"}:
            break
        time.sleep(2)
        task = api(f"/tasks/{task_id}")
    plans = api(f"/tasks/{task_id}/plan-versions")
    assignments = api(f"/tasks/{task_id}/step-assignments")
    current_steps = next((p["planSteps"] for p in plans if p["id"] == task.get("currentPlanVersionId")), [])
    actions = [{"capability": next((s["capabilityType"] for s in current_steps if s["stepSeq"] == a["stepSeq"]), None),
                "deviceAgentCode": a.get("deviceAgentCode"), "status": a["stepStatus"],
                "output": a.get("outputParams")} for a in assignments]
    return {"task": task, "plans": plans, "assignments": assignments, "actions": actions,
            "events": api(f"/tasks/{task_id}/events")}

results = []
samples = (("NORMAL", (55, 40, 20), 10), ("OVERSIZE", (80, 55, 35), 35))
if "--oversize-only" in sys.argv:
    samples = samples[1:]
try:
    for name, dimensions, weight in samples:
        fixture = sample(name)
        result = run(name, dimensions, weight)
        result["sample"] = fixture
        results.append(result)
finally:
    sample("OVERSIZE")

destination = env.EVIDENCE / ("20261024-group2-baggage-" + time.strftime("%H%M%S") + ".json")
env.save(destination, {"recordedAt": env.stamp(), "case": "GROUP2_BAGGAGE_BOTH_BRANCHES", "results": results})
for result, expected in zip(results, (False, True) if len(samples) == 2 else (True,)):
    task = result["task"]
    measure = next((a for a in result["actions"] if a["capability"] == "CAP_BAGGAGE_MEASURE"), None)
    assert task["status"] == "COMPLETED", f"task {task['id']} ended {task['status']}"
    assert measure and measure["status"] == "COMPLETED", "measurement missing"
    output = measure["output"]
    assert output["isOversize"] is expected
    assert output["dimensionThresholdCm"] == 158 and output["weightThresholdKg"] == 32
    assert "附录F" in output["thresholdSource"]
    if not expected:
        assert not any(a["capability"] == "CAP_OVERSIZE_ALERT" and a["status"] == "COMPLETED" for a in result["actions"]), "normal baggage caused an alert"
        assert any(a["status"] == "SKIPPED" for a in result["actions"]), "normal branch did not skip remaining actions"
    else:
        assert any(a["capability"] == "CAP_OVERSIZE_ALERT" and a["status"] == "COMPLETED" for a in result["actions"]), "oversize alert missing"
        assert any(a["capability"] == "CAP_INFO_DISPLAY" and a["status"] == "COMPLETED" for a in result["actions"]), "display missing"
print(json.dumps({"taskIds": [r["task"]["id"] for r in results], "statuses": [r["task"]["status"] for r in results], "evidence": str(destination)}, ensure_ascii=False))
