"""Check three core scenario families in saved seed fixtures and V1.5 runtime."""
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("配置管理员")
fixture = root / "scripts/test-fixtures/baselines.json"
raw = fixture.read_bytes()
seed = json.loads(raw)
definitions = api("/task-definitions")
templates = api("/baseline-templates")
agents = api("/device-agents?page=1&size=100")["content"]
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "seedFixture": str(fixture.relative_to(root)),
      "seedFixtureSha256": hashlib.sha256(raw).hexdigest(),
      "seedFamilies": [row["taskFamily"] for row in seed],
      "presetDefinitions": [{key: row.get(key) for key in
                             ("id", "definitionCode", "taskName", "isPreset", "definitionStatus",
                              "availableCapabilityTypes")}
                            for row in definitions if row["isPreset"]],
      "presetTemplates": [{key: row.get(key) for key in
                           ("id", "templateName", "templateIntent", "isPreset",
                            "templateStatus", "templateVersion")}
                          | {"stepCount": len(row["steps"])}
                          for row in templates if row["isPreset"]],
      "simulatorAgents": [{key: row.get(key) for key in
                           ("deviceCode", "agentStatus", "onlineStatus", "workStatus")}
                          for row in agents if row["deviceCode"].startswith("SIM_F2_")]}
out = stage / "evidence" / ("SRS_F002A-standard-dataset-coverage-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "seedFamilies": ev["seedFamilies"],
                  "definitionCodes": [r["definitionCode"] for r in ev["presetDefinitions"]],
                  "templateCount": len(ev["presetTemplates"]),
                  "simulatorAgentCount": len(ev["simulatorAgents"])}, ensure_ascii=False))
