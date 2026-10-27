"""TC-058.S2: exercise the live exception list and pending counter."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("运行操作员")
types = ["AGENT_OFFLINE", "CAPABILITY_GAP", "EXECUTION_TIMEOUT", "STEP_FAILED", "REPLAN_FAILED"]
statuses = ["PENDING", "PROCESSING", "RESOLVED", "IGNORED"]
evidence = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
            "isolatedSchema": "tip_stage2_v14", "all": api("/task-exceptions"),
            "types": {}, "statuses": {}, "pendingCount": api("/task-exceptions/pending-count")}
for kind in types:
    rows = api("/task-exceptions?exceptionType=" + kind)
    evidence["types"][kind] = {"rows": rows, "matching": all(r["exceptionType"] == kind for r in rows)}
for status in statuses:
    rows = api("/task-exceptions?exceptionStatus=" + status)
    evidence["statuses"][status] = {"rows": rows, "matching": all(r["exceptionStatus"] == status for r in rows)}
evidence["pendingCounterMatches"] = evidence["pendingCount"] == len(evidence["statuses"]["PENDING"]["rows"])
evidence["allFiltersMatch"] = all(x["matching"] for x in evidence["types"].values()) and all(
    x["matching"] for x in evidence["statuses"].values())
out = Path(__file__).parent / "evidence" / ("TC-058-exception-list-api-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": out.name, "allCount": len(evidence["all"]),
                  "typeCounts": {k: len(v["rows"]) for k, v in evidence["types"].items()},
                  "statusCounts": {k: len(v["rows"]) for k, v in evidence["statuses"].items()},
                  "pendingCounterMatches": evidence["pendingCounterMatches"],
                  "allFiltersMatch": evidence["allFiltersMatch"]}, ensure_ascii=False))
