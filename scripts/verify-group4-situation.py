"""Bounded API smoke for the situation snapshot; not the 20-report load case."""
import importlib.util
import json
import pathlib
import statistics
import time
from PIL import Image

spec = importlib.util.spec_from_file_location("localenv", pathlib.Path(__file__).with_name("local-test-environment.py"))
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)
operator = env.API("运行操作员")
config = env.API("配置管理员")
width, height = Image.open(env.ROOT / "frontend/public/F2.jpg").size
assert (width, height) == (1260, 6895)
measurements = []
for _ in range(25):
    started = time.perf_counter()
    snapshot = operator("/situation/snapshot")
    measurements.append(round((time.perf_counter() - started) * 1000, 2))
    assert snapshot["refreshIntervalSeconds"] == 5
admin_snapshot = config("/situation/snapshot")
assert len(snapshot["agents"]) == len(admin_snapshot["agents"])
assert len(snapshot["agents"]) >= 20
agents = snapshot["agents"]
f2 = [agent for agent in agents if agent["deviceCode"].startswith("SIM_F2_")]
assert len(f2) == 6
assert all(agent["capabilityTypes"] for agent in f2)
assert all(agent["location"]["x"] >= 0 and agent["location"]["x"] <= width
           and agent["location"]["y"] >= 0 and agent["location"]["y"] <= height for agent in f2)
record = {"recordedAt": env.stamp(), "scope": "SITUATION_API_SMOKE_NO_20_REPORT_LOAD",
          "imagePixels": [width, height], "objectCount": len(agents), "f2Agents": f2,
          "refreshIntervalSeconds": snapshot["refreshIntervalSeconds"],
          "requestDurationsMs": measurements, "medianMs": statistics.median(measurements),
          "p95Ms": sorted(measurements)[int(len(measurements) * .95) - 1]}
path = env.EVIDENCE / ("20261024-group4-situation-" + time.strftime("%H%M%S") + ".json")
env.save(path, record)
print(json.dumps({"objectCount": len(agents), "f2Count": len(f2), "medianMs": record["medianMs"],
                  "p95Ms": record["p95Ms"], "evidence": str(path)}, ensure_ascii=False))
