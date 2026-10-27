"""Fresh V1.5 matrix-to-live-instance check for simulator inheritance rules."""
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
matrix_rows = api("/device-types/capability-matrix")
matrix = {row["deviceTypeCode"]: sorted(key for key, value in row.items()
          if key.startswith("CAP_") and value) for row in matrix_rows}
assert "SIMULATOR" in matrix and "CAP_SIM_STATUS" in matrix["SIMULATOR"]
devices = [x for x in api("/devices?page=1&size=100")["content"]
           if x["deviceCode"].startswith("SIM_F2_")]
assert len(devices) == 6
samples = []
for device in devices:
    code = device["deviceCode"]
    detail = api("/devices/" + code)
    agent = next(x for x in api("/device-agents?page=1&size=100")["content"]
                 if x["deviceCode"] == code)
    actual = sorted({x["capabilityType"] for x in api("/devices/" + code + "/capabilities")
                     if x["capabilityStatus"] == "ENABLED"})
    expected = sorted(set(matrix["SIMULATOR"]) | set(matrix[detail["simulatedDeviceType"]]))
    samples.append({"deviceCode": code, "deviceTypeCode": detail["deviceTypeCode"],
                    "simulatedDeviceType": detail["simulatedDeviceType"],
                    "agentStatus": agent["agentStatus"], "onlineStatus": agent["onlineStatus"],
                    "actualEnabledTypes": actual, "expectedInheritedTypes": expected,
                    "missingTypes": sorted(set(expected) - set(actual)),
                    "outOfBoundaryTypes": sorted(set(actual) - set(expected))})
out = stage / "evidence" / ("TC-017-simulator-profile-followup-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "matrix": matrix, "samples": samples}
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": out.name, "sampleCount": len(samples),
                  "allMissingSimStatus": all("CAP_SIM_STATUS" in x["missingTypes"] for x in samples),
                  "allBusinessWithinBoundary": all(not x["outOfBoundaryTypes"] for x in samples)},
                 ensure_ascii=False))
