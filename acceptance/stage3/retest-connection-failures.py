"""TC-009.S2: unreachable, malformed, and read-timeout device handshakes."""
import importlib.util
import json
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
api = local.API("配置管理员")
code = "SIM_F2_DISPLAY"
original = api("/devices/" + code)
assert original["connectionTestStatus"] == "PASSED"
mode = {"value": "INVALID_JSON"}


class Stub(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        if mode["value"] == "TIMEOUT":
            time.sleep(6)
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{malformed-json")
        except (BrokenPipeError, ConnectionResetError):
            pass


server = ThreadingHTTPServer(("127.0.0.1", 0), Stub)
threading.Thread(target=server.serve_forever, daemon=True).start()


def payload(endpoint):
    return {"deviceName": original["deviceName"], "areaCode": original["areaCode"],
            "positionX": original["positionX"], "positionY": original["positionY"],
            "accessEndpoint": endpoint, "accessCredentialRef": "",
            "statusReportInterval": original["statusReportInterval"], "remark": original["remark"]}


def create_agent_status():
    request = urllib.request.Request(local.BASE + "/device-agents",
        data=json.dumps({"deviceCode": code}).encode(), method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + api.token})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


evidence = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
            "isolatedSchema": "tip_stage2_v14", "deviceCode": code, "cases": {}}
try:
    for name, endpoint in (
        ("UNREACHABLE", "http://127.0.0.1:8199"),
        ("INVALID_JSON", f"http://127.0.0.1:{server.server_port}"),
        ("TIMEOUT", f"http://127.0.0.1:{server.server_port}"),
    ):
        mode["value"] = name
        api("/devices/" + code, "PUT", payload(endpoint))
        before = api("/devices/" + code)
        result = api("/devices/" + code + "/connection-test", "POST")
        after = api("/devices/" + code)
        evidence["cases"][name] = {
            "beforeStatus": before["connectionTestStatus"],
            "testResult": result["result"], "failureReason": result.get("failReason"),
            "savedStatus": after["connectionTestStatus"],
            "agentCreateHttpStatus": create_agent_status(),
        }
finally:
    api("/devices/" + code, "PUT", payload(original["accessEndpoint"]))
    evidence["restoredEndpointMatches"] = api("/devices/" + code)["accessEndpoint"] == original["accessEndpoint"]
    evidence["restoreRetestResult"] = api("/devices/" + code + "/connection-test", "POST")["result"]
    evidence["finalConnectionStatus"] = api("/devices/" + code)["connectionTestStatus"]
    server.shutdown()
    server.server_close()

out = Path(__file__).resolve().parent / "evidence/TC-009-connection-failures.json"
out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(evidence, ensure_ascii=False))
