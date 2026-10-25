"""Run the authorized F2 reset against the explicitly isolated local runtime."""
import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)
OUT = ROOT / "acceptance/stage2/evidence"
OUT.mkdir(parents=True, exist_ok=True)


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


if "--post-only" not in sys.argv:
    api = env.API("系统管理员")
    preview = api("/demo-data/reset-preview")
    assert preview["enabled"] is True
    assert not preview["blockingTasks"] and not preview["busyDemoAgents"]
    save("reset-preview.json", {"recordedAt": env.stamp(), **preview})
    result = api("/demo-data/reset", "POST", {"confirmationPhrase": preview["confirmationPhrase"], "confirmed": True})
    save("reset-result.json", {"recordedAt": env.stamp(), **result})
    assert result["result"] == "SUCCESS"
else:
    result = json.loads((OUT / "reset-result.json").read_text(encoding="utf-8"))
api = env.API("配置管理员")
devices = api("/devices?page=1&size=100")["content"]
templates = api("/baseline-templates")
f2 = [d for d in devices if d["deviceCode"].startswith("SIM_F2_")]
assert len(f2) == 6 and all(d["connectionTestStatus"] == "UNTESTED" for d in f2)
assert sum(t["templateStatus"] == "DRAFT" for t in templates if t["isPreset"]) == 3
save("post-reset-state.json", {"recordedAt": env.stamp(), "devices": f2,
                               "templates": [t for t in templates if t["isPreset"]]})
print(json.dumps({"result": result["result"], "sourceDigest": result["sourceDigest"],
                  "contentDigest": result["contentDigest"], "devices": len(f2),
                  "connectionStatus": "UNTESTED", "presetTemplates": "DRAFT"}, ensure_ascii=False))
