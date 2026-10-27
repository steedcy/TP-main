"""Classify the exception timeline rule from the preserved Stage3 task 83 run."""
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
source = stage / "evidence/TC-050-baseline-failure-20261027T042130Z.json"
raw = source.read_bytes()
run = json.loads(raw)
assert run["runtimeInput"] == "V1.5" and run["sourceTaskId"] == 19
assert run["task"]["id"] == 83
events = [event for event in run["events"] if event["taskId"] == 83]
exceptions = [item for item in run["exceptions"] if item["taskId"] == 83]
assert len(exceptions) == 3
assert {item["exceptionStatus"] for item in exceptions} == {"RESOLVED"}
assert {item["exceptionType"] for item in exceptions} == {"STEP_FAILED", "CAPABILITY_GAP"}
recovery = [event for event in events if event["eventType"] in
            ("EXCEPTION_RECOVERED", "EXCEPTION_RECOVERY_FAILED")]
assert len(recovery) == 3
assert sum(event["reasonCode"] is None for event in recovery) == 2
assert all(item["recoveryAction"] and item["recoveryResult"] and
           item["impactConclusion"] and item["reasonCode"] for item in exceptions)
event_text = "\n".join((event.get("reasonCode") or "") + " " +
                       (event.get("detailSummary") or "") for event in events)
missing_impacts = [item["id"] for item in exceptions
                   if item["impactConclusion"] not in event_text]
assert missing_impacts == [5, 4, 3]
last_recovery = recovery[-1]
assert last_recovery["eventType"] == "EXCEPTION_RECOVERED"
assert any(event["eventType"] == "REPLAN_FAILED" and
           event["id"] < last_recovery["id"] for event in events)
assert run["task"]["status"] == "PENDING_MANUAL"

evidence = {
    "classifiedAt": datetime.now().astimezone().isoformat(),
    "runtimeInput": "V1.5",
    "sourceEvidence": "acceptance/stage3/evidence/" + source.name,
    "sourceSha256": hashlib.sha256(raw).hexdigest(),
    "taskId": 83,
    "taskStatus": run["task"]["status"],
    "exceptions": exceptions,
    "recoveryEvents": recovery,
    "replanFailedEventIds": [event["id"] for event in events
                             if event["eventType"] == "REPLAN_FAILED"],
    "exceptionIdsWhoseExactImpactConclusionIsAbsentFromTimeline": missing_impacts,
    "recoveryEventIdsWithNullReasonCode": [event["id"] for event in recovery
                                                if event["reasonCode"] is None],
    "finding": "Exception records hold all five fields; the task timeline omits each exact impact conclusion, two recovery events lack reasonCode, and a recovered event follows replan failure while the task is pending manual.",
}
name = "SRS_F018-R09-task83-timeline-fields.json"
out = stage / "evidence" / name
assert not out.exists()
out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
ref = "acceptance/stage3/evidence/" + name


def update_csv(name, key, value, update):
    path = stage / name
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    row = next(item for item in rows if item[key] == value)
    update(row)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def update_rule(row):
    assert row["status"] == "NOT_RUN"
    row.update(status="F", verifiedBy="TC-057.S2;TC-059.S2", evidence=ref)


def update_issue(row):
    assert row["状态"] == "待修复" and "SRS_F018.R09" in row["关联需求规则"]
    row["事实"] += (" 任务83三条异常记录的五个字段均非空，但任务事件时间线没有任一条对应的完整影响判断结论；"
                    "两条EXCEPTION_RECOVERED的reasonCode为空。")
    row["证据"] += ";" + ref
    row["阶段4动作"] += " 恢复事件需逐条保留异常类型、恢复动作、结果、影响结论与原因码，并核对API和页面时间线。"


update_csv("rules.csv", "ruleId", "SRS_F018.R09", update_rule)
update_csv("issues.csv", "编号", "DEF-S3-066", update_issue)
progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
old = "281 条需求规则为 P 101、F 47、NT 11、未执行 122"
assert old in body
body = body.replace(old, "281 条需求规则为 P 101、F 48、NT 11、未执行 121", 1)
note = ("- `SRS_F018.R09`：复核本轮V1.5任务83原始异常与事件逐条对应。三条异常记录的类型、恢复动作、"
        "结果、影响结论和原因码非空，但事件时间线没有完整的对应影响结论，两条恢复成功事件reasonCode为空；"
        "重新规划失败后又记恢复成功。规则判F，补充既有`DEF-S3-066`；TC-057.S2的独立恢复成功场景尚未执行，"
        "不据此判该步骤通过。原始文件哈希及事件对照见`evidence/SRS_F018-R09-task83-timeline-fields.json`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 12:34（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded SRS_F018.R09 F; TC-057.S2 remains NOT_RUN")
