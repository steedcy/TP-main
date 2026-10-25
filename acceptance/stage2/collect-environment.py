"""Capture current stage-2 runtime identity and readiness without secrets."""
import hashlib
import importlib.util
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


env = module("localenv", ROOT / "scripts/local-test-environment.py")
db = module("isodb", ROOT / "acceptance/stage2/db-isolation.py")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def version(path):
    command = "(Get-Item -LiteralPath '" + str(path) + "').VersionInfo.ProductVersion"
    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    return result.stdout.strip() if result.returncode == 0 else "UNAVAILABLE"


def git(*arguments):
    return subprocess.check_output(["git", *arguments], cwd=ROOT, text=True).strip()


settings = env.env()
chrome = pathlib.Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe"
edge = pathlib.Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
fixtures = env.load(env.FIXTURES / "devices.json")
api = env.API("配置管理员")
roles = []
for name in ("系统管理员", "配置管理员", "运行操作员"):
    session = env.API(name)
    roles.append({"role": session.role, "login": "PASS"})
devices = api("/devices?page=1&size=100")["content"]
agents = api("/device-agents?page=1&size=100")["content"]
templates = [t for t in api("/baseline-templates") if t["isPreset"]]
active = db.query(db.source, "SELECT count(*) FROM " + db.schema +
                  ".tasks WHERE status IN ('PLANNING','SUPERVISING','PENDING_ASSIGNMENT','DOWNGRADING','EXECUTING')")
processes = env.load(ROOT / ".local-test/processes.json")
model = {"provider": settings.get("PLANNING_MODEL_PROVIDER", "moonshot"),
         "service": "Moonshot/Kimi", "modelId": settings.get("MOONSHOT_MODEL") or "kimi-k2.6",
         "providerInternalRevision": "not exposed by configured API",
         "interface": (settings.get("MOONSHOT_BASE_URL") or "https://api.moonshot.cn/v1").rstrip("/") + "/chat/completions",
         "request": {"response_format": "json_object", "stream": False,
                     "max_tokens": int(settings.get("MOONSHOT_MAX_TOKENS") or 4096),
                     "thinking": "disabled for kimi-k2.6"},
         "timeoutMs": 60000, "connectTimeoutSeconds": 10,
         "apiKey": "SET (masked)" if settings.get("MOONSHOT_API_KEY") else "UNSET"}
out = {"recordedAt": env.stamp(), "gitHead": git("rev-parse", "HEAD"),
       "gitStatus": git("status", "--short", "--untracked-files=no").splitlines(),
       "runtime": {"backendPid": processes["backend"]["pid"],
                   "backendJarSha256": sha(ROOT / ".local-test/runtime/backend.jar"),
                   "backendBuildSha256": sha(ROOT / "backend/target/airport-ai-app-1.0.0.jar"),
                   "simulatorJarSha256": sha(ROOT / "simulator/target/device-simulator-runtime.jar"),
                   "simulatorPids": {d["deviceCode"]: processes[d["deviceCode"]]["pid"] for d in fixtures},
                   "frontendBuild": "npm run build passed"},
       "database": {"name": db.source, "isolatedSchema": db.schema, "flyway": db.inspect_schema()["flyway"],
                    "activeTaskCount": int(active), "allTaskStates": db.inspect_schema()["taskStates"]},
       "model": model,
       "browsers": {"Chrome": {"path": str(chrome), "version": version(chrome)},
                    "Edge": {"path": str(edge), "version": version(edge)}},
       "roles": roles,
       "demoSetup": {"maxObjects": 10, "activeObjects": len(devices),
                     "onlineEnabledAgents": sum(a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE" for a in agents),
                     "f2MapSha256": sha(ROOT / "F2.jpg"), "f2Coordinates":
                     [{k: d[k] for k in ("deviceCode", "simulatedDeviceType", "positionX", "positionY", "areaCode", "accessEndpoint")}
                      for d in fixtures],
                     "faultControls": ["online/offline", "heartbeat/silent", "scenario SUCCESS/FAILED/TIMEOUT/NO_OBJECT/LOST_TARGET", "delay"]},
       "presetBaselines": [{"id": t["id"], "taskFamily": t["templateIntent"],
                            "version": t["templateVersion"], "status": t["templateStatus"]} for t in templates]}
assert out["runtime"]["backendJarSha256"] == out["runtime"]["backendBuildSha256"]
assert len(out["database"]["flyway"]) == 16
assert active == "0" and len(devices) == 6 and out["demoSetup"]["onlineEnabledAgents"] == 6
assert len(templates) == 3 and all(t["status"] == "ENABLED" for t in out["presetBaselines"])
dest = ROOT / "acceptance/stage2/evidence/environment-snapshot.json"
dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"backendSha256": out["runtime"]["backendJarSha256"],
                  "simulatorSha256": out["runtime"]["simulatorJarSha256"],
                  "flyway": 16, "activeTasks": active, "devices": len(devices),
                  "templates": len(templates)}, ensure_ascii=False))
