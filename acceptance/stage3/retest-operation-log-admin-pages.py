"""TC-085.S2: enumerate both admin audit pages to confirm full access."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("系统管理员")
first = api("/operation-logs?page=1&size=1000")
second = api("/operation-logs?page=2&size=1000")
ids = [row["id"] for row in first["content"] + second["content"]]
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "pageSize": 1000,
      "first": {"totalElements": first["totalElements"], "returned": len(first["content"]),
                "minId": min(row["id"] for row in first["content"]),
                "maxId": max(row["id"] for row in first["content"])},
      "second": {"totalElements": second["totalElements"], "returned": len(second["content"]),
                 "minId": min(row["id"] for row in second["content"]),
                 "maxId": max(row["id"] for row in second["content"])},
      "allUniqueIds": len(ids) == len(set(ids)),
      "usernames": sorted({row["username"] for row in first["content"] + second["content"]})}
out = stage / "evidence" / ("TC-085-S2-admin-audit-pages-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "first": ev["first"], "second": ev["second"],
                  "allUniqueIds": ev["allUniqueIds"]}, ensure_ascii=False))
