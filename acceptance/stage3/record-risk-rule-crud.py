"""Record TC-043.S1 validation, page and version findings from fresh evidence."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
evidence = stage / "evidence"
runs = list(evidence.glob("TC-043-risk-rule-crud-20*.json"))
followups = list(evidence.glob("TC-043-risk-rule-audit-followup-20*.json"))
assert len(runs) == len(followups) == 1
run = json.loads(runs[0].read_text(encoding="utf-8"))
followup = json.loads(followups[0].read_text(encoding="utf-8"))
ui = json.loads((evidence / "TC-043-risk-rule-ui.json").read_text(encoding="utf-8"))
assert run["beforeCount"] == run["cleanup"]["afterCount"] == 3
assert run["cleanup"]["temporaryCodesRemaining"] == []
assert followup["remainingCodes"] == followup["beforeCodes"] == run["beforeRuleCodes"]
assert run["boundary"]["emptyCode"]["httpStatus"] == 200
assert run["boundary"]["emptyContent"]["httpStatus"] == 200
assert run["boundary"]["missingCode"]["httpStatus"] == 500
assert run["boundary"]["missingContent"]["httpStatus"] == 500
assert run["operatorCreate"]["httpStatus"] == 403
assert run["duplicate"]["httpStatus"] == 409
assert run["created"]["ruleVersion"] == "V1.0"
assert run["afterContentUpdate"]["ruleVersion"] == "V1.1"
assert run["afterEnable"]["enabled"] is True
assert run["afterDisable"]["enabled"] is False
assert run["afterEnable"]["ruleVersion"] == run["afterDisable"]["ruleVersion"] == "V1.1"
assert run["browserExitCode"] == 0 and ui["route"] == "/risk-rules"
assert ui["ruleCode"] == run["ruleCode"] and ui["createButtonCount"] == 0
assert ui["editButtonCount"] == ui["switchCount"] == 1
assert len(followup["changeLogs"]) == 4
refs = ";".join("acceptance/stage3/evidence/" + name for name in [
    runs[0].name, followups[0].name, "TC-043-risk-rule-ui.json",
    "TC-043-risk-rule-ui.png"])
today = datetime.now().astimezone().date().isoformat()


def update(name, key, target, values):
    path = stage / name
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    row = next(row for row in rows if row[key] == target)
    assert row["status"] == "NOT_RUN"
    row.update(values)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


update("steps.csv", "stepId", "TC-043.S1", {
    "status": "F", "observedAt": today,
    "actual": "隔离库API重复编号409、非配置管理员403，规则内容修改V1.0→V1.1；空编号/空内容却保存成功，缺字段返回500而非参数提示；Chrome配置页仅可编辑/启停，缺新增入口；启用/停用后规则版本仍V1.1。临时规则已清理且数量恢复3",
    "evidence": refs, "issue": "DEF-S3-041;DEF-S3-042;DEF-S3-043"})
update("rules.csv", "ruleId", "SRS_F014.R05", {
    "status": "F", "verifiedBy": "TC-043.S1", "evidence": refs,
    "issue": "DEF-S3-043"})
issues = stage / "issues.csv"
with issues.open(encoding="utf-8-sig", newline="") as stream:
    found = {row["编号"] for row in csv.DictReader(stream)}
assert not {"DEF-S3-041", "DEF-S3-042", "DEF-S3-043"} & found
with issues.open("a", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["DEF-S3-041", "缺陷", "中", "TC-043.S1", "", "待修复",
                     "风险规则新增接口接受空编号和空内容并持久化；缺少编号/内容返回500系统繁忙，未作明确必填校验。重复编号409、非配置管理员403正常",
                     refs, "新增规则校验编号与内容非空，缺字段返回明确参数错误；复测拒绝后无脏数据"])
    writer.writerow(["DEF-S3-042", "缺陷", "中", "TC-043.S1", "", "待修复",
                     "Chrome风险规则配置页只有内容编辑和启停控件，没有新增规则入口，无法按原步骤填写编号和内容保存",
                     refs, "增加配置管理员新增表单并验证必填、重复及保存结果"])
    writer.writerow(["DEF-S3-043", "缺陷", "中", "TC-043.S1", "SRS_F014.R05", "待修复",
                     "临时规则内容修改使版本V1.0变V1.1，但后续启用和停用均保持V1.1，状态变更未形成新规则集版本",
                     refs, "对规则启停生成可追溯版本并在后续监督判定中记录生效版本"])
print("recorded TC-043.S1 and DEF-S3-041/042/043")
