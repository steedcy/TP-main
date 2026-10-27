"""Record TC-064.S2's four independent actions and the retry coverage gap."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
ev = stage / "evidence"
switch_file = ev / "TC-064-switch-baseline-20261027T012103Z.json"
retry_file = ev / "TC-064-retry-planning-20261027T012146Z.json"
terminate_file = ev / "TC-064-terminate-ui-35.json"
follow_file = ev / "TC-064-manual-branches-followup-20261027T012317Z.json"
failed_file = ev / "TC-064-mark-failed-task20-ui.json"
switch = json.loads(switch_file.read_text(encoding="utf-8"))
retry = json.loads(retry_file.read_text(encoding="utf-8"))
term = json.loads(terminate_file.read_text(encoding="utf-8"))
follow = json.loads(follow_file.read_text(encoding="utf-8"))
failed = json.loads(failed_file.read_text(encoding="utf-8"))
assert all(x["runtimeInput"] == "V1.5" for x in (switch, retry, term, follow, failed))
assert len({switch["created"]["id"], retry["created"]["id"], term["taskId"], failed["taskId"]}) == 4
assert switch["created"]["id"] == 69 and retry["created"]["id"] == 70
assert term["taskId"] == 35 and failed["taskId"] == 20
assert switch["before"]["status"] == retry["before"]["status"] == "PENDING_MANUAL"
assert switch["action"]["accepted"] and retry["action"]["accepted"]
for sample in (switch, retry):
    assert sample["after"]["status"] == "EXECUTING"
    assert len(sample["planVersions"]) == 1
    assert all(sample["planVersions"][0][key] == "PASS" for key in
               ("structureCheckResult", "capabilityCheckResult", "constraintCheckResult"))
    assert sample["planVersions"][0]["source"] == "BASELINE_TEMPLATE"
    assert len(sample["manualAudit"]) == 1
    assert sample["manualAudit"][0]["operationResult"] == "SUCCESS"
    assert sample["manualAudit"][0]["detail"] is None
    assert sample["cleanup"] == "MANUAL_TERMINATED"
assert any(e["eventType"] == "PLAN_GENERATED" and
           e["reasonCode"] == "ERR_PLANNING_MODEL_FAILED" for e in retry["events"])
assert not any(e["eventType"] == "SUPERVISION_COMPLETED" for e in retry["events"])
assert term["taskStatusBefore"] == "待人工处理" and term["confirmHttpStatus"] == 200
assert term["emptyReasonDisabled"] and term["uncheckedDisabled"] and term["checkedEnabled"]
assert term["modalClosedAfterConfirm"]
assert failed["beforeStatus"] == "待人工处理" and failed["afterStatus"] == "失败"
assert all(follow["tasks"][str(i)]["task"]["status"] == "MANUAL_TERMINATED" for i in (35, 69, 70))
assert follow["tasks"]["35"]["task"]["manualTerminateReason"] == "阶段3人工终止边界复测"
assert len(follow["manualAudit"]) == 2 and len(follow["terminateAudit"]) == 1
assert len(follow["simulatorAgents"]) == 6
assert all(a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE" and
           a["workStatus"] == "IDLE" and a["currentTaskId"] is None
           for a in follow["simulatorAgents"])

base = "acceptance/stage3/evidence/"
refs = ";".join(base + f.name for f in
                (failed_file, switch_file, retry_file, terminate_file, follow_file))
steps_file = stage / "steps.csv"
with steps_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, steps = reader.fieldnames, list(reader)
row = next(r for r in steps if r["stepId"] == "TC-064.S2")
assert row["status"] == "NOT_RUN"
row.update(status="F", observedAt=datetime.now().strftime("%Y-%m-%d"),
           actual="四个独立任务分别执行置失败、转基线、重试规划和待人工终止。置失败形成终态；转基线模板三类校验PASS并进入执行；重试时模型未生成候选，自主新计划和监督正向路径未验证，自动模板降级后三类校验PASS；终止原因和二次确认经浏览器提交成功。三项人工动作审计detail为空，缺本次操作具体原因，处置记录不完整。",
           evidence=refs, issue="DEF-S3-062;NT-S3-026")
with steps_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(steps)

rules_file = stage / "rules.csv"
with rules_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rules = reader.fieldnames, list(reader)
row = next(r for r in rules if r["ruleId"] == "SRS_F020.R05")
assert row["status"] == "NOT_RUN"
row.update(status="NT", verifiedBy="TC-064.S2", evidence=base + switch_file.name + ";" +
           base + retry_file.name, issue="NT-S3-026")
with rules_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rules)

issues_file = stage / "issues.csv"
with issues_file.open(encoding="utf-8-sig", newline="") as stream:
    assert "NT-S3-026" not in {r["编号"] for r in csv.DictReader(stream)}
with issues_file.open("a", encoding="utf-8", newline="") as stream:
    csv.writer(stream, lineterminator="\n").writerow([
        "NT-S3-026", "前置缺口", "待定", "TC-064.S2;TC-065.S1", "SRS_F020.R05", "待补模型可用正向路径",
        "独立任务70重试规划触发模型候选生成失败ERR_PLANNING_MODEL_FAILED，转模板降级且三类校验PASS；本轮未获得新的自主候选计划及监督判定，不能判定重试规划正向路径或人工操作不绕过监督。",
        base + retry_file.name + ";" + base + follow_file.name,
        "在隔离且规划模型可用时用独立待人工任务重试，核对新计划三类校验、监督判定和执行门槛，保留原始请求与事件。"])

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
assert "原 200 步：P 42、F 59、NT 19、未执行 80" in body
assert "281 条需求规则为 P 92、F 40、NT 10、未执行 139" in body
body = body.replace("原 200 步：P 42、F 59、NT 19、未执行 80",
                    "原 200 步：P 42、F 60、NT 19、未执行 79", 1)
body = body.replace("281 条需求规则为 P 92、F 40、NT 10、未执行 139",
                    "281 条需求规则为 P 92、F 40、NT 11、未执行 138", 1)
heading = "## 已执行\n\n"
assert heading in body
note = ("- TC-064.S2四分支本轮闭合尝试：任务20置失败、任务69转基线、任务70重试规划、"
        "任务35从待人工由Chrome确认终止，均为独立任务。转基线模板V1.2三类校验PASS后进入执行；"
        "重试规划模型返回`ERR_PLANNING_MODEL_FAILED`，随后模板降级三类校验PASS，但没有新的自主计划及"
        "监督判定，正向重试路径记`NT-S3-026`，`SRS_F020.R05`暂判NT。任务35原因与二次确认"
        "HTTP200、终态保留；任务69/70执行中已人工终止，六仿真代理在线空闲。"
        "三项处置审计`detail=null`，原因留痕缺陷`DEF-S3-062`可复现，故TC-064.S2整步判F。"
        "浏览器取消弹窗的即时`isHidden`采样为false，与任务64旧样本相同，未据此判断取消逻辑。"
        "原始证据见`evidence/TC-064-*`。\n")
body = body.replace(heading, heading + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 08:50（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded TC-064.S2 F and SRS_F020.R05 NT; four branches attempted")
