"""Restore the exact preset JSON after the API normalized omitted defaultValue to null."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
db_spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(db_spec)
db_spec.loader.exec_module(db)
ev0 = json.loads((Path(__file__).parent / "evidence/TC-069-preset-definitions.json").read_text(encoding="utf-8"))
original = ev0["presetsBefore"][0]
assert original["definitionCode"] == "OVERSIZE_BAGGAGE_HANDLING" and original["isPreset"]
api = local.API("配置管理员")
before = api(f"/task-definitions/{original['id']}")
assert before["sceneParams"] == [{**original["sceneParams"][0], "defaultValue": None}]
raw = json.dumps(original["sceneParams"], ensure_ascii=True, separators=(",", ":"))
escaped = raw.replace("'", "''")
result = db.query(db.source, "UPDATE tip_stage2_v14.task_definitions SET scene_params='" + escaped +
                  "'::json WHERE id=" + str(original["id"]) + " AND definition_code='OVERSIZE_BAGGAGE_HANDLING'")
after = api(f"/task-definitions/{original['id']}")
keys = ["goalTemplate", "sceneParams", "availableCapabilityTypes", "constraintDescription",
        "completionCondition", "definitionStatus", "isPreset"]
same = all(after[k] == original[k] for k in keys)
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "definitionId": original["id"], "before": before, "dbUpdateResult": result,
      "after": after, "configurationMatchesOriginal": same}
(Path(__file__).parent / "evidence/TC-069-preset-exact-restore.json").write_text(
    json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
assert same
print(json.dumps({"definitionId": original["id"], "configurationMatchesOriginal": same}))
