"""F028.R06: inspect all current audit details for credential masking."""
import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
response = local.API("系统管理员")("/operation-logs?page=1&size=2000")
rows = response["content"]
assert len(rows) == response["totalElements"]
full_text = json.dumps(rows, ensure_ascii=False, default=str)
secrets = [local.account(role)[1] for role in
           ("系统管理员", "配置管理员", "运行操作员")]
secrets += list(local.secrets().values())
secrets = [value for value in secrets if value and len(value) >= 8]
sensitive = re.compile(r"credential|token|password|secret|凭据|口令|密钥", re.I)
scanned = []
unparsed = []
for row in rows:
    detail = row.get("detail")
    if not detail:
        continue
    try:
        parsed = json.loads(detail)
    except (TypeError, ValueError):
        unparsed.append(row["id"])
        continue
    if not isinstance(parsed, dict):
        unparsed.append(row["id"])
        continue
    fields = {key: {"masked": "*" in str(value) or str(value).upper() == "[REDACTED]",
                    "valueLength": len(str(value))}
              for key, value in parsed.items() if sensitive.search(key)
              and key != "credentialChanged"}
    if fields:
        scanned.append({"id": row["id"], "operationType": row["operationType"],
                        "createdAt": row["createdAt"], "sensitiveFields": fields})
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "totalLogRows": len(rows),
      "rowsWithDetail": sum(bool(row.get("detail")) for row in rows),
      "unparsedDetailIds": unparsed, "sensitiveDetailRows": scanned,
      "knownCredentialSampleCount": len(secrets),
      "knownCredentialRawFound": any(value in full_text for value in secrets),
      "sensitiveKeyNamesOnTopLevel": sorted({key for row in rows for key in row if sensitive.search(key)})}
out = stage / "evidence" / ("SRS_F028-audit-masking-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "totalLogRows": ev["totalLogRows"],
                  "rowsWithDetail": ev["rowsWithDetail"],
                  "sensitiveDetailRows": len(scanned),
                  "unmaskedSensitiveFields": sum(not item["masked"] for row in scanned
                                                 for item in row["sensitiveFields"].values()),
                  "unparsedDetails": len(unparsed),
                  "knownCredentialRawFound": ev["knownCredentialRawFound"]}, ensure_ascii=False))
