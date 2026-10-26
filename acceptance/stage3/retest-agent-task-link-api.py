"""TC-011.S2: verify the linked dry-run task exists and role access is asymmetric."""
import importlib.util
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
task_id = 57
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "taskId": task_id, "roleResults": {}}
for role in ("配置管理员", "运行操作员"):
    api = local.API(role)
    request = urllib.request.Request(local.BASE + f"/tasks/{task_id}",
        headers={"Authorization": "Bearer " + api.token})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            data = json.loads(response.read()).get("data", {})
            ev["roleResults"][role] = {"httpStatus": response.status,
                "returnedId": data.get("id"), "isDryRun": data.get("isDryRun"),
                "status": data.get("status")}
    except urllib.error.HTTPError as error:
        ev["roleResults"][role] = {"httpStatus": error.code}
out = Path(__file__).parent / "evidence/TC-011-task-link-api.json"
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(ev["roleResults"], ensure_ascii=False))
