"""TC-086 live sensitive-data inspection. Evidence contains booleans/counts only."""
import hashlib
import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def module(name, location):
    spec = importlib.util.spec_from_file_location(name, location)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


local = module("tip_local", ROOT / "scripts/local-test-environment.py")
db = module("tip_db", ROOT / "acceptance/stage2/db-isolation.py")
schema = "tip_stage2_v14"
assert db.schema == schema and db.source == "airport_ai"

accounts = [local.account(role) for role in ("系统管理员", "运行操作员", "配置管理员")]
passwords = [password for _, password in accounts]
user_lines = db.query(db.source, f"SELECT username,password_hash FROM {schema}.users ORDER BY id").splitlines()
users = [line.split("|", 1) for line in user_lines]
hashes = [value for _, value in users]

device_lines = db.query(db.source,
    f"SELECT device_code,coalesce(device_token_hash,''),coalesce(device_token_ciphertext,''),"
    f"coalesce(access_credential_ref,'') "
    f"FROM {schema}.devices ORDER BY device_code").splitlines()
devices = [line.split("|", 3) for line in device_lines]
device_secrets = local.secrets()
matched_device_hashes = sum(
    hash_value == hashlib.sha256(device_secrets[code].encode()).hexdigest()
    for code, hash_value, _, _ in devices if code in device_secrets)
plain_device_tokens_in_db = any(
    token and any(token == value for value in (code, hash_value, ciphertext))
    for code, hash_value, ciphertext, _ in devices for token in device_secrets.values())

admin_users = local.API("系统管理员")("/users?page=1&size=100")
config_devices = local.API("配置管理员")("/devices?page=1&size=100")
listed_users = admin_users["content"]
listed_devices = config_devices["content"]
user_api_json = json.dumps(listed_users, ensure_ascii=False)
device_api_json = json.dumps(listed_devices, ensure_ascii=False)
log_lines = db.query(db.source,
    f"SELECT coalesce(detail::text,'') FROM {schema}.operation_logs ORDER BY id").splitlines()
password_matches = [
    {"accountIndex": index, "field": key, "exact": password == value,
     "passwordLength": len(password), "fieldLength": len(value)}
    for index, password in enumerate(passwords)
    for row in listed_users for key, value in row.items()
    if isinstance(value, str) and password in value
]

evidence = {
    "observedAt": datetime.now(timezone.utc).isoformat(),
    "runtimeInput": "V1.5",
    "isolatedSchema": schema,
    "userCount": len(users),
    "passwordHashesAllBcrypt": all(re.fullmatch(r"\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}", value) for value in hashes),
    "userPlainPasswordsInDatabaseHashColumn": any(password == value for password in passwords for value in hashes),
    "userPlainPasswordsInListResponse": any(match["exact"] for match in password_matches),
    "userListExposesPasswordHash": any("passwordHash" in row for row in listed_users),
    "deviceCount": len(devices),
    "deviceSecretCount": len(device_secrets),
    "matchedDeviceTokenHashes": matched_device_hashes,
    "configuredDeviceCiphertextsNonempty": all(ciphertext for code, _, ciphertext, _ in devices if code in device_secrets),
    "plainDeviceTokensInDatabaseFields": plain_device_tokens_in_db,
    "plainDeviceTokensInListResponse": any(token in device_api_json for token in device_secrets.values()),
    "deviceListExposesTokenHashOrCiphertext": any(
        "deviceTokenHash" in row or "deviceTokenCiphertext" in row for row in listed_devices),
    "deviceListHasMaskedCredentialField": all("accessCredentialRefMasked" in row for row in listed_devices),
    "operationLogCountChecked": len(log_lines),
    "plainUserPasswordsInLogDetail": any(password and password in line for password in passwords for line in log_lines),
    "plainDeviceTokensInLogDetail": any(token and token in line for token in device_secrets.values() for line in log_lines),
    "deviceCredentialRefsInLogDetailCount": sum(
        1 for _, _, _, credential_ref in devices if credential_ref and any(credential_ref in line for line in log_lines)),
}
out = HERE / "evidence/TC-086-sensitive.json"
out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(evidence, ensure_ascii=False))
