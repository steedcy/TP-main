"""TC-068.S1: isolate blank-constraint save and remove the disposable record."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("配置管理员")
name = "S3_TC068_EMPTY_CONSTRAINT"
assert not any(d["taskName"] == name for d in api("/task-definitions"))
payload = {"taskName": name, "goalTemplate": "虚构航显测试目标",
           "sceneParams": [{"name": "sampleLocation", "type": "String", "required": True,
                            "range": "虚构地点"}],
           "availableCapabilityTypes": ["CAP_INFO_DISPLAY"],
           "constraintDescription": "", "completionCondition": "航显成功"}
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "request": payload, "observations": {}}
created = None
try:
    try:
        created = api("/task-definitions", "POST", payload)
        ev["observations"]["created"] = created
    except RuntimeError as error:
        ev["observations"]["rejection"] = str(error)
finally:
    if created:
        api(f"/task-definitions/{created['id']}", "DELETE")
        ev["observations"]["removedFromList"] = not any(
            d["id"] == created["id"] for d in api("/task-definitions"))
(Path(__file__).parent / "evidence/TC-068-empty-constraint.json").write_text(
    json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"acceptedEmptyConstraint": bool(created),
                  "removed": ev["observations"].get("removedFromList")}, ensure_ascii=False))
