"""Record TC-012.S1 and occupied-agent recovery rule from this run only."""
import csv
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

stage = Path(__file__).resolve().parent
root = stage.parents[1]
runs = list((stage / "evidence").glob("TC-012-disable-busy-20*.json"))
assert len(runs) == 1
run = json.loads(runs[0].read_text(encoding="utf-8"))
task_id = run["dryRunStarted"]["taskId"]
assert run["atBusy"]["currentTaskId"] == task_id
assert not run["cancelConfirmation"]["accepted"]
assert run["afterCancelConfirmation"]["agentStatus"] == "ENABLED"
assert run["afterCancelConfirmation"]["currentTaskId"] == task_id
assert run["afterConfirmedDisable"]["agentStatus"] == "DISABLED"
assert run["afterConfirmedDisable"]["workStatus"] == "BUSY"
assert run["afterConfirmedDisable"]["currentTaskId"] == task_id
assert [e["eventType"] for e in run["eventsAfterConfirmedDisable"]][-1] == "AGENT_DISABLED_WITH_OCCUPATION"
assert run["restore"]["templateStatus"] == "DISABLED"
assert run["restore"]["delayMs"] == 1000

spec = importlib.util.spec_from_file_location("local", root / "scripts/local-test-environment.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
config = local.API("配置管理员")
agents = [a for a in config("/device-agents?page=1&size=100")["content"]
          if a["deviceCode"].startswith("SIM_F2_")]
assert len(agents) == 6 and all(
    a["agentStatus"] == "ENABLED" and a["onlineStatus"] == "ONLINE"
    and a["workStatus"] == "IDLE" and a["currentTaskId"] is None for a in agents)
followup = stage / "evidence" / (
    "TC-012-disable-busy-restored-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
followup.write_text(json.dumps({
    "observedAt": datetime.now(timezone.utc).isoformat(), "runtimeInput": "V1.5",
    "isolatedSchema": "tip_stage2_v14", "taskId": task_id,
    "finalAgents": [{k: a.get(k) for k in (
        "deviceCode", "agentId", "agentStatus", "onlineStatus", "workStatus", "currentTaskId")}
        for a in agents],
    "templateStatus": config(f"/baseline-templates/{run['templateId']}")["templateStatus"]
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
refs = ";".join("acceptance/stage3/evidence/" + p.name for p in (runs[0], followup))

def update(path, key, value, change):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    row = next(r for r in rows if r[key] == value)
    assert row["status"] == "NOT_RUN"
    change(row)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

today = datetime.now().astimezone().date().isoformat()
update(stage / "steps.csv", "stepId", "TC-012.S1", lambda row: row.update(
    status="F", observedAt=today,
    actual="任务63试运行真实占用代理；取消二次确认返回400且代理保持启用忙碌。确认停用后代理立即DISABLED/OFFLINE，但仍BUSY、占用任务号63；时间线只增加AGENT_DISABLED_WITH_OCCUPATION待恢复事件，两秒后仍无5.5.3恢复或占用释放。后续人工取消投递失败并手动终止；在途仿真指令结束后六代理均恢复在线空闲，模板和延时已复原。",
    evidence=refs, issue="DEF-S3-055"))
update(stage / "rules.csv", "ruleId", "SRS_F004.R05", lambda row: row.update(
    status="F", verifiedBy="TC-012.S1", evidence=refs, issue="DEF-S3-055"))
with (stage / "issues.csv").open(encoding="utf-8-sig", newline="") as stream:
    assert "DEF-S3-055" not in {r["编号"] for r in csv.DictReader(stream)}
with (stage / "issues.csv").open("a", encoding="utf-8", newline="") as stream:
    csv.writer(stream, lineterminator="\n").writerow([
        "DEF-S3-055", "缺陷", "高", "TC-012.S1", "SRS_F004.R05", "待修复",
        "真实占用任务63期间确认停用代理，平台立即标记DISABLED/OFFLINE，但保留BUSY和currentTaskId；仅追加AGENT_DISABLED_WITH_OCCUPATION待处理事件，没有先执行5.5.3恢复再释放占用。随后试运行人工取消投递失败，任务手动终止后在途反馈才使代理空闲。",
        refs, "将占用代理停用接入5.5.3恢复并确认释放完成后改变代理状态；回归取消确认、候选排除及任务事件顺序"])
print(json.dumps({"recorded": "TC-012.S1;SRS_F004.R05;DEF-S3-055",
                  "evidence": refs}, ensure_ascii=False))
