"""TC-009.S3: change an isolated simulator endpoint, then restore it safely."""
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
code = "SIM_F2_DISPLAY"
original = api("/devices/" + code)
assert original["connectionTestStatus"] == "PASSED" and original["deviceStatus"] == "ACTIVE"


def edit_payload(endpoint):
    return {"deviceName": original["deviceName"], "areaCode": original["areaCode"],
            "positionX": original["positionX"], "positionY": original["positionY"],
            "accessEndpoint": endpoint, "accessCredentialRef": "",
            "statusReportInterval": original["statusReportInterval"], "remark": original["remark"]}


def status_request(path, body):
    request = urllib.request.Request(local.BASE + path,
        data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + api.token})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


evidence = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
            "isolatedSchema": "tip_stage2_v14", "deviceCode": code,
            "beforeConnectionStatus": original["connectionTestStatus"]}
try:
    api("/devices/" + code, "PUT", edit_payload("http://127.0.0.1:8199"))
    changed = api("/devices/" + code)
    evidence["afterEndpointChangeStatus"] = changed["connectionTestStatus"]
    evidence["credentialMaskedAfterEdit"] = changed["accessCredentialRefMasked"] == original["accessCredentialRefMasked"]
    evidence["agentCreateWhileUntestedHttpStatus"] = status_request("/device-agents", {"deviceCode": code})
    evidence["failedTestResult"] = api("/devices/" + code + "/connection-test", "POST")["result"]
finally:
    api("/devices/" + code, "PUT", edit_payload(original["accessEndpoint"]))
    restored = api("/devices/" + code)
    evidence["afterRestoreBeforeTestStatus"] = restored["connectionTestStatus"]
    evidence["restoredEndpointMatches"] = restored["accessEndpoint"] == original["accessEndpoint"]
    evidence["retestResult"] = api("/devices/" + code + "/connection-test", "POST")["result"]
    final = api("/devices/" + code)
    evidence["finalConnectionStatus"] = final["connectionTestStatus"]
    evidence["finalCredentialMasked"] = final["accessCredentialRefMasked"] == original["accessCredentialRefMasked"]

out = Path(__file__).resolve().parent / "evidence/TC-009-connection-reset.json"
out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(evidence, ensure_ascii=False))
