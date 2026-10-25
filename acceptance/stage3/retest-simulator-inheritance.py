"""TC-017.S3: compare six live simulator profiles with type inheritance rule."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("配置管理员")
matrix = {row["deviceTypeCode"]: {key for key, value in row.items() if key.startswith("CAP_") and value}
          for row in api("/device-types/capability-matrix")}
samples = []
for device in api("/devices?page=1&size=100")["content"]:
    if not device["isSimulator"]:
        continue
    actual = {row["capabilityType"] for row in api("/devices/" + device["deviceCode"] + "/capabilities")}
    expected = matrix["SIMULATOR"] | matrix[device["simulatedDeviceType"]]
    samples.append({"deviceCode": device["deviceCode"], "simulatedDeviceType": device["simulatedDeviceType"],
                    "actualCapabilityTypes": sorted(actual), "missingInheritedCapabilityTypes": sorted(expected - actual),
                    "unexpectedCapabilityTypes": sorted(actual - expected)})
evidence = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
            "sampleCount": len(samples), "samples": samples}
out = Path(__file__).resolve().parent / "evidence/TC-017-simulator-inheritance.json"
out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"sampleCount": len(samples), "missingSimulatorStatusCount": sum(
    "CAP_SIM_STATUS" in row["missingInheritedCapabilityTypes"] for row in samples)}, ensure_ascii=False))
