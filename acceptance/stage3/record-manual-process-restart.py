"""Record TC-094 and the process recovery rule from the live restart trace."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
ev = stage / "evidence"
restart_file = ev / "TC-094-manual-restart-20261027T041012Z.json"
service_file = ev / "stage3-services-recovered-20261027T041048Z.json"
core_file = ev / "TC-094-postrestart-core-20261027T041145Z.json"
pages_file = ev / "TC-094-postrestart-pages.json"
restart, service, core, pages = [json.loads(p.read_text(encoding="utf-8"))
                                 for p in (restart_file, service_file, core_file, pages_file)]
assert restart["runtimeInput"] == core["runtimeInput"] == pages["runtimeInput"] == "V1.5"
assert restart["isolatedSchema"] == core["isolatedSchema"] == "tip_stage2_v14"
assert restart["stop"]["verified"] and restart["stop"]["healthUnavailableAfterStop"]
assert restart["restart"]["exitCode"] == 0
assert restart["restart"]["elapsedSecondsToServicesReady"] < 30 * 60
assert restart["after"]["persistedExactly"]
assert restart["after"]["backendHealth"]["status"] == "UP"
assert restart["after"]["frontendHttpStatus"] == 200
assert service["sixOnlineIdle"]
assert core["task"]["id"] == 80 and core["task"]["status"] == "COMPLETED"
assert len(core["assignments"]) == 4 and all(a["stepStatus"] == "COMPLETED"
                                              for a in core["assignments"])
assert core["restore"]["fixtureExact"]
assert len(core["restore"]["agents"]) == 6 and all(a["workStatus"] == "IDLE"
                                                   for a in core["restore"]["agents"])
assert pages["pages"]["overview"]["taskMetricVisible"]
assert pages["pages"]["task"]["route"] == "/tasks/80"
assert "已完成" in pages["pages"]["task"]["header"]
assert pages["pages"]["task"]["timelineItemCount"] >= 20
assert all(status == 200 for status in (r["status"] for r in pages["requests"]))
refs = ";".join("acceptance/stage3/evidence/" + p.name for p in
                (restart_file, service_file, core_file, pages_file))
refs += ";acceptance/stage3/evidence/TC-094-postrestart-overview.png"
refs += ";acceptance/stage3/evidence/TC-094-postrestart-task.png"

steps_file = stage / "steps.csv"
with steps_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, steps = reader.fieldnames, list(reader)
for step_id in ("TC-094.S1", "TC-094.S2"):
    row = next(r for r in steps if r["stepId"] == step_id)
    assert row["status"] == "NOT_RUN"
    row.update(status="P", observedAt=datetime.now().strftime("%Y-%m-%d"),
               actual=("经监听端口和命令行确认PID9500为阶段3隔离后端后，人工停止进程，健康检查确实不可用；"
                       "人工执行本地重启脚本后36.954秒服务与六代理恢复，远低于30分钟。"
                       if step_id.endswith("S1") else
                       "重启前后任务19/73行及事件哈希完全一致，任务73仍已完成；"
                       "重启后新建行李核心任务80，四步骤全完成；Chrome总览与任务详情返回正常，"
                       "详情显示已完成及28条事件。"),
               evidence=refs, issue="")
with steps_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(steps)

rules_file = stage / "rules.csv"
with rules_file.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rules = reader.fieldnames, list(reader)
row = next(r for r in rules if r["ruleId"] == "SRS_NF017.R01")
assert row["status"] == "NOT_RUN"
row.update(status="P", verifiedBy="TC-094.S1;TC-094.S2", evidence=refs, issue="")
with rules_file.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rules)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
assert "原 200 步：P 44、F 62、NT 19、未执行 75" in body
assert "281 条需求规则为 P 96、F 44、NT 11、未执行 130" in body
body = body.replace("原 200 步：P 44、F 62、NT 19、未执行 75",
                    "原 200 步：P 46、F 62、NT 19、未执行 73", 1)
body = body.replace("281 条需求规则为 P 96、F 44、NT 11、未执行 130",
                    "281 条需求规则为 P 97、F 44、NT 11、未执行 129", 1)
note = ("- TC-094.S1/S2与`SRS_NF017.R01`：本轮确认阶段3后端PID后人工停止，"
        "健康探针不可用；人工重启脚本恢复隔离库后端、前端及六代理耗时36.954秒。"
        "重启前后任务19/73与事件哈希一致；新提交行李核心任务80四步完成，Chrome总览与任务详情可用，"
        "页面见28条事件。两步与规则判P；这不代替连续八小时或高可用测试。"
        "原始证据见`evidence/TC-094-*`及同轮恢复记录。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 12:08（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded TC-094.S1/S2 P and SRS_NF017.R01 P")
