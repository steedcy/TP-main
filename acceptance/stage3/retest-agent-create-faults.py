"""TC-013: scoped insert faults against one disposable, connection-tested device."""
import importlib.util
import json
import re
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    item = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(item)
    return item


local = module("local", root / "scripts/local-test-environment.py")
db = module("db", root / "acceptance/stage2/db-isolation.py")
api = local.API("配置管理员")
code, port = "S3_TC013_FAULTS_C", 8202
fixture = dict(local.load(local.FIXTURES / "devices.json")[0])
fixture.update(deviceCode=code, deviceName="阶段三临时代理故障设备",
               accessEndpoint=f"http://127.0.0.1:{port}",
               accessCredentialRef="S3-TC013-ONLY", remark="代理插入故障隔离测试")
fixture.pop("capabilities")
assert all(d["deviceCode"] != code for d in api("/devices?page=1&size=100")["content"])
other = next(a["agentId"] for a in api("/device-agents?page=1&size=100")["content"]
             if a["deviceCode"] == "SIM_F2_DISPLAY")
assert re.fullmatch(r"AGT-[A-Z0-9]{8}", other)
function = "tip_stage2_v14.s3_tc013_agent_fault"
trigger = "s3_tc013_agent_fault"
table = "tip_stage2_v14.device_agents"
out = stage / "evidence" / ("TC-013-agent-create-faults-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "deviceCode": code,
      "collisionTargetAgentCode": other, "faults": {}, "cleanup": {}}
created = False
simulator_pid = None
trigger_active = False
function_exists = False


def count_agent(device_id):
    return int(db.query(db.source,
        f"SELECT count(*) FROM {table} WHERE device_id={device_id}"))


def raw_create():
    body = json.dumps({"deviceCode": code}).encode("utf-8")
    req = urllib.request.Request(local.BASE + "/device-agents", method="POST", data=body,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + api.token})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read()
            return {"httpStatus": response.status,
                    "contentType": response.headers.get("Content-Type"),
                    "body": json.loads(raw.decode("utf-8", errors="replace"))}
    except urllib.error.HTTPError as error:
        raw = error.read()
        return {"httpStatus": error.code,
                "contentType": error.headers.get("Content-Type"),
                "rawBodyHex": raw.hex(),
                "body": json.loads(raw.decode("utf-8", errors="replace"))}


def arm(mode, device_id):
    global trigger_active
    assert mode in ("collision", "insert_failure")
    db.query(db.source,
        f"CREATE TRIGGER {trigger} BEFORE INSERT ON {table} FOR EACH ROW "
        f"WHEN (NEW.device_id = {device_id}) EXECUTE FUNCTION {function}('{mode}','{other}')")
    trigger_active = True


def disarm():
    global trigger_active
    if trigger_active:
        db.query(db.source, f"DROP TRIGGER IF EXISTS {trigger} ON {table}")
        trigger_active = False


try:
    api("/devices", "POST", fixture)
    created = True
    device_id = int(db.query(db.source,
        "SELECT id FROM tip_stage2_v14.devices WHERE device_code='" + code + "'"))
    ev["deviceId"] = device_id
    token = api("/devices/" + code + "/device-token/rotate", "POST")["accessToken"]
    local.start_simulator(fixture, token)
    simulator_pid = local.load(local.LOCAL / "processes.json")[code]["pid"]
    ev["connectionTest"] = api("/devices/" + code + "/connection-test", "POST")
    assert ev["connectionTest"]["result"] == "PASSED"
    assert count_agent(device_id) == 0
    db.query(db.source,
        f"CREATE FUNCTION {function}() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN IF TG_ARGV[0] = 'collision' THEN NEW.agent_code := TG_ARGV[1]; RETURN NEW; "
        "END IF; RAISE EXCEPTION 'S3_TC013_INJECTED_INSERT_FAILURE'; END; $$")
    function_exists = True
    for mode in ("collision", "insert_failure"):
        arm(mode, device_id)
        result = raw_create()
        disarm()
        ev["faults"][mode] = {"request": result,
            "agentCountAfter": count_agent(device_id),
            "connectionTestStatusAfter": api("/devices/" + code)["connectionTestStatus"]}
    ev["retry"] = raw_create()
    agent = next(a for a in api("/device-agents?page=1&size=100")["content"]
                 if a["deviceCode"] == code)
    ev["agentAfterRetry"] = {k: agent.get(k) for k in
        ("agentId", "agentStatus", "onlineStatus", "workStatus", "deviceCode")}
    ev["agentCountAfterRetry"] = count_agent(device_id)
    ev["repeatCreate"] = raw_create()
    ev["agentCountAfterRepeat"] = count_agent(device_id)
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        agent = api("/device-agents/" + agent["agentId"])
        if agent["onlineStatus"] == "ONLINE":
            break
        time.sleep(1)
    ev["agentAfterBinding"] = {k: agent.get(k) for k in
        ("agentId", "agentStatus", "onlineStatus", "workStatus", "lastReportedAt")}
    ev["simulatorHealth"] = {k: v for k, v in local.request(
        fixture["accessEndpoint"] + "/device-api/v1/health?nonce=stage3-tc013", token=token).items()
        if k in ("deviceCode", "onlineStatus", "workStatus")}
finally:
    try:
        disarm()
        if function_exists:
            db.query(db.source, f"DROP FUNCTION IF EXISTS {function}()")
        ev["cleanup"]["faultFunctionAbsent"] = db.query(db.source,
            "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
            "WHERE n.nspname='tip_stage2_v14' AND p.proname='s3_tc013_agent_fault'") == "0"
    except Exception as error:
        ev["cleanup"]["faultCleanupError"] = str(error)
    if created:
        try:
            api("/devices/" + code, "DELETE")
            ev["cleanup"]["deviceStatus"] = api("/devices/" + code)["deviceStatus"]
        except Exception as error:
            ev["cleanup"]["deviceCleanupError"] = str(error)
    if simulator_pid is not None:
        probe = subprocess.run(["powershell", "-NoProfile", "-Command",
            f"(Get-CimInstance Win32_Process -Filter 'ProcessId={simulator_pid}').CommandLine"],
            capture_output=True, encoding="utf-8", errors="replace")
        if "device-simulator-runtime.jar" in probe.stdout:
            stopped = subprocess.run(["taskkill", "/PID", str(simulator_pid), "/F"],
                                     capture_output=True, encoding="utf-8", errors="replace")
            ev["cleanup"]["simulatorStopped"] = stopped.returncode == 0
        else:
            ev["cleanup"]["simulatorStopped"] = False
    ev["finishedAt"] = datetime.now(timezone.utc).isoformat()
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": out.name,
    "faultStatus": {k: v["request"]["httpStatus"] for k, v in ev["faults"].items()},
    "retryStatus": ev.get("retry", {}).get("httpStatus"), "cleanup": ev["cleanup"]},
    ensure_ascii=False))
