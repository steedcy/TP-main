"""Read persisted audit trail for the original Stage3 lockout sequence."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
prior = json.loads((stage / "evidence/TC-002-lockout.json").read_text(encoding="utf-8"))
account = prior["accounts"]["A"]
assert account.startswith("s3a") and account.isalnum()
spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db)
sql = ("SELECT id,username,operation_type,coalesce(operation_target,''),"
       "operation_result,coalesce(source_ip,''),created_at,coalesce(detail::text,'') "
       "FROM tip_stage2_v14.operation_logs "
       "WHERE username='" + account + "' OR operation_target='" + account + "' "
       "ORDER BY id")
rows = []
for line in db.query(db.source, sql).splitlines():
    cells = line.split("|", 7)
    assert len(cells) == 8
    rows.append(dict(zip(("id", "username", "operationType", "operationTarget",
                          "result", "sourceIp", "createdAt", "detail"), cells)))
out = stage / "evidence" / ("TC-002-lockout-audit-followup-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps({"observedAt": datetime.now(timezone.utc).isoformat(),
    "runtimeInput": "V1.5", "isolatedSchema": "tip_stage2_v14",
    "priorEvidence": "acceptance/stage3/evidence/TC-002-lockout.json",
    "account": account, "rows": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "operations": [
    (row["operationType"], row["operationTarget"], row["result"]) for row in rows]},
    ensure_ascii=False))
