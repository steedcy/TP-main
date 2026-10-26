"""Restore the Stage 3 V1.5 services against the isolated schema only."""
import hashlib
import importlib.util
import json
import shutil
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def healthy(url):
    try:
        return local.request(url, timeout=2)
    except Exception:
        return None

jar = root / "backend/target/airport-ai-app-1.0.0.jar"
runtime = root / ".local-test/runtime/backend.jar"
assert jar.is_file() and runtime.is_file()
assert sha(jar) == sha(runtime), "runtime JAR differs from built V1.5 input"
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "jarSha256": sha(jar), "services": {}}
environment = local.env()
database = environment.get("DB_NAME", "airport_ai")
environment.update(
    SPRING_DATASOURCE_URL="jdbc:postgresql://localhost:5432/" + database + "?currentSchema=tip_stage2_v14",
    SPRING_FLYWAY_SCHEMAS="tip_stage2_v14",
    SPRING_FLYWAY_DEFAULT_SCHEMA="tip_stage2_v14",
    DEMO_RESET_ENABLED="true",
    PLANNING_MODEL_PROVIDER="moonshot",
)
if not healthy("http://127.0.0.1:8080/actuator/health"):
    local.launch("backend", [shutil.which("java"), "-Xms128m", "-Xmx384m",
                             "-XX:+UseSerialGC", "-jar", str(runtime)], environment)
    ev["services"]["backendLaunched"] = True
ev["services"]["backendHealth"] = local.wait_health("http://127.0.0.1:8080/actuator/health")
assert ev["services"]["backendHealth"]["status"] == "UP"
def frontend_ok():
    try:
        with urllib.request.urlopen("http://127.0.0.1:5173/", timeout=2) as response:
            return response.status == 200
    except Exception:
        return False

if not frontend_ok():
    node = shutil.which("node") or str(Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe")
    local.launch("frontend", [node, str(root / "frontend/node_modules/vite/bin/vite.js"),
                              str(root / "frontend"), "--host", "127.0.0.1", "--port", "5173", "--strictPort"],
                 environment)
    ev["services"]["frontendLaunched"] = True
deadline = time.monotonic() + 30
while time.monotonic() < deadline and not frontend_ok():
    time.sleep(1)
assert frontend_ok()
ev["services"]["frontendStatus"] = 200
fixture = local.load(local.FIXTURES / "devices.json")
fixture_codes = {d["deviceCode"] for d in fixture}
api = local.API("配置管理员")
agents = {a["deviceCode"]: a["agentId"] for a in api("/device-agents?page=1&size=100")["content"]}
values = local.secrets()
for device in fixture:
    code = device["deviceCode"]
    assert code in agents and code in values
    local.start_simulator(device, values[code], agents[code])
    ev["services"][code] = "healthy"
for device in fixture:
    code = device["deviceCode"]
    endpoint = device["accessEndpoint"] + "/device-api/v1"
    local.request(endpoint + "/agents/" + agents[code] + "/binding", "POST", {
        "deviceCode": code, "agentCode": agents[code],
        "reportUrl": "http://127.0.0.1:8080/device-api/v1/agents/" + agents[code] + "/report",
        "heartbeatIntervalSeconds": 5, "heartbeatTimeoutSeconds": 30}, values[code])
    local.request(endpoint + "/control/online?value=true", "POST", token=values[code])
    local.request(endpoint + "/control/heartbeat?value=true", "POST", token=values[code])
deadline = time.monotonic() + 25
while time.monotonic() < deadline:
    online = [a for a in api("/device-agents?page=1&size=100")["content"]
              if a["deviceCode"] in fixture_codes]
    if len(online) == 6 and all(a["agentStatus"] == "ENABLED" and
        a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE" and
        a["currentTaskId"] is None for a in online):
        break
    time.sleep(1)
ev["sixOnlineIdle"] = len(online) == 6 and all(a["agentStatus"] == "ENABLED" and
    a["onlineStatus"] == "ONLINE" and a["workStatus"] == "IDLE" and
    a["currentTaskId"] is None for a in online)
assert ev["sixOnlineIdle"]
out = stage / "evidence" / ("stage3-services-recovered-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "sixOnlineIdle": ev["sixOnlineIdle"],
                  "jarSha256": ev["jarSha256"]}, ensure_ascii=False))
