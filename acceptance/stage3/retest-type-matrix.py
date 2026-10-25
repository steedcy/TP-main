"""TC-017: compare live 5x8 capability matrix against the frozen step text."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("配置管理员")
types = api("/device-types")
matrix = api("/device-types/capability-matrix")
expected = {
    "SMART_DISPLAY": {"CAP_INFO_DISPLAY", "CAP_FLIGHT_UPDATE", "CAP_NAVIGATION"},
    "BAGGAGE_SCANNER": {"CAP_BAGGAGE_MEASURE", "CAP_OVERSIZE_ALERT"},
    "FLIGHT_DELAY_BOARD": {"CAP_INFO_DISPLAY", "CAP_FLIGHT_UPDATE"},
    "MOBILE_ROBOT": {"CAP_INFO_DISPLAY", "CAP_NAVIGATION", "CAP_ESCORT", "CAP_NOTIFICATION"},
    "SIMULATOR": {"CAP_SIM_STATUS"},
}
observed = {row["deviceTypeCode"]: {key for key, value in row.items() if key.startswith("CAP_") and value}
            for row in matrix}
detail_counts = {}
for row in types:
    code = row["deviceTypeCode"]
    detail = api("/device-types/" + code + "/capability-boundary")
    detail_counts[code] = {"supportedCapabilityCount": len(detail["supportedCapabilityTypes"]),
                           "templateCount": detail["templateCount"],
                           "templateRowsMatch": detail["templateCount"] == len(detail["templates"]),
                           "instanceCount": detail["instanceCount"]}
ev = {
    "observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
    "typeCodes": [row["deviceTypeCode"] for row in types],
    "capabilityColumnCount": len([key for key in matrix[0] if key.startswith("CAP_")]),
    "matrixMatchesFrozenExpected": observed == expected,
    "typeListHasCounts": any("instanceCount" in row or "templateCount" in row or "supportedCapabilityCount" in row for row in types),
    "detailCounts": detail_counts,
}
out = Path(__file__).resolve().parent / "evidence/TC-017-type-matrix-api.json"
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(ev, ensure_ascii=False))
