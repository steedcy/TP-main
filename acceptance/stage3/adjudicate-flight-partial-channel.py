"""Withdraw DEF-S3-070 after checking SRS 5.6.5 alternate path 5a."""
import csv
import hashlib
import io
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

stage = Path(__file__).resolve().parent
root = stage.parents[1]
spec_path = root / "document/20260904-智慧机场人工智能集群协同服务平台-需求规格说明书-V1.4.md"
spec_text = spec_path.read_text(encoding="utf-8")
clause = "5a、部分渠道设备不可用时，按可用渠道执行并在结果中标注未覆盖渠道。"
assert clause in spec_text
case = json.loads((stage / "evidence/TC-041-no-candidate-validation-followup-20261027T063555Z.json")
                  .read_text(encoding="utf-8"))
assert case["task"]["taskFamily"] == "FLIGHT_CHANGE_RESPONSE"
assert [x["stepStatus"] for x in case["assignments"]] == [
    "SKIPPED", "SKIPPED", "COMPLETED", "COMPLETED"]
assert sum(x["eventType"] == "FLIGHT_CHANNEL_UNCOVERED" for x in case["events"]) == 2
assert case["task"]["status"] == "COMPLETED"
out = stage / "evidence/TC-041-flight-partial-channel-adjudication.json"
out.write_text(json.dumps({
    "observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
    "testTaskId": 91, "taskFamily": case["task"]["taskFamily"],
    "specification": "SRS V1.4 section 5.6.5 alternate path 5a",
    "specificationPath": "document/" + spec_path.name,
    "specificationSha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
    "exactClause": clause,
    "adjudication": "任务91是航班变更部分渠道不可用分支；跳过并标记未覆盖渠道属于明确允许行为。该样本不能用于TC-041.S1通用无候选硬闸门，也不能推翻SRS_F017.R09先前正向验证。",
    "originalEvidence": "acceptance/stage3/evidence/TC-041-no-candidate-validation-followup-20261027T063555Z.json"
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def previous_rows(name, key):
    raw = subprocess.check_output(["git", "show", "V1.102:acceptance/stage3/" + name],
                                  cwd=root, text=True, encoding="utf-8")
    return {x[key]: x for x in csv.DictReader(io.StringIO(raw))}

for name, key, identifiers in (("steps.csv", "stepId", ["TC-041.S1"]),
                               ("rules.csv", "ruleId", ["SRS_F013.R02", "SRS_F013.R04", "SRS_F017.R09"])):
    target = stage / name
    with target.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    old = previous_rows(name, key)
    for identifier in identifiers:
        current = next(x for x in rows if x[key] == identifier)
        assert current["status"] == "F" and current["issue"] == "DEF-S3-070"
        current.update(old[identifier])
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

issues = stage / "issues.csv"
with issues.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
item = next(x for x in rows if x["编号"] == "DEF-S3-070")
assert item["状态"] == "待修复"
item["状态"] = "误报撤销"
item["事实"] += " 复核SRS V1.4第5.6.5节备选路径5a后撤销：航班变更允许部分渠道不可用时仅执行可用渠道并标记未覆盖；任务91不构成所述缺陷。"
item["证据"] += ";acceptance/stage3/evidence/" + out.name
item["阶段4动作"] = "无需按此误报修复；改用不适用5.6.5备选路径5a的任务族重测TC-041无候选硬闸门。"
with issues.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
assert "原 200 步：P 48、F 68、NT 19、未执行 65" in body
assert "281 条需求规则为 P 105、F 54、NT 11、未执行 111" in body
body = body.replace("原 200 步：P 48、F 68、NT 19、未执行 65",
                    "原 200 步：P 48、F 67、NT 19、未执行 66", 1)
body = body.replace("281 条需求规则为 P 105、F 54、NT 11、未执行 111",
                    "281 条需求规则为 P 106、F 51、NT 11、未执行 113", 1)
lines = body.splitlines()
assert lines[6].startswith("- TC-041.S1及`DEF-S3-070`")
lines[6] = ("- 纠正V1.103误报`DEF-S3-070`：固定SRS第5.6.5节备选路径5a明确允许航班变更部分渠道不可用时"
            "执行其余渠道并标注未覆盖。任务91正符合该例外，原始候选、上下文和执行证据保留，缺陷标为误报撤销。"
            "TC-041.S1与`SRS_F013.R02/R04`恢复未执行，`SRS_F017.R09`恢复此前正向样本的P；"
            "须用不适用该场景例外的任务族重新验证无候选硬闸门。见`evidence/TC-041-flight-partial-channel-adjudication.json`。")
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-28 09:23（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("withdrawn DEF-S3-070; restored one step and three rules")
