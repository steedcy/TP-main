"""Record the V1.5 preset-vs-required-channel conflict without passing TC-054.S1."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
first_name = "TC-054-formal-ack-order-20261027T060139Z.json"
second_name = "TC-054-formal-ack-order-corrected-20261027T060425Z.json"
contrast_name = "TC-054-oversize-capability-contradiction-20261027T060755Z.json"
first, second, contrast = [json.loads((stage / "evidence" / name).read_text(encoding="utf-8"))
                           for name in (first_name, second_name, contrast_name)]
assert first["runtimeInput"] == second["runtimeInput"] == contrast["runtimeInput"] == "V1.5"
assert first["submitted"]["id"] == 86 and second["submitted"]["id"] == 87
assert first["finished"]["task"]["status"] == second["finished"]["task"]["status"] == "COMPLETED"
assert first["firstReceipt"]["task"]["status"] == second["firstReceipt"]["task"]["status"] == "EXECUTING"
assert first["finished"]["plans"][0]["source"] == second["finished"]["plans"][0]["source"] == "AUTONOMOUS"
assert first["finished"]["plans"][0]["constraintCheckResult"] == "FAIL"
assert second["finished"]["plans"][0]["constraintCheckResult"] == "FAIL"
assert all(run["finished"]["plans"][1]["source"] == "BASELINE_TEMPLATE" and
           run["finished"]["plans"][1]["frozenAt"] for run in (first, second))
allowed = contrast["definition"]["availableCapabilityTypes"]
assert "CAP_NOTIFICATION" in allowed and "CAP_INFO_DISPLAY" not in allowed
assert any(c["capabilityType"] == "CAP_INFO_DISPLAY" and c["capabilityStatus"] == "ENABLED"
           for c in contrast["displayCapabilities"])
errors = {key: value["plans"][0]["validationErrors"] for key, value in contrast["tasks"].items()}
assert errors["19"][0]["reasonCode"] == "ERR_REQUIRED_CHANNEL_MISSING"
assert errors["86"][0]["reasonCode"] == errors["87"][0]["reasonCode"] == "ERR_CAPABILITY_NOT_IN_TASK_DEFINITION"
assert all(run["restore"]["fixtureModeExact"] and run["restore"]["moonshotExitCode"] == 0 and
           run["restore"]["fixtureStopped"] and run["restore"]["sixOnlineIdle"]
           for run in (first, second))
refs = ";".join("acceptance/stage3/evidence/" + name for name in
                (first_name, second_name, contrast_name))

issues_file = stage / "issues.csv"
with issues_file.open(encoding="utf-8-sig", newline="") as stream:
    assert "DEF-S3-069" not in {row["编号"] for row in csv.DictReader(stream)}
with issues_file.open("a", encoding="utf-8", newline="") as stream:
    csv.writer(stream, lineterminator="\n").writerow([
        "DEF-S3-069", "缺陷", "高", "TC-054.S1;TC-072.S2", "SRS_F013.R03;SRS_F024.R04", "待修复",
        "预置超规行李任务定义允许CAP_NOTIFICATION却不允许CAP_INFO_DISPLAY。V1.5任务19自主候选使用CAP_NOTIFICATION被判缺少SMART_DISPLAY必需的CAP_INFO_DISPLAY；本轮正式任务86/87改用已启用的CAP_INFO_DISPLAY，又均被约束校验判ERR_CAPABILITY_NOT_IN_TASK_DEFINITION，转基线降级。两种配置无法形成该核心场景三类校验全部通过的自主计划。",
        refs,
        "校准超规行李预置任务定义允许能力与核心场景智慧航显必需渠道，确保可生成三类校验通过、接受监督的自主计划；回归候选校验、降级、TC-054正式多步执行及TC-072超规闭环。"])

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
note = ("- 正式多步执行前置条件与`DEF-S3-069`：同一V1.5隔离JAR上，受控模型只提供计划内容，"
        "任务86/87实际走后端目标解析、三类校验、降级、设备承接与四步执行，两次最终COMPLETED。"
        "但超规预置定义允许CAP_NOTIFICATION而不允许已启用的CAP_INFO_DISPLAY；用前者的任务19被判缺智慧航显必需能力，"
        "改用后者的任务86/87又被判超出任务定义，均不能达到自主计划校验及监督通过的TC-054.S1前置条件。"
        "故该整步保持未执行，不把基线降级完成当作正式监督通过路径；高危缺陷待阶段4修复。"
        "两轮模型配置原文恢复、Moonshot服务恢复、夹具停止、六代理空闲。见`evidence/TC-054-formal-ack-order-*`"
        "及`evidence/TC-054-oversize-capability-contradiction-*`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 13:58（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded DEF-S3-069; TC-054.S1 remains NOT_RUN")
