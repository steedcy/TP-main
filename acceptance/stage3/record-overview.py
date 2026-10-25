"""Add TC-004 observations; never infer missing fixture branches as passes."""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
api = json.loads((HERE / "evidence/TC-004-overview-api.json").read_text(encoding="utf-8"))
ui = json.loads((HERE / "evidence/TC-004-overview-ui.json").read_text(encoding="utf-8"))
assert ui["pass"]
assert api["dryRunStates"].get("COMPLETED") == 6
assert api["statusFixture"].get("COMPLETED") == 6
assert api["apiMetrics"]["today"]["statusCounts"]["COMPLETED"] == 12
assert api["observedStatusCount"] < 9

path = HERE / "steps.csv"
with path.open(encoding="utf-8-sig", newline="") as source:
    rows = list(csv.DictReader(source))
updates = {
    "TC-004.S1": ("NT", "当前仅3种正式任务状态，缺九状态及五类异常完整夹具；现有代理/进行中/重规划/未处置指标与独立SQL一致", "TC-004-overview-api.json", "NT-S3-002"),
    "TC-004.S2": ("F", "正式COMPLETED=6，试运行COMPLETED=6，总览已完成显示12；试运行混入正式九状态分布。五类异常及跳转分支另缺夹具", "TC-004-overview-api.json", "DEF-S3-002"),
    "TC-004.S3": ("P", "三角色默认今日、切换近7日与手动刷新均发实际请求；配置管理员不显示任务指标，管理员和操作员显示", "TC-004-overview-api.json;TC-004-overview-ui.json;TC-004-S3-admin.png;TC-004-S3-oprator.png;TC-004-S3-set.png", ""),
    "TC-004.S4": ("NT", "尚无单个总览指标查询超时/失败的隔离注入点；未用整页接口拦截冒充单指标故障", "", "NT-S3-003"),
}
for row in rows:
    if row["stepId"] in updates:
        status, actual, files, issue = updates[row["stepId"]]
        assert row["status"] == "NOT_RUN"
        row.update(status=status, observedAt="2026-10-25", actual=actual,
                   evidence=";".join("acceptance/stage3/evidence/" + file for file in files.split(";")) if files else "",
                   issue=issue)
with path.open("w", encoding="utf-8-sig", newline="") as target:
    writer = csv.DictWriter(target, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

rules_path = HERE / "rules.csv"
with rules_path.open(encoding="utf-8-sig", newline="") as source:
    rules = list(csv.DictReader(source))
for row in rules:
    if row["ruleId"] == "SRS_F002.R02":
        row.update(status="F", verifiedBy="TC-004.S2", issue="DEF-S3-002",
                   evidence="acceptance/stage3/evidence/TC-004-overview-api.json")
    elif row["ruleId"] == "SRS_F002.R08":
        row.update(status="P", verifiedBy="TC-004.S3",
                   evidence="acceptance/stage3/evidence/TC-004-overview-ui.json")
with rules_path.open("w", encoding="utf-8-sig", newline="") as target:
    writer = csv.DictWriter(target, fieldnames=rules[0].keys())
    writer.writeheader()
    writer.writerows(rules)
print(json.dumps({"steps": {state: sum(r["status"] == state for r in rows) for state in ("P", "F", "NT", "NOT_RUN")},
                  "rules": {state: sum(r["status"] == state for r in rules) for state in ("P", "F", "NT", "NOT_RUN")}}, ensure_ascii=False))
