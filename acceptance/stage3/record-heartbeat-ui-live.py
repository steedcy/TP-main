"""Upgrade TC-014.S2 to F from fresh offline/recovery UI evidence."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
evidence = stage / "evidence"
first = json.loads((evidence / "TC-014-heartbeat-ui-20261026T074351Z.json").read_text(encoding="utf-8"))
run = json.loads((evidence / "TC-014-heartbeat-ui-20261026T074608Z.json").read_text(encoding="utf-8"))
off = json.loads((evidence / "TC-014-offline-ui.json").read_text(encoding="utf-8"))
on = json.loads((evidence / "TC-014-recovered-ui.json").read_text(encoding="utf-8"))
assert first["offline"]["browser"]["exitCode"] == first["restore"]["browser"]["exitCode"] == 1
assert first["restore"]["agent"]["onlineStatus"] == "ONLINE"
assert run["offlineElapsedSeconds"] >= 30
assert run["offline"]["agent"]["onlineStatus"] == "OFFLINE"
assert run["offline"]["situation"]["onlineStatus"] == "OFFLINE"
assert run["offline"]["onlineFilterContains"] is False
assert run["offline"]["agent"]["lastReportedAt"] == run["before"]["agent"]["lastReportedAt"]
assert len(run["offline"]["events"]) == len(run["before"]["events"]) + 1
assert run["offline"]["events"][-1]["eventType"] == "AGENT_OFFLINE_DETECTED"
assert run["offline"]["events"][-1]["reasonCode"] == "ERR_HEARTBEAT_TIMEOUT"
assert run["restore"]["agent"]["onlineStatus"] == "ONLINE"
assert run["restore"]["situation"]["onlineStatus"] == "ONLINE"
assert len(run["restore"]["events"]) == len(run["before"]["events"]) + 2
assert run["restore"]["events"][-1]["eventType"] == "AGENT_ONLINE_RECOVERED"
assert run["offline"]["browser"]["exitCode"] == run["restore"]["browser"]["exitCode"] == 0
assert "marker-offline" in off["situationMarkerClass"]
assert "marker-online" in on["situationMarkerClass"]
assert off["markerClick"] == on["markerClick"] == "blocked-by-overlap"
assert off["situationAlerts"] == off["agentAlerts"] == []
assert off["situationLastReportedCell"]["className"] == "ant-table-cell"
assert off["agentLastReportedCell"]["className"] == "ant-table-cell"
assert off["situationLastReportedCell"]["text"] == run["offline"]["agent"]["lastReportedAt"]
assert "ERR_HEARTBEAT_TIMEOUT" not in off["situationDetail"]
assert "ERR_HEARTBEAT_TIMEOUT" not in off["agentRow"]
assert run["offline"]["agent"]["currentTaskId"] is None
files = ["TC-014-heartbeat-ui-20261026T074351Z.json",
         "TC-014-heartbeat-ui-20261026T074608Z.json",
         "TC-014-offline-ui.json", "TC-014-recovered-ui.json",
         "TC-014-offline-situation.png", "TC-014-offline-agent.png",
         "TC-014-recovered-situation.png", "TC-014-recovered-agent.png"]
refs = ";".join("acceptance/stage3/evidence/" + file for file in files)

path = stage / "steps.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(row for row in rows if row["stepId"] == "TC-014.S2")
assert row["status"] == "NT" and row["issue"] == "NT-S3-010"
row.update(status="F", observedAt=datetime.now().astimezone().date().isoformat(),
    actual="本轮停心跳31.55秒后代理/态势OFFLINE、退出在线筛选，新增心跳超时事件及原因码；恢复后ONLINE并新增恢复事件。Chrome地图灰标、代理列表离线，但最后上报时间均为普通单元格、无高亮；详情/列表无离线原因码和是否影响任务说明。默认图上显示终端标记与机器人标记重叠，直接点击被遮挡。新任务分配拒绝分支尚未实测",
    evidence=row["evidence"] + ";" + refs,
    issue="DEF-S3-047;DEF-S3-048;NT-S3-010")
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

path = stage / "issues.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
by_id = {row["编号"]: row for row in rows}
assert "DEF-S3-047" not in by_id and "DEF-S3-048" not in by_id
by_id["NT-S3-010"]["事实"] = "心跳离线与恢复、Chrome离线显示已实测；离线设备不得参与新任务分配的执行保护尚未独立实测"
by_id["NT-S3-010"]["证据"] += ";" + refs
by_id["NT-S3-010"]["阶段4动作"] = "在独立新任务分配夹具中使航显离线，核对候选与指令均排除该代理，再恢复验证"
rows.append(dict(zip(fields, ["DEF-S3-047", "缺陷", "中", "TC-014.S2", "", "待修复",
    "心跳超时离线后态势及代理列表最后上报时间均无高亮；页面不显示离线原因码及是否影响任务说明，尽管设备事件API已有ERR_HEARTBEAT_TIMEOUT",
    refs, "在离线态势及代理详情显示高亮时间、原因码和任务影响判断，复测离线与恢复界面"])))
rows.append(dict(zip(fields, ["DEF-S3-048", "缺陷", "中", "TC-014.S2", "", "待修复",
    "默认F2地图中显示终端标记被移动机器人标记遮挡，Playwright真实点击因后者拦截而失败；只能通过DOM触发该标记详情",
    refs, "处理坐标接近时标记重叠的选中与层级，复测鼠标点击和离线详情入口"])))
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print("recorded TC-014.S2 F and DEF-S3-047/048; assignment branch remains NT")
