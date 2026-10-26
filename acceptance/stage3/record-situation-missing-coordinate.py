"""Record the unresolved live missing-coordinate branch of TC-071.S1."""
import csv
import json
from pathlib import Path

p = Path(__file__).resolve().parent
names = (
    "TC-014-heartbeat-ui-20261026T074608Z.json",
    "TC-014-offline-ui.json", "TC-014-offline-situation.png",
    "TC-071-missing-coordinate-api-20261026T115437Z.json",
    "TC-071-missing-coordinate-ui.json", "TC-071-missing-coordinate-ui.png",
)
refs = ";".join("acceptance/stage3/evidence/" + name for name in names)
assert all((p / "evidence" / name).exists() for name in names)
api = json.loads((p / "evidence" / names[3]).read_text(encoding="utf-8"))
ui = json.loads((p / "evidence" / names[4]).read_text(encoding="utf-8"))
assert api["databaseCoordinateConstraints"] == ["position_x|NO", "position_y|NO"]
assert all(not attempt["accepted"] for attempt in api["attempts"])
assert ui["injectedMarkerCount"] == 0 and "无有效坐标" in ui["injectedTableRow"]
assert ui["markerCount"] == 5

for filename, key, updates in (
    ("steps.csv", "stepId", {"TC-071.S1": {
        "status": "NT", "observedAt": "2026-10-26",
        "actual": "离线保留灰色末位置已有本轮实测；真实设备更新缺X/Y均400且隔离库两坐标列NOT NULL，无法建立真实缺坐标代理。浏览器仅用注入快照验证图外列表回退，不能代替端到端路径",
        "evidence": refs, "issue": "NT-S3-024"}}),
    ("rules.csv", "ruleId", {"SRS_F023.R07": {
        "status": "NT", "verifiedBy": "TC-071.S1",
        "evidence": refs, "issue": "NT-S3-024"}}),
):
    file = p / filename
    with file.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    for row in rows:
        if row[key] in updates:
            assert row["status"] == "NOT_RUN"
            row.update(updates[row[key]])
    with file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

file = p / "issues.csv"
with file.open(encoding="utf-8-sig", newline="") as handle:
    reader = csv.DictReader(handle)
    fields = reader.fieldnames
    rows = list(reader)
assert not any(row["编号"] == "NT-S3-024" for row in rows)
rows.append({
    "编号": "NT-S3-024", "类型": "前置缺口", "级别": "待定",
    "关联用例步骤": "TC-071.S1", "关联需求规则": "SRS_F023.R07",
    "状态": "待真实缺坐标路径",
    "事实": "隔离库设备position_x/y均NOT NULL，已有设备PUT缺任一坐标均400；真实态势无法产生缺坐标设备。Chrome注入快照后仅该标记退出地图并在列表显示无有效坐标，证明页面回退但不证明端到端路径",
    "证据": refs,
    "阶段4动作": "明确允许缺坐标的设备生命周期/数据入口，建立真实缺坐标代理后重测地图外列表、恢复坐标及离线组合",
})
with file.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

report = p / "阶段3-复测进度.md"
body = report.read_text(encoding="utf-8")
body = body.replace("2026-10-26 19:52（Asia/Shanghai）", "2026-10-26 19:55（Asia/Shanghai）", 1)
body = body.replace(
    "原 200 步：P 39、F 50、NT 18、未执行 93；27 项 AC 为 F 5、NT 1、未执行 21；281 条需求规则为 P 62、F 29、NT 8、未执行 182。",
    "原 200 步：P 39、F 50、NT 19、未执行 92；27 项 AC 为 F 5、NT 1、未执行 21；281 条需求规则为 P 62、F 29、NT 9、未执行 181。", 1)
anchor = "- TC-071.S2："
addition = (
    "- TC-071.S1：离线设备末位置灰标由本轮TC-014.S2原始实测覆盖；缺坐标分支本轮分别将现有设备X、Y置空提交，"
    "均被真实API以400拒绝，隔离库两列均NOT NULL。Chrome对真实200态势响应只在浏览器侧将航显坐标注入null，"
    "该标记从底图消失、列表保留并显示“无有效坐标”。页面防御性回退已证，真实设备缺坐标状态无法建立，"
    "故步骤和`SRS_F023.R07`具名NT（`NT-S3-024`），不把注入结果充作端到端通过。"
    "原始接口/约束/页面证据见`evidence/TC-071-missing-coordinate-api-20261026T115437Z.json`、"
    "`evidence/TC-071-missing-coordinate-ui.json`及截图。\n"
)
assert anchor in body
body = body.replace(anchor, addition + anchor, 1)
body = body.replace("继续剩余 93 个原步骤、21 项未执行 AC 和 182 条未执行规则",
                    "继续剩余 92 个原步骤、21 项未执行 AC 和 181 条未执行规则")
report.write_text(body, encoding="utf-8")
