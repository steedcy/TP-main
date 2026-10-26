"""Follow up the disposable 15-second simulator with its retained business state."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db)
run = json.loads((stage / "evidence/TC-014-status-cadence-20261026T073137Z.json").read_text(encoding="utf-8"))
agent = run["agentCode"]
assert agent.startswith("AGT-") and agent[4:].isalnum()
result = db.query(db.source, "SELECT json_build_object('businessStatus',business_status,"
    "'lastReportedAt',last_reported_at,'agentStatus',agent_status,'onlineStatus',online_status) "
    "FROM tip_stage2_v14.device_agents WHERE agent_code='" + agent + "'")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(),
      "isolatedSchema": "tip_stage2_v14", "agentCode": agent,
      "afterSoftDeleteDatabaseRow": json.loads(result)}
out = stage / "evidence/TC-014-status-cadence-db.json"
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(ev, ensure_ascii=False))
