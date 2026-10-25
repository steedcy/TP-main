"""Record only the TC-031/068 and AC-001 outcomes supported by fresh evidence."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
evidence = stage / "evidence"
definition = json.loads((evidence / "TC-068-dynamic-definition-api.json").read_text(encoding="utf-8"))
ui = json.loads((evidence / "TC-031-068-dynamic-ui.json").read_text(encoding="utf-8"))
submit = json.loads((evidence / "TC-031-068-dynamic-submit.json").read_text(encoding="utf-8"))
disable = json.loads((evidence / "TC-068-dynamic-disable.json").read_text(encoding="utf-8"))
disabled_ui = json.loads((evidence / "TC-068-disabled-ui.json").read_text(encoding="utf-8"))
constraint = json.loads((evidence / "TC-068-empty-constraint.json").read_text(encoding="utf-8"))
assert ui["submit"]["definitionSelectable"] and not ui["submit"]["sampleLocationLabelVisible"]
assert ui["submit"]["sceneParamInputCount"] == 0
assert submit["observations"]["afterMissingMaxTaskId"] > submit["observations"]["beforeMaxTaskId"]
assert constraint["observations"]["created"]["constraintDescription"] == ""
assert disable["observations"]["detailAfterDisable"]["definitionStatus"] == "DISABLED"
assert "newSubmitAfterDisableError" in disable["observations"]
assert disabled_ui["observations"]["disabledInSubmitOptions"] == 0
assert disabled_ui["observations"]["inHistoricalFilter"] == 1
assert [x.split("|")[0] for x in disable["observations"]["logsAfterDisable"]] == [
    "TASK_DEFINITION_CREATE", "TASK_DEFINITION_UPDATE", "TASK_DEFINITION_DISABLE"]
day = datetime.now().astimezone().date().isoformat()

def ref(*names):
    return ";".join(f"acceptance/stage3/evidence/{name}" for name in names)

def update_csv(name, key, changes):
    path = stage / name
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    for row in rows:
        if row[key] in changes:
            row.update(changes[row[key]])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

definition_ref = ref("TC-068-dynamic-definition-api.json", "TC-068-empty-constraint.json",
                     "TC-068-definition-edit.png")
form_ref = ref("TC-031-068-dynamic-ui.json", "TC-031-068-submit-dynamic.png",
               "TC-031-068-dynamic-submit.json")
life_ref = ref("TC-068-dynamic-disable.json", "TC-068-disabled-ui.json",
               "TC-068-disabled-submit.png", "TC-068-disabled-history-filter.png")
update_csv("steps.csv", "stepId", {
    "TC-031.S1": {"status": "F", "observedAt": day,
        "actual": "扩展定义可选且空目标按钮禁用；定义的必填sampleLocation未随任务族显示，缺参提交创建任务33后才追问；仅测空/501位，1/500边界未全测",
        "evidence": form_ref, "issue": "DEF-S3-028;DEF-S3-029"},
    "TC-068.S1": {"status": "F", "observedAt": day,
        "actual": "扩展定义创建/编辑及名称等非法输入拒绝；空约束仍可创建，与约束必填不符；一次性空约束定义已删除",
        "evidence": definition_ref, "issue": "DEF-S3-030"},
    "TC-068.S2": {"status": "F", "observedAt": day,
        "actual": "新定义可选但无动态参数；缺必填输入仍建任务33；停用后提交不可选且新提交400，旧任务可查，三类操作日志齐全；计划≤5步与完成判定未测",
        "evidence": form_ref + ";" + life_ref, "issue": "DEF-S3-028;DEF-S3-029"},
})
update_csv("ac.csv", "acId", {
    "AC-001": {"status": "F", "observedAt": day,
        "actual": "参数名/类型/必填/说明在定义编辑页存在；提交页不展示sampleLocation，缺参仍创建任务；停用与历史保留通过，类型校验和实际路径未完整测",
        "evidence": definition_ref + ";" + form_ref + ";" + life_ref,
        "issue": "DEF-S3-028;DEF-S3-029;DEF-S3-030"},
})
update_csv("rules.csv", "ruleId", {
    "SRS_F010.R01": {"status": "F", "verifiedBy": "TC-031.S1", "evidence": form_ref,
                      "issue": "DEF-S3-028"},
    "SRS_F022.R02": {"status": "P", "verifiedBy": "TC-068.S1", "evidence": definition_ref,
                      "issue": ""},
    "SRS_F022.R03": {"status": "F", "verifiedBy": "TC-068.S1", "evidence": definition_ref,
                      "issue": "DEF-S3-030"},
    "SRS_F022.R08": {"status": "P", "verifiedBy": "TC-068.S2", "evidence": life_ref,
                      "issue": ""},
})
issues = stage / "issues.csv"
with issues.open(encoding="utf-8-sig", newline="") as handle:
    reader = csv.DictReader(handle)
    fields = reader.fieldnames
    existing = {row["编号"] for row in reader}
new = [
    ["DEF-S3-028", "缺陷", "高", "TC-031.S1;TC-068.S2;AC-001", "SRS_F010.R01;SRS_F022.R03", "待修复",
     "扩展定义必填sampleLocation在配置页存在，提交页选中后无该输入项", form_ref,
     "提交页按已启用任务定义动态渲染场景参数，校验类型和必填，完整重跑TC-031/068及AC-001"],
    ["DEF-S3-029", "缺陷", "高", "TC-031.S1;TC-068.S2;AC-001", "SRS_F010.R01;SRS_F022.R03", "待修复",
     "缺少必填sampleLocation的POST /tasks返回200并创建任务33，随后目标理解才追问", ref("TC-031-068-dynamic-submit.json"),
     "任务提交前按定义校验场景参数必填和类型，非法请求不建任务不调模型；复测边界"],
    ["DEF-S3-030", "缺陷", "中", "TC-068.S1;AC-001", "SRS_F022.R03", "待修复",
     "POST /task-definitions的constraintDescription为空仍保存扩展定义，复测定义已删除", ref("TC-068-empty-constraint.json"),
     "定义新增和编辑均校验约束必填，复测预置与扩展定义边界"],
]
with issues.open("a", encoding="utf-8", newline="") as handle:
    writer = csv.writer(handle, lineterminator="\n")
    for row in new:
        assert row[0] not in existing
        writer.writerow(row)
print("recorded TC-031.S1, TC-068.S1/S2, AC-001, four rules, three defects")
