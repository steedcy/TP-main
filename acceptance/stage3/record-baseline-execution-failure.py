"""Record live baseline failure and preserve two earlier inconclusive model attempts."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
ev = stage / "evidence"
early = [ev / "TC-050-baseline-failure-20261027T041502Z.json",
         ev / "TC-050-baseline-failure-20261027T041735Z.json"]
profile_file = ev / "TC-050-controlled-profile-20261027T042057Z.json"
task_file = ev / "TC-050-baseline-failure-20261027T042130Z.json"
profile = json.loads(profile_file.read_text(encoding="utf-8"))
task = json.loads(task_file.read_text(encoding="utf-8"))
assert [json.loads(p.read_text(encoding="utf-8"))["task"]["status"] for p in early] == [
    "PLANNING", "PENDING_MANUAL"]
assert profile["runtimeInput"] == task["runtimeInput"] == "V1.5"
assert profile["isolatedSchema"] == task["isolatedSchema"] == "tip_stage2_v14"
assert [(r["phase"], r["mode"]) for r in profile["newModelRequests"]] == [
    ("goal", "success"), ("planning", "malformed"), ("replanning", "success")]
assert profile["restore"]["moonshotExitCode"] == 0
assert profile["restore"]["fixtureStopped"] and profile["restore"]["fixtureModeExact"]
assert profile["restore"]["backendHealth"]["status"] == "UP"
assert len(profile["restore"]["agents"]) == 6 and all(a["onlineStatus"] == "ONLINE" and
    a["workStatus"] == "IDLE" and a["currentTaskId"] is None
    for a in profile["restore"]["agents"])
assert task["task"]["id"] == 83 and task["task"]["status"] == "PENDING_MANUAL"
assert task["task"]["replanUsed"] is True
assert task["task"]["replanningReason"].startswith("CAPABILITY_GAP:")
assert task["task"]["failureReason"].startswith("局部重新规划失败")
assert [p["source"] for p in task["plans"]] == ["BASELINE_TEMPLATE", "AUTONOMOUS"]
assert all(task["plans"][0][k] == "PASS" for k in
           ("structureCheckResult", "capabilityCheckResult", "constraintCheckResult"))
assert task["plans"][1]["constraintCheckResult"] == "FAIL"
types = [e["eventType"] for e in task["events"]]
assert types.count("STEP_RETRY_DISPATCHED") == 2
assert types.count("STEP_FAILED") == 2
assert types.count("EXCEPTION_DETECTED") == 3
assert types.index("EXCEPTION_RECOVERY_FAILED") < types.index("REPLANNING_TRIGGERED") < types.index("REPLAN_FAILED")
assert types[-1] == "EXCEPTION_RECOVERED"
assert task["restore"]["fixtureExact"] and task["restore"]["cleanup"] == "MANUAL_TERMINATED"
assert all(task["restore"][c]["scenarioResult"] == "SUCCESS" for c in
           ("SIM_F2_ROBOT", "SIM_F2_ROBOT_B"))
refs = ";".join("acceptance/stage3/evidence/" + p.name for p in
                (*early, profile_file, task_file))

steps_file = stage / "steps.csv"
with steps_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, steps = reader.fieldnames, list(reader)
for step_id in ("TC-050.S1", "TC-059.S2"):
    row = next(r for r in steps if r["stepId"] == step_id)
    assert row["status"] == "NOT_RUN"
    row.update(status="F", observedAt=datetime.now().strftime("%Y-%m-%d"),
               actual=("受控本地规划服务明确返回malformed，任务83合格基线V1在导航步骤先后两台机器人各重试一次均失败；"
                       "恢复失败后未直接待人工，而触发局部重规划、消耗一次机会并生成自主V2；"
                       "V2校验失败后才待人工。末尾又记EXCEPTION_RECOVERED，与实际失败相矛盾。"
                       "先前81/82在Moonshot模式未进入该分支，不计为通过。"),
               evidence=refs, issue="DEF-S3-065;DEF-S3-066")
with steps_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(steps)

rules_file = stage / "rules.csv"
with rules_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rules = reader.fieldnames, list(reader)
row = next(r for r in rules if r["ruleId"] == "SRS_F015.R08")
assert row["status"] == "NOT_RUN"
row.update(status="F", verifiedBy="TC-050.S1;TC-059.S2", evidence=refs,
           issue="DEF-S3-065;DEF-S3-066")
with rules_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rules)

issues_file = stage / "issues.csv"
with issues_file.open(encoding="utf-8-sig", newline="") as stream:
    seen = {r["编号"] for r in csv.DictReader(stream)}
assert "DEF-S3-065" not in seen and "DEF-S3-066" not in seen
with issues_file.open("a", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["DEF-S3-065", "缺陷", "高", "TC-050.S1;TC-059.S2", "SRS_F015.R08",
        "待修复", "受控故障下任务83自动基线V1首步两台机器人执行失败；恢复失败后仍触发局部重规划，消耗一次机会并生成自主V2，直到V2校验失败才待人工，违反基线执行失败直接待人工的异常路径。",
        refs, "按基线来源/降级执行标志判断失败分支，恢复穷尽后直接待人工；回归自主任务重规划、基线任务失败及邻接异常处理。"])
    writer.writerow(["DEF-S3-066", "缺陷", "中", "TC-050.S1;TC-059.S2", "SRS_F015.R08;SRS_F018.R09",
        "待修复", "任务83时间线在EXCEPTION_RECOVERY_FAILED、REPLANNING_TRIGGERED、REPLAN_FAILED后仍追加EXCEPTION_RECOVERED；异常列表将第二个STEP_FAILED的候选切换记SUCCESS，最终任务却待人工，恢复结果与实际路径矛盾。",
        refs, "待设备承接与执行结果确认后再定恢复成功；避免嵌套异常处理后追加虚假的恢复事件并核对异常列表结论。"])

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
assert "原 200 步：P 46、F 62、NT 19、未执行 73" in body
assert "281 条需求规则为 P 97、F 44、NT 11、未执行 129" in body
body = body.replace("原 200 步：P 46、F 62、NT 19、未执行 73",
                    "原 200 步：P 46、F 64、NT 19、未执行 71", 1)
body = body.replace("281 条需求规则为 P 97、F 44、NT 11、未执行 129",
                    "281 条需求规则为 P 97、F 45、NT 11、未执行 128", 1)
note = ("- TC-050.S1/TC-059.S2与`SRS_F015.R08`：先前Moonshot模式任务81/82没有形成基线执行分支；"
        "改用同一V1.5隔离JAR的受控本地规划故障服务，实际请求日志为目标成功、规划malformed、重规划成功。"
        "任务83自动基线V1首步两台机器人各重试后均失败，系统仍发起局部重规划、生成自主V2且耗尽一次机会，"
        "V2校验失败才待人工，违反基线执行失败直接人工分支，记高危`DEF-S3-065`。"
        "时间线末尾虚报`EXCEPTION_RECOVERED`，记`DEF-S3-066`。三项判F。故障服务、机器人场景及"
        "Moonshot配置均已恢复，任务83取证后终止，六代理在线空闲。见`evidence/TC-050-*`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 12:12（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded TC-050.S1/TC-059.S2 F; SRS_F015.R08 F; DEF-S3-065/066")
