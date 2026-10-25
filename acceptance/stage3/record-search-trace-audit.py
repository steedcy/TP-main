"""Record observed V1.5 task search, trace, and audit results without widening coverage."""
import csv
import json
from collections import Counter
from pathlib import Path

here = Path(__file__).resolve().parent
evidence = here / "evidence"
search = json.loads((evidence / "TC-063-task-search.json").read_text(encoding="utf-8"))
trace = json.loads((evidence / "TC-084-trace.json").read_text(encoding="utf-8"))
audit = json.loads((evidence / "TC-085-operation-log.json").read_text(encoding="utf-8"))
assert search["browser"]["goalKeywordFieldCount"] == 0
assert search["missingApiHttpStatus"] == 404 and search["browser"]["returnedToList"] is False
assert trace["planHeaderCount"] >= 2 and trace["stepDetailsVisible"] is False
assert audit["api"]["changedAccountRows"] > 0 and audit["api"]["changedAccountHasDetail"] is False


def read(name):
    with (here / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(name, rows):
    with (here / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


steps = read("steps.csv")
updates = {
    "TC-063.S1": ("F", "任务编号、状态和任务族 API 筛选可用；浏览器没有目标关键字字段，默认时间范围为空，未满足目标关键字和默认今日", "TC-063-task-search.json;TC-063-S1-task-list.png", "DEF-S3-006"),
    "TC-063.S3": ("F", "不存在记录 API 返回404、无权 API 返回403；浏览器访问不存在详情仍停在 /tasks/999999999，未提示后返回列表", "TC-063-task-search.json;TC-063-S3-missing.png", "DEF-S3-007"),
    "TC-084.S1": ("F", "任务19 可按精确编号追溯且显示两个计划版本、27条事件和最终结果；展开计划仅见三类校验，未显示版本步骤明细", "TC-084-trace.json;TC-084-trace-plan.png", "DEF-S3-008"),
    "TC-084.S3": ("NT", "空查询结果显示空态；缺事件区段任务夹具尚未准备，未验证标缺失且不伪造事件", "TC-084-trace.json;TC-084-trace-empty.png", "NT-S3-007"),
    "TC-085.S1": ("F", "管理员筛选操作人与类型/结果准确，默认近7日且账号为空；12条账号状态变更日志均无详情，缺变更前后关键字段摘要", "TC-085-operation-log.json;TC-085-audit-detail.png", "DEF-S3-009"),
    "TC-085.S2": ("NT", "非管理员 API 仅返回自身、页面无编辑删除且空结果有空态；仅抽查一条详情口令未原文显示，尚未穷尽敏感字段和所有记录权限", "TC-085-operation-log.json;TC-085-audit-empty.png", "NT-S3-008"),
}
for row in steps:
    if row["stepId"] not in updates:
        continue
    assert row["status"] == "NOT_RUN", row["stepId"]
    status, actual, files, issue = updates[row["stepId"]]
    row.update(status=status, observedAt="2026-10-25", actual=actual,
               evidence=";".join("acceptance/stage3/evidence/" + part for part in files.split(";")), issue=issue)
write("steps.csv", steps)

rules = read("rules.csv")
for row in rules:
    update = {
        "SRS_F020.R06": ("TC-063.S1", "DEF-S3-006", "TC-063-task-search.json"),
        "SRS_F027.R01": ("TC-084.S1", "DEF-S3-008", "TC-084-trace.json"),
        "SRS_F028.R03": ("TC-085.S1", "DEF-S3-009", "TC-085-operation-log.json"),
    }.get(row["ruleId"])
    if update:
        assert row["status"] == "NOT_RUN", row["ruleId"]
        step, issue, file = update
        row.update(status="F", verifiedBy=step, issue=issue,
                   evidence="acceptance/stage3/evidence/" + file)
write("rules.csv", rules)

issues = read("issues.csv")
issue_updates = [
    ("DEF-S3-006", "缺陷", "中", "TC-063.S1", "SRS_F020.R06", "待修复", "任务列表没有目标关键字筛选，默认时间范围为空；仅状态、任务族、任务号筛选可用", "TC-063-task-search.json", "补目标关键字与默认今日，重测列表及总览跳转"),
    ("DEF-S3-007", "缺陷", "中", "TC-063.S3", "SRS_F020", "待修复", "不存在详情的 API 返回404，但浏览器停在缺失记录路由，未提示并返回列表", "TC-063-task-search.json;TC-063-S3-missing.png", "处理404/归档详情回退，重测403审计"),
    ("DEF-S3-008", "缺陷", "中", "TC-084.S1", "SRS_F027.R01", "待修复", "追溯页计划版本展开仅列三类校验结果，未显示各版本步骤明细", "TC-084-trace.json;TC-084-trace-plan.png", "渲染并核对每版步骤、来源和冻结时间"),
    ("NT-S3-007", "前置缺口", "待定", "TC-084.S3", "SRS_F027", "待补夹具", "空态已见；缺事件区段的任务夹具尚未准备", "TC-084-trace.json", "准备缺事件任务并核对提示和无伪造"),
    ("DEF-S3-009", "缺陷", "中", "TC-085.S1", "SRS_F028.R03", "待修复", "12条账号状态变更日志详情为空，未提供变更前后关键字段摘要", "TC-085-operation-log.json;TC-085-audit-detail.png", "写入脱敏变更摘要并复测详情和关联任务"),
    ("NT-S3-008", "前置缺口", "待定", "TC-085.S2", "SRS_F028", "待补样本", "角色范围、空态、只读已抽查；敏感字段和全部记录范围未穷尽", "TC-085-operation-log.json", "补多类型敏感日志和角色样本，核对掩码"),
]
for values in issue_updates:
    assert values[0] not in {row["编号"] for row in issues}, values[0]
    row = dict(zip(issues[0].keys(), values))
    row["证据"] = ";".join("acceptance/stage3/evidence/" + part for part in row["证据"].split(";"))
    issues.append(row)
write("issues.csv", issues)
print(json.dumps({"steps": dict(Counter(r["status"] for r in steps)),
                  "ac": dict(Counter(r["status"] for r in read("ac.csv"))),
                  "rules": dict(Counter(r["status"] for r in rules))}, ensure_ascii=False))
