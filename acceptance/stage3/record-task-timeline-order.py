"""Record F020.R07 from browser chronology and the existing mutation attempt."""
import csv
import json
from pathlib import Path

stage = Path(__file__).resolve().parent
ev = stage / "evidence"
ui_file = ev / "SRS_F020-R07-timeline-task19.json"
api_file = ev / "SRS_F020-R07-timeline-api-task19.json"
immutable_file = ev / "TC-084-trace-immutability-20261026T130257Z.json"
ui = json.loads(ui_file.read_text(encoding="utf-8"))
api = json.loads(api_file.read_text(encoding="utf-8"))
immutable = json.loads(immutable_file.read_text(encoding="utf-8"))

assert ui["runtimeInput"] == api["runtimeInput"] == immutable["runtimeInput"] == "V1.5"
assert ui["taskId"] == api["taskId"] == immutable["taskId"] == 19
assert ui["route"] == "/tasks/19" and "只读" in ui["cardTitle"]
assert len(ui["items"]) == api["count"] == api["uiCount"] == immutable["before"]["count"] == 27
assert ui["editControls"] == ui["editableElements"] == 0
assert (ev / ui["screenshot"]).is_file()
assert api["events"] == sorted(api["events"], key=lambda item: (item["occurredAt"], item["id"]))
assert api["uiTimestamps"] == sorted(api["uiTimestamps"])
assert [(item["occurredAt"], item["eventType"]) for item in api["events"]] == list(
    zip(api["uiTimestamps"], api["uiTypes"]))
assert immutable["before"] == {key: immutable["after"][key] for key in ("count", "sha256")}
assert all(not attempt["accepted"] for attempt in immutable["attempts"])
assert immutable["after"]["eventStillPresent"] and immutable["after"]["injectedTextAbsent"]

rule_path = stage / "rules.csv"
with rule_path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["ruleId"] == "SRS_F020.R07")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-063.S2",
           evidence=";".join("acceptance/stage3/evidence/" + p.name for p in
                             (ui_file, api_file, ev / ui["screenshot"], immutable_file)), issue="")
with rule_path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
body = body.replace("P 82、F 39、NT 9、未执行 151", "P 83、F 39、NT 9、未执行 150", 1)
heading = "## 已执行\n\n"
assert heading in body
note = ("- `SRS_F020.R07`：Chrome运行操作员查看本轮已完成任务19的27条时间线，"
        "页面顺序与API事件时间、类型逐条一致且时间正序；卡片无编辑、删除按钮或可编辑控件。"
        "结合本轮对真实事件PUT/DELETE均被拒、前后27条事件内容哈希一致的原始证据，"
        "只读正序及不可改删规则判P。TC-063.S2还要求详情字段和执行中≤15秒刷新，"
        "此处没有覆盖，整步维持未执行。浏览器及API证据见`evidence/SRS_F020-R07-*`，"
        "不可修改证据见`evidence/TC-084-trace-immutability-20261026T130257Z.json`。\n")
body = body.replace(heading, heading + note, 1)
body = body.replace("2026-10-27 02:52（Asia/Shanghai）", "2026-10-27 03:45（Asia/Shanghai）", 1)
progress.write_text(body, encoding="utf-8")
print("recorded SRS_F020.R07 P; TC-063.S2 unchanged")
