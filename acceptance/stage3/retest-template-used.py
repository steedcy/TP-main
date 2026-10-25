"""TC-018.S3 / TC-019.S1-S2: isolated template use, retirement and cleanup."""
import importlib.util
import json
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
db_spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(db_spec)
db_spec.loader.exec_module(db)
api = local.API("配置管理员")
base = "/device-types/SMART_DISPLAY/capability-templates"
template_code = "S3_TC019_USED3"
devices = ["S3_TC019_DISPLAY_G", "S3_TC019_DISPLAY_H", "S3_TC019_DISPLAY_I"]
cap_code = "S3_TC019_INFO3"
evidence = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
            "isolatedSchema": "tip_stage2_v14", "templateCode": template_code,
            "deviceCodes": devices, "observations": {}, "cleanup": {}}
out = Path(__file__).resolve().parent / "evidence/TC-018-019-template-used-retry3.json"


def raw(path, method="GET", data=None):
    body = json.dumps(data, ensure_ascii=False).encode() if data is not None else None
    request = urllib.request.Request(local.BASE + path, data=body, method=method,
        headers={"Authorization": "Bearer " + api.token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def device_payload(code):
    return {"deviceCode": code, "deviceName": "阶段三临时航显 " + code[-1],
            "deviceTypeCode": "SMART_DISPLAY", "isSimulator": False, "areaCode": "F2",
            "positionX": 10, "positionY": 10, "accessEndpoint": "http://127.0.0.1:8997",
            "accessCredentialRef": "S3-TEST-UNUSED", "statusReportInterval": 15,
            "remark": "仅阶段三模板引用验证"}


def template_row():
    return next((r for r in api(base) if r["templateCode"] == template_code), None)


def existing_device(code):
    return db.query(db.source, "SELECT count(*) FROM tip_stage2_v14.devices WHERE device_code='" + code + "'")


def cleanup():
    # Only exact stage-3 fixture rows are touched in the isolated schema.
    for code in devices:
        if existing_device(code) == "1":
            try:
                api("/devices/" + code, "DELETE")
            except Exception as error:
                evidence["cleanup"][code + "ApiDeleteError"] = str(error)
    statement = ("BEGIN; "
        "DELETE FROM tip_stage2_v14.device_capabilities WHERE capability_code='S3_TC019_INFO3' "
        "AND device_id IN (SELECT id FROM tip_stage2_v14.devices WHERE device_code IN "
        "('S3_TC019_DISPLAY_G','S3_TC019_DISPLAY_H','S3_TC019_DISPLAY_I')); "
        "UPDATE tip_stage2_v14.capability_template SET usage_count=0 WHERE "
        "device_type_code='SMART_DISPLAY' AND template_code='S3_TC019_USED3' "
        "AND NOT EXISTS (SELECT 1 FROM tip_stage2_v14.device_capabilities "
        "WHERE template_id=tip_stage2_v14.capability_template.id); COMMIT;")
    db.query(db.source, statement)
    if template_row() is not None:
        try:
            api(base + "/" + template_code, "DELETE")
        except Exception as error:
            evidence["cleanup"]["templateApiDeleteError"] = str(error)
    evidence["cleanup"]["templateAbsent"] = template_row() is None
    evidence["cleanup"]["capabilityRows"] = db.query(db.source,
        "SELECT count(*) FROM tip_stage2_v14.device_capabilities "
        "WHERE capability_code='S3_TC019_INFO3'")
    evidence["cleanup"]["deviceStates"] = db.query(db.source,
        "SELECT device_code,device_status FROM tip_stage2_v14.devices WHERE device_code IN "
        "('S3_TC019_DISPLAY_G','S3_TC019_DISPLAY_H','S3_TC019_DISPLAY_I') ORDER BY device_code").splitlines()


assert template_row() is None
assert all(existing_device(code) == "0" for code in devices)
evidence["beforeTemplateCount"] = len(api(base))
try:
    payload = {"templateCode": template_code, "templateName": "阶段三已使用航显模板",
        "capabilityType": "CAP_INFO_DISPLAY", "templateDescription": "临时引用验证",
        "inputParams": [
            {"name": "contentType", "type": "String", "required": True, "defaultValue": "TEXT"},
            {"name": "contentData", "type": "String", "required": True, "defaultValue": "template-default"},
            {"name": "displayDuration", "type": "Number", "required": True, "defaultValue": "30"}],
        "outputParams": [{"name": "displayStatus", "type": "String", "required": True}]}
    created = api(base, "POST", payload)
    evidence["observations"]["createdVersion"] = created["templateVersion"]
    api("/devices", "POST", device_payload(devices[0]))
    evidence["observations"]["firstDeviceInitialCapabilities"] = len(api("/devices/" + devices[0] + "/capabilities"))

    node = root / "acceptance/stage3/retest-template-used-ui.cjs"
    runner = root / ".local-test/stage3-template-used-ui.json"
    runner.write_text(json.dumps({"first": devices[0], "third": devices[2], "template": template_code}), encoding="utf-8")
    node_bin = Path(r"C:\Users\savy\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe")
    import os
    environment = os.environ.copy()
    environment["PLAYWRIGHT_CORE_PATH"] = r"C:\Users\savy\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\playwright-core"
    browser = subprocess.run([str(node_bin), str(node), "first"], cwd=root, env=environment,
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
    evidence["observations"]["firstBrowserExit"] = browser.returncode
    if browser.returncode:
        evidence["observations"]["firstBrowserError"] = browser.stderr[-1200:]
    else:
        evidence["observations"]["firstBrowser"] = json.loads(browser.stdout.strip().splitlines()[-1])

    custom = dict(payload, capabilityCode=cap_code, capabilityName="阶段三实例定制信息展示",
                  templateId=created["id"], applicableCondition="F2",
                  capabilityDescription="临时引用验证")
    custom.pop("templateCode")
    custom.pop("templateName")
    custom.pop("templateDescription")
    custom["inputParams"] = [dict(p, defaultValue=("instance-custom" if p["name"] == "contentData" else p["defaultValue"]))
                             for p in payload["inputParams"]]
    first_cap = api("/devices/" + devices[0] + "/capabilities", "POST", custom)
    evidence["observations"]["firstCapabilityStatus"] = first_cap["capabilityStatus"]
    evidence["observations"]["firstCustomizedDefault"] = next(
        p["defaultValue"] for p in first_cap["inputParams"] if p["name"] == "contentData")
    evidence["observations"]["usageAfterFirst"] = template_row()["usageCount"]

    api("/devices", "POST", device_payload(devices[1]))
    second = dict(custom, inputParams=payload["inputParams"])
    api("/devices/" + devices[1] + "/capabilities", "POST", second)
    evidence["observations"]["usageAfterSecond"] = template_row()["usageCount"]
    status, body = raw(base + "/" + template_code, "DELETE")
    evidence["observations"]["usedDeleteHttpStatus"] = status
    evidence["observations"]["usedDeleteMessage"] = body.get("message")
    evidence["observations"]["actualReferencedDeviceCount"] = db.query(db.source,
        "SELECT count(DISTINCT d.id) FROM tip_stage2_v14.device_capabilities c "
        "JOIN tip_stage2_v14.devices d ON d.id=c.device_id "
        "WHERE c.template_id=" + str(created["id"]))

    api(base + "/" + template_code + "/status", "POST", {"status": "INACTIVE"})
    evidence["observations"]["stoppedTemplateStatus"] = template_row()["templateStatus"]
    api("/devices", "POST", device_payload(devices[2]))
    evidence["observations"]["newDeviceInitialCapabilities"] = len(api("/devices/" + devices[2] + "/capabilities"))
    browser = subprocess.run([str(node_bin), str(node), "third"], cwd=root, env=environment,
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
    evidence["observations"]["thirdBrowserExit"] = browser.returncode
    if browser.returncode:
        evidence["observations"]["thirdBrowserError"] = browser.stderr[-1200:]
    else:
        evidence["observations"]["thirdBrowser"] = json.loads(browser.stdout.strip().splitlines()[-1])
    old = api("/devices/" + devices[0] + "/capabilities")
    evidence["observations"]["oldInstanceStatusAfterStop"] = old[0]["capabilityStatus"]
    evidence["observations"]["oldInstanceDefaultAfterStop"] = next(
        p["defaultValue"] for p in old[0]["inputParams"] if p["name"] == "contentData")
    evidence["observations"]["usageAfterStop"] = template_row()["usageCount"]
finally:
    try:
        cleanup()
    except Exception as error:
        evidence["cleanup"]["error"] = str(error)
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(evidence, ensure_ascii=False))
