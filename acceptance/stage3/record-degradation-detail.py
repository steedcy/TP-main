"""Classify TC-048.S2 from live V1.5 operator UI and API evidence."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
ui_name = "TC-048-downgrade-detail-ui-20261027T054601Z.json"
api_name = "TC-048-downgrade-detail-api-20261027T054628Z.json"
source_name = "TC-050-baseline-failure-20261027T042130Z.json"
ui = json.loads((stage / "evidence" / ui_name).read_text(encoding="utf-8"))
api = json.loads((stage / "evidence" / api_name).read_text(encoding="utf-8"))
source = json.loads((stage / "evidence" / source_name).read_text(encoding="utf-8"))
assert ui["runtimeInput"] == api["runtimeInput"] == source["runtimeInput"] == "V1.5"
assert [item["taskId"] for item in ui["tasks"]] == [19, 83]
assert [item["taskId"] for item in api["tasks"]] == [19, 83]
assert source["request"]["taskGoal"] == source["task"]["taskGoal"]
for display, data in zip(ui["tasks"], api["tasks"]):
    assert data["task"]["taskGoal"] in display["header"]
    assert data["baselineTemplate"]["templateName"]
    assert data["baselineTemplate"]["templateVersion"] == "V1.3"
    baseline = next(plan for plan in data["plans"] if plan["source"] == "BASELINE_TEMPLATE")
    assert baseline["baselineTemplateId"] == data["baselineTemplate"]["id"] == 1
    assert baseline["frozenAt"] and [baseline[key] for key in
        ("structureCheckResult", "capabilityCheckResult", "constraintCheckResult")] == ["PASS"] * 3
    assert len(display["tabs"]) == 2 and not display["planCardLinks"]
    detail = "\n".join(version["detail"] for version in display["versions"])
    assert data["baselineTemplate"]["templateName"] not in detail
    assert data["baselineTemplate"]["templateVersion"] not in detail
    assert "匹配依据" not in detail
assert api["tasks"][0]["task"]["status"] == "COMPLETED"

refs = ";".join("acceptance/stage3/evidence/" + name for name in
                (ui_name, api_name, source_name,
                 ui["tasks"][0]["screenshot"], ui["tasks"][1]["screenshot"]))

steps_file = stage / "steps.csv"
with steps_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(item for item in rows if item["stepId"] == "TC-048.S2")
assert row["status"] == "NOT_RUN"
row.update(status="F", observedAt=datetime.now().strftime("%Y-%m-%d"),
           actual=("本轮Chrome运行操作员查看任务19与83降级详情，任务目标与API逐字一致；任务19展示原自主规划版本1和"
                   "基线版本2，任务83展示基线版本1与后续自主版本2。API关联启用模板1（V1.3），基线版本三类校验PASS且已冻结，"
                   "任务19继续分配并完成。页面计划区只有版本标签与三类结果，没有模板名称/版本的可跳转链接，也没有目标、"
                   "能力、五步限制的匹配依据；任务19时间线虽以文字提及模板名称与V1.3，仍无法跳转模板详情。故整步判F。"),
           evidence=refs, issue="DEF-S3-067")
with steps_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

issues_file = stage / "issues.csv"
with issues_file.open(encoding="utf-8-sig", newline="") as stream:
    assert "DEF-S3-067" not in {item["编号"] for item in csv.DictReader(stream)}
with issues_file.open("a", encoding="utf-8", newline="") as stream:
    csv.writer(stream, lineterminator="\n").writerow([
        "DEF-S3-067", "缺陷", "中", "TC-048.S2", "SRS_F015.R06", "待修复",
        "任务19/83的基线计划API均关联模板1（V1.3），原目标一致且三类校验PASS。Chrome任务详情计划区仅有版本标签和校验结果；无模板名称/版本详情链接，也无目标、能力、五步限制的匹配依据。任务19时间线仅以文字提及模板名称和版本。",
        refs,
        "在降级详情呈现原计划和模板名称/版本的明确关联入口，以及目标、能力、五步限制逐项匹配依据；回归两类降级任务和冻结执行路径。"])

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
old = "原 200 步：P 46、F 64、NT 19、未执行 71"
assert old in body
body = body.replace(old, "原 200 步：P 46、F 65、NT 19、未执行 70", 1)
note = ("- TC-048.S2：重启并核对同一V1.5隔离运行环境后，Chrome实测任务19与83的降级详情；"
        "原目标和两版计划可见，任务19基线版本冻结后四步完成。API模板1为V1.3且基线三类校验PASS；"
        "页面计划区缺模板名称/版本详情链接和目标、能力、五步限制匹配依据，记`DEF-S3-067`并判F。"
        "任务19时间线虽文字记模板名和版本，不等同于详情链接。TC-048.S1的运行中改模板冻结场景尚未执行。"
        "证据见`evidence/TC-048-downgrade-*`；服务恢复见`evidence/stage3-services-recovered-*`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 13:40（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded TC-048.S2 F and DEF-S3-067")
