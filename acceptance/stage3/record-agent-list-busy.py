"""Record TC-011.S2 from the live busy agent, Chrome and role follow-ups."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
evidence = stage / "evidence"
runs = list(evidence.glob("TC-011-busy-agent-20*.json"))
assert len(runs) == 1
run = json.loads(runs[0].read_text(encoding="utf-8"))
ui = json.loads((evidence / "TC-011-busy-agent-ui.json").read_text(encoding="utf-8"))
routes = json.loads((evidence / "TC-011-task-link-role.json").read_text(encoding="utf-8"))
api = json.loads((evidence / "TC-011-task-link-api.json").read_text(encoding="utf-8"))
agent = run["agentAtBusy"]
assert agent["workStatus"] == "BUSY" and agent["onlineStatus"] == "ONLINE"
assert agent["currentTaskId"] == run["dryRunStarted"]["taskId"] == ui["taskId"] == 57
assert agent["currentStepSeq"] == 1 and agent["lastReportedAt"]
assert run["browserExitCode"] == 0 and ui["route"] == "/device-agents"
assert ui["currentTaskLinkCount"] == 1 and ui["currentTaskHref"] == "/tasks/57"
assert ui["agentDetailLinkCount"] == 0 and not ui["capabilitySummaryVisible"]
assert all(label in ui["headers"] for label in ["代理编号", "关联设备", "设备编码",
    "代理状态", "在线状态", "工作状态", "当前任务", "最后上报时间"])
assert routes["roles"]["配置管理员"]["finalRoute"] == "/overview"
assert routes["roles"]["运行操作员"]["finalRoute"] == "/tasks/57"
assert api["roleResults"]["配置管理员"]["httpStatus"] == 403
assert api["roleResults"]["运行操作员"]["httpStatus"] == 200
assert api["roleResults"]["运行操作员"]["returnedId"] == 57
assert run["restore"]["allSixOnlineIdle"]
assert run["restore"]["templateStatus"] == "DISABLED"
assert run["restore"]["delayMs"] == 1000
refs = ";".join("acceptance/stage3/evidence/" + name for name in [
    runs[0].name, "TC-011-busy-agent-ui.json", "TC-011-busy-agent-list.png",
    "TC-011-busy-agent-task.png", "TC-011-task-link-role.json",
    "TC-011-task-link-api.json"])
path = stage / "steps.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(row for row in rows if row["stepId"] == "TC-011.S2")
assert row["status"] == "NOT_RUN"
row.update(status="F", observedAt=datetime.now().astimezone().date().isoformat(),
    actual="任务57试运行真实占用航显代理，列表显示设备/编码、启停、在线、占用、当前任务步骤和最后上报时间；无代理详情入口与启用能力编码名称摘要。配置管理员可见的任务#57链接指向真实任务，但点击/直达回总览且API403；运行操作员同一路由和API可访问。试运行取消后六代理在线空闲",
    evidence=refs, issue="DEF-S3-044;DEF-S3-045")
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
issues = stage / "issues.csv"
with issues.open(encoding="utf-8-sig", newline="") as stream:
    found = {row["编号"] for row in csv.DictReader(stream)}
assert not {"DEF-S3-044", "DEF-S3-045"} & found
with issues.open("a", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["DEF-S3-044", "缺陷", "中", "TC-011.S2", "", "待修复",
                     "Chrome设备代理列表展示忙碌任务与状态，但没有代理详情入口，也不展示启用能力编码名称摘要；代理详情API本身不含能力摘要",
                     refs, "增加代理详情和能力摘要，核对列表/详情及当前任务与步骤"])
    writer.writerow(["DEF-S3-045", "缺陷", "中", "TC-011.S2", "", "待修复",
                     "配置管理员可见当前任务#57链接，但该角色打开任务详情被路由重定向至总览、API返回403；运行操作员可访问同一任务",
                     refs, "为配置管理员提供可读的关联任务详情或在无权时改为明确不可点击提示；重测链接和权限"])
print("recorded TC-011.S2 and DEF-S3-044/045")
