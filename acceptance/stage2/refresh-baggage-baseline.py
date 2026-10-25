"""Apply the corrected four-channel F2 baggage fixture and prove its dry run."""
import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)
api = env.API("配置管理员")
family = sys.argv[1] if len(sys.argv) > 1 else "OVERSIZE_BAGGAGE_HANDLING"
fixture = next(f for f in env.load(env.FIXTURES / "baselines.json")
               if f["taskFamily"] == family)
template = next(t for t in api("/baseline-templates")
                if t["templateIntent"] == fixture["taskFamily"] and t["isPreset"])
updated = api("/baseline-templates/" + str(template["id"]), "PUT",
              {key: fixture[key] for key in ("inputParams", "steps")})
agents = {a["deviceCode"]: a["agentId"] for a in api("/device-agents?page=1&size=100")["content"]}
trial = env.run_baseline(api, updated, fixture, agents)
assert trial["result"] == "SUCCESS", trial
api("/baseline-templates/" + str(updated["id"]) + "/enable", "POST")
enabled = next(t for t in api("/baseline-templates") if t["id"] == updated["id"])
out = {"recordedAt": env.stamp(), "templateId": updated["id"],
       "version": enabled["templateVersion"], "status": enabled["templateStatus"],
       "capabilities": [s["capabilityType"] for s in fixture["steps"]], "trial": trial}
(ROOT / ("acceptance/stage2/evidence/" + family.lower() + "-baseline-refresh.json")).write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"result": trial["result"], "templateStatus": enabled["templateStatus"],
                  "version": enabled["templateVersion"], "taskId": trial["taskId"]}, ensure_ascii=False))
