"""Record retry impact P and missing manual status event F from task 83."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
first = stage / "evidence/TC-050-baseline-failure-20261027T042130Z.json"
follow = stage / "evidence/TC-050-failed-command-trace-20261027T042748Z.json"
run = json.loads(first.read_text(encoding="utf-8"))
ev = json.loads(follow.read_text(encoding="utf-8"))
assert run["task"]["status"] == ev["beforeCleanupTaskStatus"] == "PENDING_MANUAL"
assert len(ev["commands"]) == 6
execution = [r for r in ev["commands"] if r[2] == "EXECUTE_CAPABILITY"]
assert len(execution) == 4 and all(r[4] == "FAILED" for r in execution)
assert execution[0][0] == execution[1][0] != execution[2][0] == execution[3][0]
assert [r[3] for r in execution] == ["0", "1", "0", "1"]
types = ev["beforeCleanupEventTypes"]
assert types.count("STEP_FAILED") == 2 and types.count("EXCEPTION_DETECTED") == 3
assert "EXCEPTION_RECOVERY_FAILED" in types and "REPLANNING_TRIGGERED" in types
assert "TASK_PENDING_MANUAL" not in types and "TASK_MANUAL_REQUIRED" not in types
assert types[-1] == "EXCEPTION_RECOVERED"
assert ev["afterCleanupTaskStatus"] == "MANUAL_TERMINATED"
refs = ";".join("acceptance/stage3/evidence/" + p.name for p in (first, follow))

rules_file = stage / "rules.csv"
with rules_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(r for r in rows if r["ruleId"] == "SRS_F017.R03")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-050.S1", evidence=refs, issue="")
row = next(r for r in rows if r["ruleId"] == "SRS_F017.R10")
assert row["status"] == "NOT_RUN"
row.update(status="F", verifiedBy="TC-050.S1", evidence=refs, issue="DEF-S3-066")
with rules_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

issues_file = stage / "issues.csv"
with issues_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, issues = reader.fieldnames, list(reader)
issue = next(r for r in issues if r["编号"] == "DEF-S3-066")
assert "任务83时间线" in issue["事实"]
issue["事实"] += " 另在任务API已为PENDING_MANUAL时，取证时间线无TASK_PENDING_MANUAL/TASK_MANUAL_REQUIRED状态转移事件。"
issue["证据"] += ";acceptance/stage3/evidence/" + follow.name
issue["阶段4动作"] += " 补全待人工状态转换事件并回归全状态流转时间线。"
with issues_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(issues)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
assert "281 条需求规则为 P 100、F 45、NT 11、未执行 125" in body
body = body.replace("281 条需求规则为 P 100、F 45、NT 11、未执行 125",
                    "281 条需求规则为 P 101、F 46、NT 11、未执行 123", 1)
note = ("- `SRS_F017.R03/R10`：任务83两台机器人各有同指令号attempt 0/1的失败反馈，"
        "重试后均出现STEP_FAILED及异常影响判断，故R03判P。任务已为PENDING_MANUAL时，"
        "时间线末尾为EXCEPTION_RECOVERED，没有待人工状态转移事件；R10要求完整状态留痕，判F并补证"
        "`DEF-S3-066`。指令号幂等的全范围效果尚未验证，`SRS_F017.R02`维持未执行。"
        "证据见`evidence/TC-050-failed-command-trace-20261027T042748Z.json`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 12:26（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded SRS_F017.R03 P, R10 F; expanded DEF-S3-066")
