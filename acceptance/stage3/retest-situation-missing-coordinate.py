"""TC-071.S1: check whether the live model can represent a missing coordinate."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

local = module("local", root / "scripts/local-test-environment.py")
db = module("db", root / "acceptance/stage2/db-isolation.py")
api = local.API("配置管理员")
code = "SIM_F2_DISPLAY"
before = api("/devices/" + code)
assert before["positionX"] is not None and before["positionY"] is not None
snapshot_before = next(a for a in api("/situation/snapshot")["agents"] if a["deviceCode"] == code)
assert snapshot_before["location"]["x"] is not None
constraints = db.query(db.source,
    "SELECT column_name,is_nullable FROM information_schema.columns "
    "WHERE table_schema='tip_stage2_v14' AND table_name='devices' "
    "AND column_name IN ('position_x','position_y') ORDER BY column_name").splitlines()
assert constraints == ["position_x|NO", "position_y|NO"]
payload = {key: before[key] for key in ("deviceName", "areaCode", "positionX", "positionY",
    "accessEndpoint", "statusReportInterval", "remark")}
payload["accessCredentialRef"] = ""
attempts = []
for key in ("positionX", "positionY"):
    attempted = dict(payload)
    attempted[key] = None
    try:
        result = api("/devices/" + code, "PUT", attempted)
        attempts.append({"missing": key, "accepted": True, "response": result})
    except Exception as error:
        attempts.append({"missing": key, "accepted": False, "error": str(error)})
after = api("/devices/" + code)
snapshot_after = next(a for a in api("/situation/snapshot")["agents"] if a["deviceCode"] == code)
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "deviceCode": code,
      "databaseCoordinateConstraints": constraints,
      "before": {"device": before, "marker": snapshot_before},
      "attempts": attempts, "after": {"device": after, "marker": snapshot_after}}
assert all(not a["accepted"] and "400" in a["error"] for a in attempts)
assert after["positionX"] == before["positionX"] and after["positionY"] == before["positionY"]
out = stage / "evidence" / ("TC-071-missing-coordinate-api-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "constraints": constraints,
                  "rejected": [not a["accepted"] for a in attempts]}, ensure_ascii=False))
