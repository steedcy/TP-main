"""Map the live TC-052 overlap trace to assignment and acceptance rules."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
first_file = stage / "evidence/TC-052-concurrent-claim-20261027T040409Z.json"
follow_file = stage / "evidence/TC-052-concurrent-followup-20261027T040459Z.json"
first = json.loads(first_file.read_text(encoding="utf-8"))
follow = json.loads(follow_file.read_text(encoding="utf-8"))
assert first["first"]["commandsAtBusy"] == first["first"]["commandsAfterSecond"]
commands = first["first"]["commandsAtBusy"]
assert len(commands) == 2 and "|TASK_ACCEPT|ACCEPTED|" in commands[0]
assert "|EXECUTE_CAPABILITY|SENT|" in commands[1]
events = follow["tasks"][str(first["first"]["start"]["taskId"])]["events"]
selected = [e for e in events if e["eventType"] in
            ("AGENT_ASSIGNMENT_REQUESTED", "AGENT_ASSIGNED", "STEP_DISPATCHED")]
assert [e["eventType"] for e in selected] == [
    "AGENT_ASSIGNMENT_REQUESTED", "AGENT_ASSIGNED", "STEP_DISPATCHED"]
assert "候选排序" in selected[0]["detailSummary"]
assert "接受步骤1承接请求" in selected[1]["detailSummary"]
assert "指令" in selected[2]["detailSummary"]
assert selected[0]["occurredAt"] < selected[1]["occurredAt"] < selected[2]["occurredAt"]
refs = ";".join("acceptance/stage3/evidence/" + p.name for p in (first_file, follow_file))
target = stage / "rules.csv"
with target.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
for rule_id in ("SRS_F016.R06", "SRS_F016.R07"):
    row = next(r for r in rows if r["ruleId"] == rule_id)
    assert row["status"] == "NOT_RUN"
    row.update(status="P", verifiedBy="TC-052.S1", evidence=refs, issue="")
with target.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
assert "281 条需求规则为 P 94、F 44、NT 11、未执行 132" in body
body = body.replace("281 条需求规则为 P 94、F 44、NT 11、未执行 132",
                    "281 条需求规则为 P 96、F 44、NT 11、未执行 130", 1)
note = ("- `SRS_F016.R06/R07`：任务78的设备命令先有唯一`TASK_ACCEPT`承接，"
        "再有`EXECUTE_CAPABILITY`业务下发；三条真实任务事件按分配请求、接受承接、步骤下发先后记录，"
        "含步骤和代理、响应摘要，故这两条窄范围规则判P。TC-051.S2仍须另测候选响应时间、"
        "设备状态与页面，不由此推断整步通过。证据沿用`evidence/TC-052-concurrent-*`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 12:05（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded SRS_F016.R06/R07 P; TC-051.S2 unchanged")
