"""Record TC-041.S2 motion-safety branch without scoring its other branches."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
name = "TC-041-capability-validation-motion-safety-20261028T013705Z.json"
ev = json.loads((stage / "evidence" / name).read_text(encoding="utf-8"))
assert ev["runtimeInput"] == "V1.5" and ev["submitted"]["id"] == 95
assert ev["initialPlanSteps"][3]["inputParams"]["speed"] == 2
candidate = ev["finished"]["plans"][0]
assert candidate["source"] == "AUTONOMOUS"
assert candidate["structureCheckResult"] == candidate["capabilityCheckResult"] == "PASS"
assert candidate["constraintCheckResult"] == "FAIL" and candidate["frozenAt"] is None
assert any(x["stepSeq"] == 4 and x["reasonCode"] == "ERR_MOTION_SAFETY_FIELD"
           for x in candidate["validationErrors"])
assert not any(x["eventType"] == "SUPERVISION_JUDGED" for x in ev["finished"]["events"])
assert ev["finished"]["plans"][1]["source"] == "BASELINE_TEMPLATE"
assert ev["restore"]["fixtureModeExact"] and ev["restore"]["moonshotExitCode"] == 0
assert ev["restore"]["fixtureStopped"] and ev["restore"]["sixOnlineIdle"]
with (stage / "steps.csv").open(encoding="utf-8-sig", newline="") as stream:
    row = next(x for x in csv.DictReader(stream) if x["stepId"] == "TC-041.S2")
assert row["status"] == "NOT_RUN"
progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
note = ("- TC-041.S2运动安全字段分支：同一V1.5正式候选任务95的空间引导输入注入`speed=2`，"
        "结构/能力PASS，约束FAIL，步骤4同时给出`ERR_MOTION_SAFETY_FIELD`和参数无效原因码；"
        "该自主版本未冻结、未进入监督，另建基线版本执行。任务93的超界时长也被约束拦截；"
        "资源冲突、完成条件等其他分支仍未覆盖，整步及整条约束规则保持未执行。"
        "模型模式、服务和六代理恢复，见`evidence/TC-041-capability-validation-motion-safety-*`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-28 09:35（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded TC-041.S2 motion-safety branch; full step remains NOT_RUN")
