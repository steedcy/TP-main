"""Classify TC-070.S1/S3 and exact map rules from live Chrome/API samples."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
evidence = stage / "evidence"
ev = json.loads((evidence / "TC-070-situation-interactions.json").read_text(encoding="utf-8"))
off = json.loads((evidence / "TC-014-offline-ui.json").read_text(encoding="utf-8"))
busy = json.loads((evidence / "TC-014-status-A-ui.json").read_text(encoding="utf-8"))
assert ev["runtimeInput"] == "V1.5" and len(ev["snapshot"]["agents"]) == 6
assert ev["defaultChecked"] == 5 and len(ev["filterValues"]) == 5
assert set(ev["filterValues"]) == {"SMART_DISPLAY", "BAGGAGE_SCANNER",
                                  "FLIGHT_DELAY_BOARD", "MOBILE_ROBOT", "SIMULATOR"}
assert ev["initialMarkerCount"] == ev["initialRows"] == ev["restoredMarkerCount"] == 6
assert ev["singleTypeChecked"] == 1 and len(ev["singleTypeMarkers"]) == len(ev["singleTypeRows"]) == 1
assert "SIM_F2_DISPLAY" in ev["singleTypeRows"][0]
image = ev["floorplan"]
assert image["loaded"] and (image["naturalWidth"], image["naturalHeight"]) == (1260, 6895)
assert abs(image["displayedWidth"] / image["displayedHeight"] - 1260 / 6895) < 0.0001
assert [ev[x] for x in ("zoomAfterIn", "zoomAfterOut", "zoomFitWidth")] == ["125%", "100%", "100%"]
assert ev["zoomFitAll"] != "100%" and "translate(60px, 30px)" in ev["canvasStylePanned"]
assert ev["displayClick"] == "blocked-by-overlap"
assert len(ev["markers"]) == 6
for marker, agent in zip(ev["markers"], ev["snapshot"]["agents"]):
    assert marker["name"] == agent["deviceName"]
    assert "marker-online" in marker["className"]
    assert abs(float(marker["left"].strip("%")) - agent["location"]["x"] / 1260 * 100) < 0.0002
    assert abs(float(marker["top"].strip("%")) - agent["location"]["y"] / 6895 * 100) < 0.0002
assert "SIM_F2_BAGGAGE" in ev["selectedBaggageDetail"]
assert ev["mutationsAfterOpen"] == []
assert all(value == 0 for value in ev["noOperationLabels"].values())
assert "重新标定" in ev["scopeHint"]
assert "marker-offline" in off["situationMarkerClass"]
assert "marker-busy" in busy["markerClass"]
assert off["situationRow"].split("\t")[5] == "805, 4200"
refs = ";".join("acceptance/stage3/evidence/" + name for name in [
    "TC-070-situation-interactions.json", "TC-070-map-default.png",
    "TC-070-map-filtered.png", "TC-070-map-selected.png"])
offline_refs = "acceptance/stage3/evidence/TC-014-offline-ui.json;acceptance/stage3/evidence/TC-014-offline-situation.png"
busy_refs = "acceptance/stage3/evidence/TC-014-status-A-ui.json;acceptance/stage3/evidence/TC-014-status-A.png"
date = datetime.now().astimezone().date().isoformat()

path = stage / "steps.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
for row in rows:
    if row["stepId"] == "TC-070.S1":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", observedAt=date, issue="DEF-S3-048",
            actual="Chrome态势底图1260×6895按原比缩放，六个标记的百分比位置与接口像素坐标一致；五类默认全选、125%放大/还原/全图、拖动平移及仅航显筛选正常。地图中航显标记与机器人标记相叠，直接点击被后者拦截，不能可靠选中该图标；离线灰和忙碌橙由本轮TC-014动态采样补证",
            evidence=refs + ";" + offline_refs + ";" + busy_refs)
    elif row["stepId"] == "TC-070.S3":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", observedAt=date,
            actual="态势页面只有刷新、底图缩放/适配、类型筛选与设备状态详情；本轮交互无POST/PUT/PATCH/DELETE请求，无设备指令、在线编辑、地图版本管理或轨迹回放入口；页面提示更换底图尺寸/裁剪范围须重标坐标。未实际替换底图",
            evidence=refs)
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

path = stage / "rules.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
updates = {
    "SRS_F023.R01": ("P", "TC-070.S1;TC-014.S1;TC-014.S2", refs + ";" + offline_refs + ";" + busy_refs, ""),
    "SRS_F023.R02": ("F", "TC-070.S1", refs + ";" + offline_refs, "DEF-S3-048"),
    "SRS_F023.R05": ("P", "TC-070.S3", refs, ""),
    "SRS_F023.R06": ("P", "TC-014.S2", offline_refs, ""),
    "SRS_F023.R08": ("P", "TC-070.S1", refs, ""),
    "SRS_F023.R10": ("P", "TC-070.S3", refs, ""),
}
for row in rows:
    if row["ruleId"] in updates:
        assert row["status"] == "NOT_RUN"
        status, verified, proof, issue = updates[row["ruleId"]]
        row.update(status=status, verifiedBy=verified, evidence=proof, issue=issue)
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print("recorded TC-070.S1 F, S3 P; five F023 rules P and R02 F")
