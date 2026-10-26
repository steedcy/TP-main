"""TC-043.S1: fresh risk-rule boundaries, versions, roles and page controls."""
import importlib.util
import json
import os
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
db_spec = importlib.util.spec_from_file_location("db", root / "acceptance/stage2/db-isolation.py")
db = importlib.util.module_from_spec(db_spec)
db_spec.loader.exec_module(db)
admin = local.API("配置管理员")
operator = local.API("运行操作员")
code = "S3_TC043_RULE"
empty_content_code = "S3_TC043_EMPTYCONTENT"
missing_content_code = "S3_TC043_MISSINGCONTENT"
out = stage / "evidence" / (
    "TC-043-risk-rule-crud-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")


def raw(token, path, body):
    request = urllib.request.Request(local.BASE + path, method="POST",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.loads(response.read())
            return {"httpStatus": response.status, "code": payload.get("code"),
                    "message": payload.get("message"), "data": payload.get("data")}
    except urllib.error.HTTPError as error:
        try:
            payload = json.loads(error.read())
        except Exception:
            payload = {}
        return {"httpStatus": error.code, "code": payload.get("code"),
                "message": (payload.get("message") or "")[:240]}


def row_count():
    return int(db.query(db.source, "SELECT count(*) FROM tip_stage2_v14.risk_rules"))


existing = admin("/risk-rules")
assert not any(row["ruleCode"] in (code, empty_content_code, missing_content_code, "")
               for row in existing)
ev = {"observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
      "isolatedSchema": "tip_stage2_v14", "ruleCode": code,
      "beforeCount": row_count(), "beforeRuleCodes": [row["ruleCode"] for row in existing],
      "boundary": {}, "cleanup": {}}
try:
    ev["boundary"]["emptyCode"] = raw(admin.token, "/risk-rules",
        {"ruleCode": "", "ruleContent": "阶段三空编码边界", "enabled": False})
    ev["boundary"]["missingCode"] = raw(admin.token, "/risk-rules",
        {"ruleContent": "阶段三缺编码边界", "enabled": False})
    ev["boundary"]["emptyContent"] = raw(admin.token, "/risk-rules",
        {"ruleCode": empty_content_code, "ruleContent": "", "enabled": False})
    ev["boundary"]["missingContent"] = raw(admin.token, "/risk-rules",
        {"ruleCode": missing_content_code, "enabled": False})
    ev["operatorCreate"] = raw(operator.token, "/risk-rules",
        {"ruleCode": code, "ruleContent": "无权创建", "enabled": False})
    ev["created"] = admin("/risk-rules", "POST", {"ruleCode": code,
        "ruleContent": "阶段三临时规则 V1.0", "enabled": False})
    ev["duplicate"] = raw(admin.token, "/risk-rules", {"ruleCode": code,
        "ruleContent": "重复编号", "enabled": False})
    ev["afterContentUpdate"] = admin("/risk-rules/" + code + "/update", "POST",
                                      {"ruleContent": "阶段三临时规则 V1.1"})
    ev["afterEnable"] = admin("/risk-rules/" + code + "/update", "POST", {"enabled": True})
    ev["afterDisable"] = admin("/risk-rules/" + code + "/update", "POST", {"enabled": False})
    ev["listed"] = next(row for row in admin("/risk-rules") if row["ruleCode"] == code)
    ev["allRulesBeforeCleanup"] = [{key: row.get(key) for key in
        ("ruleCode", "ruleVersion", "enabled")} for row in admin("/risk-rules")]
    node = "C:/Users/savy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
    environment = os.environ.copy()
    environment["PLAYWRIGHT_CORE_PATH"] = (
        "C:/Users/savy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright-core")
    browser = subprocess.run([node, str(stage / "retest-risk-rule-ui.cjs"), code],
                             cwd=root, env=environment, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=60)
    ev["browserExitCode"] = browser.returncode
    ev["browserOutput"] = browser.stdout.strip() if browser.returncode == 0 else browser.stderr.strip()[-500:]
    logs = admin("/operation-logs?page=1&size=100")["content"]
    ev["changeLogs"] = [row for row in logs if row["operationType"] == "RISK_RULE_CHANGE"
                        and row.get("operationTarget") == code]
finally:
    try:
        db.query(db.source,
            "DELETE FROM tip_stage2_v14.risk_rules WHERE rule_code IN "
            "('', '" + code + "', '" + empty_content_code + "', '" + missing_content_code + "')")
        ev["cleanup"]["afterCount"] = row_count()
        ev["cleanup"]["temporaryCodesRemaining"] = [row["ruleCode"] for row in admin("/risk-rules")
            if row["ruleCode"] in (code, empty_content_code, missing_content_code, "")]
    except Exception as error:
        ev["cleanup"]["error"] = str(error)
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(json.dumps({"evidence": str(out), "boundaryStatuses": {
    name: result["httpStatus"] for name, result in ev["boundary"].items()},
    "duplicateStatus": ev.get("duplicate", {}).get("httpStatus"),
    "versions": [ev.get(name, {}).get("ruleVersion") for name in
                 ("created", "afterContentUpdate", "afterEnable", "afterDisable")],
    "browserExitCode": ev.get("browserExitCode"), "cleanup": ev["cleanup"]}, ensure_ascii=False))
