"""Correlate unresolved goals with actual commands after manual baseline actions."""
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("运行操作员")
raw_file = stage / "evidence/TC-064-manual-device-commands-20261027T012753Z.txt"
raw = raw_file.read_text(encoding="utf-8")
commands = {}
for line in raw.splitlines():
    parts = line.split("|", 5)
    assert len(parts) == 6
    task_id = int(parts[0])
    payload = json.loads(parts[3])
    commands.setdefault(task_id, []).append({
        "stepSeq": int(parts[1]), "capabilityType": parts[2],
        "commandType": payload["commandType"],
        "inputParams": payload["inputParams"], "commandStatus": parts[4]})
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "rawCommandFile": raw_file.name,
      "rawCommandSha256": hashlib.sha256(raw.encode()).hexdigest(), "tasks": {}}
for task_id in (69, 70, 71):
    task = api(f"/tasks/{task_id}")
    ev["tasks"][str(task_id)] = {
        "task": {key: task.get(key) for key in
                 ("id", "taskCode", "taskGoal", "sceneParams", "goalParsingResult",
                  "missingInfoQuestions", "status", "failureReason")},
        "commands": commands.get(task_id, [])}
out = stage / "evidence" / ("TC-064-manual-missing-info-override-" +
                             datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "tasks": {id: {
    "missing": len(row["task"]["missingInfoQuestions"] or []),
    "origin": row["task"]["goalParsingResult"].get("origin") if row["task"]["goalParsingResult"] else None,
    "destination": row["task"]["goalParsingResult"].get("destination") if row["task"]["goalParsingResult"] else None,
    "executedCapabilities": [c["capabilityType"] for c in row["commands"]
                             if c["commandType"] == "EXECUTE_CAPABILITY"]}
    for id, row in ev["tasks"].items()}}, ensure_ascii=False))
