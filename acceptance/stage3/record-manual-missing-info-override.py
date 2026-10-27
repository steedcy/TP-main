"""Record the missing-information manual override counterexample."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
ev = stage / "evidence"
override_file = ev / "TC-064-manual-missing-info-override-20261027T012833Z.json"
raw_file = ev / "TC-064-manual-device-commands-20261027T012753Z.txt"
retry_file = ev / "TC-064-retry-positive-fixture-20261027T012646Z.json"
cleanup_file = ev / "TC-064-manual-cleanup-followup-20261027T012901Z.json"
data = json.loads(override_file.read_text(encoding="utf-8"))
retry = json.loads(retry_file.read_text(encoding="utf-8"))
cleanup = json.loads(cleanup_file.read_text(encoding="utf-8"))
assert data["runtimeInput"] == retry["runtimeInput"] == cleanup["runtimeInput"] == "V1.5"
assert data["isolatedSchema"] == retry["isolatedSchema"] == cleanup["isolatedSchema"] == "tip_stage2_v14"
assert data["rawCommandFile"] == raw_file.name
assert retry["created"]["id"] == 71 and retry["before"]["status"] == "PENDING_MANUAL"
assert retry["fixtureModeRestored"] and retry["action"]["accepted"]
assert not retry["modelRequests"]
assert cleanup["task71"]["status"] == "MANUAL_TERMINATED"
assert len(cleanup["agents"]) == 6
assert all(a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE" and
           a["workStatus"] == "IDLE" and a["currentTaskId"] is None
           for a in cleanup["agents"])
for task_id in (69, 70, 71):
    row = data["tasks"][str(task_id)]
    task = row["task"]
    assert "服务类型及起终点尚待确认" in task["taskGoal"]
    assert task["goalParsingResult"]["origin"] is None
    assert task["goalParsingResult"]["destination"] is None
    assert len(task["missingInfoQuestions"]) == 3
    assert len(task["sceneParams"]["clarificationAnswers"]) == 3
    assert all("未确认" in answer for turn in task["sceneParams"]["clarificationAnswers"]
               for answer in turn["answers"].values())
    assert task["sceneParams"]["targetLocation"] == "F2_TEST_GATE"
    assert "轮椅" in task["sceneParams"]["assistanceType"]
    executed = [command for command in row["commands"]
                if command["commandType"] == "EXECUTE_CAPABILITY"]
    assert executed
    assert any(command["capabilityType"] == "CAP_INFO_DISPLAY" for command in executed)
    if task_id in (69, 70):
        assert any(command["capabilityType"] == "CAP_ESCORT" and
                   command["inputParams"]["targetLocation"] == "F2_TEST_GATE"
                   for command in executed)

base = "acceptance/stage3/evidence/"
refs = ";".join(base + f.name for f in (override_file, raw_file, retry_file, cleanup_file))
rules_file = stage / "rules.csv"
with rules_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rules = reader.fieldnames, list(reader)
for key in ("SRS_F010.R04", "SRS_F010.R10"):
    row = next(r for r in rules if r["ruleId"] == key)
    assert row["status"] == "P"
    row.update(status="F", verifiedBy=row["verifiedBy"] + ";TC-064.S2",
               evidence=row["evidence"] + ";" + refs, issue="DEF-S3-063")
with rules_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rules)

steps_file = stage / "steps.csv"
with steps_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, steps = reader.fieldnames, list(reader)
row = next(r for r in steps if r["stepId"] == "TC-064.S2")
assert row["status"] == "F" and "DEF-S3-062" in row["issue"]
row["actual"] += " 补查任务69/70/71：三轮补充仍无协助类型和起终点，人工转基线/重试却把模板默认轮椅说明及F2_TEST_GATE写入场景参数并下发显示/通知/陪同命令。"
row["evidence"] += ";" + refs
row["issue"] += ";DEF-S3-063"
with steps_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(steps)

issues_file = stage / "issues.csv"
with issues_file.open(encoding="utf-8-sig", newline="") as stream:
    assert "DEF-S3-063" not in {r["编号"] for r in csv.DictReader(stream)}
with issues_file.open("a", encoding="utf-8", newline="") as stream:
    csv.writer(stream, lineterminator="\n").writerow([
        "DEF-S3-063", "缺陷", "高", "TC-064.S2;TC-032.S2", "SRS_F010.R04;SRS_F010.R10", "待修复",
        "任务69/70/71三轮补充仍未提供特殊旅客协助类型、起点和终点，goalParsingResult起终点为null且三项missingInfoQuestions保留。运行操作员转基线或重试规划后系统将模板默认轮椅说明和F2_TEST_GATE写入sceneParams，三类校验报告PASS并实际下发显示/通知/陪同命令；任务69/70的CAP_ESCORT已下发到仿真代理。",
        refs,
        "待人工状态的转基线/重试必须先核对必需场景值，缺值时阻止规划和设备命令并要求明确补齐；模板默认值不得代替操作员未确认的旅客类型或起终点。修复后复测三类校验、监督、命令表和三场景正常闭环。"])

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
old = "281 条需求规则为 P 92、F 40、NT 11、未执行 138"
new = "281 条需求规则为 P 90、F 42、NT 11、未执行 138"
assert old in body
body = body.replace(old, new, 1)
heading = "## 已执行\n\n"
assert heading in body
note = ("- 人工处置缺失信息反例：任务69/70/71的目标仍未确认协助类型、起点、终点，"
        "三轮回答均为未确认，`goalParsingResult`起终点为null且三项待补问题仍在。"
        "转基线与重试却注入模板默认轮椅说明及`F2_TEST_GATE`，任务69/70均实际下发"
        "`CAP_INFO_DISPLAY/CAP_NOTIFICATION/CAP_ESCORT`，其中陪同指令指向默认终点；"
        "三类计划校验仍为PASS。任务71再次用受控规划夹具尝试正向重试，模型调用记录仍为空，"
        "走相同模板降级，`NT-S3-026`继续未补。新缺陷`DEF-S3-063`为高优先级；"
        "`SRS_F010.R04/R10`此前仅观察第三轮即时状态的P被本轮人工处置反例推翻，改F。"
        "原始任务字段、命令表、模式恢复和异步取消后六代理空闲证据见"
        "`evidence/TC-064-manual-missing-info-override-20261027T012833Z.json`、"
        "`evidence/TC-064-manual-device-commands-20261027T012753Z.txt`及"
        "`evidence/TC-064-manual-cleanup-followup-20261027T012901Z.json`。\n")
body = body.replace(heading, heading + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 09:23（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded DEF-S3-063; SRS_F010.R04/R10 P->F")
