"""TC-008.S3: reject the 21st valid access object in the isolated schema."""
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
api = local.API("配置管理员")
before = api("/devices?page=1&size=100")
assert 0 < before["totalElements"] < 20
assert not any(row["deviceCode"].startswith("S3_LIMIT_") for row in before["content"])
sample = next(row for row in before["content"] if row["deviceTypeCode"] == "SIMULATOR")
payload = {
    "deviceCode": "S3_LIMIT_21", "deviceName": "阶段三接入对象上限验证",
    "deviceTypeCode": "SIMULATOR", "isSimulator": True,
    "simulatedDeviceType": sample["simulatedDeviceType"],
    "areaCode": sample["areaCode"], "positionX": 1, "positionY": 1,
    "accessEndpoint": "http://127.0.0.1:8199", "accessCredentialRef": "S3_LIMIT_FIXTURE",
    "statusReportInterval": 15, "remark": "阶段三上限测试",
}
created = []
status = None
body = {}
at_limit = None
try:
    for index in range(before["totalElements"] + 1, 21):
        candidate = dict(payload, deviceCode=f"S3_LIMIT_{index:02d}",
                         deviceName=f"阶段三临时上限对象{index:02d}")
        api("/devices", "POST", candidate)
        created.append(candidate["deviceCode"])
    at_limit = api("/devices?page=1&size=100")
    assert at_limit["totalElements"] == 20
    request = urllib.request.Request(local.BASE + "/devices",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + api.token})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status = response.status
            body = json.loads(response.read())
    except urllib.error.HTTPError as error:
        status = error.code
        body = json.loads(error.read())
    after = api("/devices?page=1&size=100")
finally:
    cleanup_errors = []
    for code in reversed(created):
        try:
            api("/devices/" + code, "DELETE")
        except Exception:
            cleanup_errors.append(code)
post_cleanup = api("/devices?page=1&size=100")
evidence = {
    "observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
    "isolatedSchema": "tip_stage2_v14", "beforeCount": before["totalElements"],
    "temporaryCreated": len(created), "atLimitCount": at_limit["totalElements"],
    "httpStatus": status, "responseCode": body.get("code"),
    "responseMessage": body.get("message"), "afterCount": after["totalElements"],
    "newCodePresentAfter": any(row["deviceCode"] == payload["deviceCode"] for row in after["content"]),
    "postCleanupCount": post_cleanup["totalElements"], "cleanupErrors": cleanup_errors,
}
out = Path(__file__).resolve().parent / "evidence/TC-008-limit.json"
out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(evidence, ensure_ascii=False))
