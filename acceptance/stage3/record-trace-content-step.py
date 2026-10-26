"""Record TC-084.S2 after this run's trace UI/API, role and retention checks."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
ev = stage / "evidence"
ui_file = ev / "TC-084-S2-trace-content-task19.json"
api_file = ev / "TC-084-S2-trace-content-api-task19.json"
permissions_file = ev / "TC-084-trace-permissions-20261026T204811Z.json"
immutable_file = ev / "TC-084-trace-immutability-20261026T130257Z.json"
ui = json.loads(ui_file.read_text(encoding="utf-8"))
api = json.loads(api_file.read_text(encoding="utf-8"))
permissions = json.loads(permissions_file.read_text(encoding="utf-8"))
immutable = json.loads(immutable_file.read_text(encoding="utf-8"))

assert ui["runtimeInput"] == api["runtimeInput"] == permissions["runtimeInput"] == immutable["runtimeInput"] == "V1.5"
assert ui["taskId"] == api["taskId"] == permissions["taskId"] == immutable["taskId"] == 19
assert ui["route"] == "/task-trace" and len(ui["versionHeaders"]) == len(api["versions"]) == 2
assert "版本1（自主规划）" in ui["versionHeaders"][0]
assert "版本2（基线模板）" in ui["versionHeaders"][1]
assert len(api["snapshots"]) == 2 and all(s["snapshotCode"] and s["generatedAt"] for s in api["snapshots"])
assert len(ui["eventTexts"]) == len(api["events"]) == 27
assert api["events"] == sorted(api["events"], key=lambda row: (row["occurredAt"], row["id"]))
for text, row in zip(ui["eventTexts"], api["events"]):
    assert text.startswith(row["occurredAt"] + " - " + row["eventType"])
    assert ("操作人" if row["trigger"] == "OPERATOR" else "系统") in text.split("\n", 1)[0]
    assert row["detailSummary"] in text
    if row["reasonCode"]:
        assert row["reasonCode"] in text
assert sum(not row["reasonCode"] for row in api["events"]) == 26
assert all(all(row[key] for key in ("eventType", "occurredAt", "trigger", "detailSummary"))
           for row in api["events"])
assert ui["eventEditControls"] == ui["eventEditableElements"] == 0
assert api["knownCredentialRawAbsent"] and api["sensitiveKeyNamesAbsent"]
assert permissions["authorized"] == {"systemAdminEventCount": 27, "operatorEventCount": 27}
assert not permissions["configAdmin"]["accepted"] and "HTTP 403" in permissions["configAdmin"]["error"]
assert permissions["denialLogs"]
assert immutable["before"] == {key: immutable["after"][key] for key in ("count", "sha256")}
assert all(not attempt["accepted"] for attempt in immutable["attempts"])
assert (ev / ui["screenshot"]).is_file()

refs = ";".join("acceptance/stage3/evidence/" + path.name for path in
                (ui_file, api_file, ev / ui["screenshot"], permissions_file, immutable_file))
path = stage / "steps.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["stepId"] == "TC-084.S2")
assert row["status"] == "NOT_RUN"
row.update(status="F", observedAt=datetime.now().astimezone().date().isoformat(),
           actual="任务19过程追溯页27条事件按时间正序展示类型、时间、触发方和摘要，两个历史计划版本及两个上下文快照保留；事件无编辑控件，PUT/DELETE被拒且前后哈希一致；系统管理员和运行操作员可读，配置管理员403并留拒绝审计；已知测试凭据原值未出现在读取数据。但27条事件中26条原因码为空，页面也无法列出这些原因码，不满足逐条展示。隐私检查仅覆盖本轮虚构对象和已知测试凭据。",
           evidence=refs, issue="DEF-S3-057")
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
body = body.replace("P 41、F 58、NT 19、未执行 82", "P 41、F 59、NT 19、未执行 81", 1)
heading = "## 已执行\n\n"
assert heading in body
note = ("- TC-084.S2：Chrome过程追溯页与API复核任务19的27条事件，时间正序，类型/时间/触发方/摘要可见；"
        "两个历史计划版本与两个上下文快照仍可读取，事件无编辑控件、写请求被拒且哈希不变；"
        "系统管理员和运行操作员可读，配置管理员403并留拒绝审计，已知测试凭据原值未出现在读取数据。"
        "但26条事件的`reasonCode`为空，页面也无法逐条显示，按已有`DEF-S3-057`判F。"
        "隐私检查限于虚构对象和已知测试凭据。新浏览器/API/角色证据见`evidence/TC-084-S2-*`与"
        "`evidence/TC-084-trace-permissions-20261026T204811Z.json`；旧的不可改删原始证据保持。\n")
body = body.replace(heading, heading + note, 1)
body = body.replace("2026-10-27 03:46（Asia/Shanghai）", "2026-10-27 04:48（Asia/Shanghai）", 1)
progress.write_text(body, encoding="utf-8")
print("recorded TC-084.S2 F on 26 missing reason codes")
