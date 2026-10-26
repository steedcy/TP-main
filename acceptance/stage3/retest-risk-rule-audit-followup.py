"""TC-043.S1: collect the operation-log and cleanup checks after the UI runner decode error."""
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
code = "S3_TC043_RULE"
original = next((stage / "evidence").glob("TC-043-risk-rule-crud-20*.json"))
run = json.loads(original.read_text(encoding="utf-8"))
ui = json.loads((stage / "evidence/TC-043-risk-rule-ui.json").read_text(encoding="utf-8"))
assert run["browserExitCode"] == 0 and ui["ruleCode"] == code
assert run["cleanup"] == {"afterCount": run["beforeCount"], "temporaryCodesRemaining": []}
logs = api("/operation-logs?page=1&size=100")["content"]
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "originalEvidence": original.name, "browserEvidence": "TC-043-risk-rule-ui.json",
      "runnerDiagnostic": "UTF-8 browser stdout was decoded as GBK after the browser saved its evidence; the runner's finally block cleaned the temporary rules",
      "changeLogs": [row for row in logs if row["operationType"] == "RISK_RULE_CHANGE"
                     and row.get("operationTarget") == code],
      "remainingCodes": [row["ruleCode"] for row in api("/risk-rules")],
      "beforeCodes": run["beforeRuleCodes"]}
out = stage / "evidence" / (
    "TC-043-risk-rule-audit-followup-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "changeLogCount": len(ev["changeLogs"]),
                  "cleanupMatchesBaseline": ev["remainingCodes"] == ev["beforeCodes"]}, ensure_ascii=False))
