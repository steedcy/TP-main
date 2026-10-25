"""Rotate only the six F2 credentials after an isolated F2 reset.

The previous DPAPI file is retained locally for restoring the prior runtime.
No plaintext token or key is written to acceptance evidence.
"""
import hashlib
import importlib.util
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)
original = ROOT / ".local-test/device-credentials.dpapi"
backup = ROOT / ".local-test/stage2-before-device-credentials.dpapi"
if original.exists() and not backup.exists():
    shutil.copy2(original, backup)
api = env.API("配置管理员")
values = env.secrets()
codes = [d["deviceCode"] for d in env.load(env.FIXTURES / "devices.json")]
assert len(codes) == 6 and all(code.startswith("SIM_F2_") for code in codes)
for code in codes:
    values[code] = api("/devices/" + code + "/device-token/rotate", "POST")["accessToken"]
    env.store_secrets(values)
result = {"recordedAt": env.stamp(), "rotatedDeviceCodes": codes,
          "previousDpapiSha256": hashlib.sha256(backup.read_bytes()).hexdigest() if backup.exists() else None,
          "currentDpapiSha256": hashlib.sha256(original.read_bytes()).hexdigest()}
out = ROOT / "acceptance/stage2/evidence/credential-rotation.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
