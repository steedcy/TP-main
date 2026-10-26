"""TC-084.S2: re-read task 19 trace, retained versions and privacy markers."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
operator = local.API("运行操作员")
task = operator("/tasks/19")
events = operator("/tasks/19/events")
versions = operator("/tasks/19/plan-versions")
snapshots = operator("/tasks/19/context-snapshots")
raw = json.dumps({"task": task, "events": events, "versions": versions,
                  "snapshots": snapshots}, ensure_ascii=False, default=str)
known_credentials = [local.account(role)[1] for role in
                     ("系统管理员", "配置管理员", "运行操作员")]
known_credentials += list(local.secrets().values())
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "taskId": 19,
      "task": {key: task.get(key) for key in
               ("id", "taskCode", "status", "createdAt", "updatedAt")},
      "events": [{key: event.get(key) for key in
                  ("id", "eventType", "occurredAt", "trigger", "reasonCode", "detailSummary")}
                 for event in events],
      "versions": [{key: version.get(key) for key in
                    ("id", "versionNo", "source", "frozenAt")}
                   | {"stepCount": len(version.get("planSteps") or [])}
                   for version in versions],
      "snapshots": [{key: snap.get(key) for key in
                     ("id", "snapshotCode", "generatedAt")}
                    for snap in snapshots],
      "knownCredentialRawAbsent": all(secret not in raw for secret in known_credentials if secret),
      "sensitiveKeyNamesAbsent": not any(key in raw for key in
                                        ('passwordHash', 'deviceToken', 'accessToken', 'secretKey'))}
out = stage / "evidence/TC-084-S2-trace-content-api-task19.json"
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"events": len(events), "missingReasonCode": sum(not e.get("reasonCode") for e in events),
                  "versions": len(versions), "snapshots": len(snapshots),
                  "knownCredentialRawAbsent": ev["knownCredentialRawAbsent"],
                  "sensitiveKeyNamesAbsent": ev["sensitiveKeyNamesAbsent"]}, ensure_ascii=False))
