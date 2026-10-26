"""Record TC-066.S1/S3 and independently covered F021 rules."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
def only(pattern):
    files = list((stage / "evidence").glob(pattern))
    assert len(files) == 1, (pattern, files)
    return files[0], json.loads(files[0].read_text(encoding="utf-8"))
live_file, live = only("TC-066-terminate-live-*.json")
ui_file, ui = only("TC-066-terminate-ui-64.json")
boundary_file, boundary = only("TC-066-terminate-modal-boundary.json")
validation_file, validation = only("TC-066-terminate-validation-*.json")
follow_file, follow = only("TC-066-terminate-followup-*.json")
repeat_file, repeat = only("TC-066-terminal-reject-*.json")
resume_file, resume = only("TC-066-terminal-resume-reject-*.json")

assert live["started"]["taskId"] == 64 and live["atBusy"]["currentTaskId"] == 64
assert live["taskBeforeUI"]["status"] == "EXECUTING"
assert live["browserExitCode"] == 0 and live["taskAfterUI"]["status"] == "MANUAL_TERMINATED"
assert live["restore"]["allSixOnlineIdle"] and live["restore"]["templateStatus"] == "DISABLED"
assert live["restore"]["delayMs"] == 1000
assert ui["modalVisible"] and ui["emptyReasonDisabled"] and ui["uncheckedDisabled"]
assert ui["checkedEnabled"] and ui["confirmHttpStatus"] == 200
assert "不等同于设备安全急停" in ui["warningText"]
assert boundary["lengthAfter201Input"] == 200 and boundary["closedAfterCancel"]
assert boundary["terminatePostCountAfterCancel"] == 0
assert all(not c["accepted"] and "HTTP 400" in c["error"] for c in validation["cases"])
assert validation["before"] == validation["after"]
assert follow["task"]["status"] == "MANUAL_TERMINATED" and follow["task"]["manualTerminateReason"]
assert [a["stepStatus"] for a in follow["assignments"]] == ["FROZEN"]
assert follow["agent"]["workStatus"] == "IDLE" and follow["agent"]["currentTaskId"] is None
assert any(c["commandType"] == "TASK_CANCEL" and c["status"] == "CONFIRMED_IDLE"
           for c in follow["commands"])
assert "TASK_CANCEL_REQUESTED" in [e["eventType"] for e in follow["events"]]
assert "TASK_CANCEL_CONFIRMED_IDLE" in [e["eventType"] for e in follow["events"]]
assert not repeat["repeatTerminate"]["accepted"] and repeat["before"] == repeat["after"]
assert not resume["retryPlanning"]["accepted"] and resume["before"] == resume["after"]
assert len(live["operationLogs"]) == 1 and live["operationLogs"][0]["detail"] is None
assert live["operationLogs"][0]["username"] == "oprator"

ref = lambda *files: ";".join("acceptance/stage3/evidence/" + p.name for p in files)
today = datetime.now().astimezone().date().isoformat()
def update(path, key, changes):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    for target, change in changes.items():
        row = next(r for r in rows if r[key] == target)
        assert row["status"] == "NOT_RUN"
        row.update(change)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

update(stage / "steps.csv", "stepId", {
    "TC-066.S1": dict(status="P", observedAt=today,
        actual="任务64真实执行中打开人工终止弹窗，显示业务终止非安全急停及责任边界；空原因/未勾选均禁用，201字符被限制为200；取消弹窗未发终止请求且任务20保持待人工；后填写原因并确认成功将任务64置人工终止。服务端空原因、未确认、超200均400且任务20无变化。",
        evidence=ref(live_file, ui_file, boundary_file, validation_file,
                     stage / "evidence/TC-066-terminate-modal-64.png"), issue=""),
    "TC-066.S3": dict(status="F", observedAt=today,
        actual="任务64终止事件记录操作者、时间、原因，取消请求及最终CONFIRMED_IDLE有事件和命令；TASK_TERMINATE操作记录有操作者、时间、结果，但detail为空，不含终止原因或设备响应，不满足两类记录完整留痕。",
        evidence=ref(live_file, follow_file), issue="DEF-S3-059")})

update(stage / "rules.csv", "ruleId", {
    "SRS_F021.R01": dict(status="P", verifiedBy="TC-066.S1",
        evidence=ref(ui_file, boundary_file, validation_file), issue=""),
    "SRS_F021.R03": dict(status="P", verifiedBy="TC-066.S2",
        evidence=ref(live_file, follow_file), issue=""),
    "SRS_F021.R04": dict(status="P", verifiedBy="TC-066.S2",
        evidence=ref(live_file, follow_file), issue=""),
    "SRS_F021.R05": dict(status="P", verifiedBy="TC-066.S1",
        evidence=ref(ui_file, stage / "evidence/TC-066-terminate-modal-64.png"), issue=""),
    "SRS_F021.R07": dict(status="P", verifiedBy="TC-066.S2",
        evidence=ref(live_file, repeat_file, resume_file), issue=""),
    "SRS_F021.R08": dict(status="F", verifiedBy="TC-066.S3",
        evidence=ref(live_file, follow_file), issue="DEF-S3-059")})

issues = stage / "issues.csv"
with issues.open(encoding="utf-8-sig", newline="") as stream:
    assert "DEF-S3-059" not in {r["编号"] for r in csv.DictReader(stream)}
with issues.open("a", encoding="utf-8", newline="") as stream:
    csv.writer(stream, lineterminator="\n").writerow([
        "DEF-S3-059", "缺陷", "中", "TC-066.S3", "SRS_F021.R08", "待修复",
        "真实任务64人工终止后，任务时间线记录操作者、时间、原因、取消请求及设备CONFIRMED_IDLE，命令记录也保留确认状态；对应TASK_TERMINATE操作日志仅有操作者、时间、结果，detail为null，缺原因和设备响应摘要，不满足两类记录完整留痕。",
        ref(live_file, follow_file),
        "在人工终止操作日志的脱敏详情中写原因及每个设备取消结果，关联取消确认事件；复测多设备与取消超时"])
print("recorded TC-066.S1 P, S3 F, five F021 P and R08 F")
