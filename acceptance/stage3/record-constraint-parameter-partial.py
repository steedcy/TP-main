"""Keep TC-041.S2 unscored while recording two parameter-validation probes."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
names = ("TC-041-capability-validation-missing-input-20261028T012620Z.json",
         "TC-041-capability-validation-invalid-param-20261028T012808Z.json")
omitted, invalid = [json.loads((stage / "evidence" / n).read_text(encoding="utf-8")) for n in names]
assert omitted["runtimeInput"] == invalid["runtimeInput"] == "V1.5"
assert omitted["submitted"]["id"] == 92 and invalid["submitted"]["id"] == 93
assert "contentData" not in omitted["initialPlanSteps"][1]["inputParams"]
assert all(omitted["finished"]["plans"][0][k] == "PASS" for k in
           ("structureCheckResult", "capabilityCheckResult", "constraintCheckResult"))
assert invalid["initialPlanSteps"][1]["inputParams"]["displayDuration"] == 9999
candidate = invalid["finished"]["plans"][0]
assert candidate["source"] == "AUTONOMOUS"
assert candidate["structureCheckResult"] == candidate["capabilityCheckResult"] == "PASS"
assert candidate["constraintCheckResult"] == "FAIL"
assert any(x["stepSeq"] == 2 and x["reasonCode"] == "ERR_CAPABILITY_PARAMETER_INVALID"
           for x in candidate["validationErrors"])
assert candidate["frozenAt"] is None
assert all(x["restore"]["fixtureModeExact"] and x["restore"]["moonshotExitCode"] == 0 and
           x["restore"]["fixtureStopped"] and x["restore"]["sixOnlineIdle"]
           for x in (omitted, invalid))
with (stage / "steps.csv").open(encoding="utf-8-sig", newline="") as stream:
    row = next(x for x in csv.DictReader(stream) if x["stepId"] == "TC-041.S2")
assert row["status"] == "NOT_RUN"
progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
note = ("- TC-041.S2参数分支续测：任务92省略航显`contentData`，但该能力画像存在默认值，"
        "候选三类校验PASS；不能把此输入构造当作无默认值缺参。任务93将`displayDuration`设为9999，"
        "自主候选结构/能力PASS、约束FAIL，错误指向步骤2及`ERR_CAPABILITY_PARAMETER_INVALID`，"
        "原候选未冻结，转基线执行。资源冲突及运动安全字段等分支仍待测，整步保持未执行。"
        "两轮模型配置、原服务和六代理均恢复。见`evidence/TC-041-capability-validation-{missing-input,invalid-param}-*`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-28 09:30（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded TC-041.S2 parameter probes without changing its status")
