"""Record TC-090 dual-browser, dual-resolution coverage and remaining interactions."""
import csv
import json
from collections import Counter
from pathlib import Path

here = Path(__file__).resolve().parent
ev = json.loads((here / "evidence/TC-090-browser-layout.json").read_text(encoding="utf-8"))
samples = ev["samples"]
assert len(samples) == 24
assert Counter((x["browser"], x["resolution"]) for x in samples) == {
    (browser, resolution): 6 for browser in ("Chrome", "Edge")
    for resolution in ("1366x768", "1920x1080")}
assert all(not x["horizontalOverflow"] and x["documentScrollWidth"] <= x["viewportWidth"] for x in samples)
assert {x["label"] for x in samples} == {"devices", "device-modal", "tasks", "task-modal", "situation", "trace"}
assert all(x["route"] == {
    "devices": "/devices", "device-modal": "/devices", "tasks": "/tasks",
    "task-modal": "/tasks", "situation": "/situation", "trace": "/task-trace"}[x["label"]] for x in samples)


def read(name):
    with (here / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(name, rows):
    with (here / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


file = "acceptance/stage3/evidence/TC-090-browser-layout.json"
screens = ";".join("acceptance/stage3/evidence/TC-090-" + browser + "-" + name + ".png"
                   for browser in ("Chrome", "Edge") for name in ("device-modal", "task-modal"))
steps = read("steps.csv")
for row in steps:
    if row["stepId"] == "TC-090.S1":
        assert row["status"] == "NOT_RUN"
        row.update(status="NT", observedAt="2026-10-26", issue="NT-S3-011",
                   actual="Chrome与Edge均可登录并打开设备配置、任务列表与提交弹窗、态势和追溯；未在两浏览器各自实际保存配置、提交并监控任务",
                   evidence=file + ";" + screens)
    elif row["stepId"] == "TC-090.S2":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", observedAt="2026-10-26",
                   actual="Chrome和Edge分别在1920×1080、1366×768打开四个核心页面及配置/任务弹窗共24个样本；页面路径正确，无横向溢出，弹窗与操作按钮在视口内可见",
                   evidence=file + ";" + screens)
write("steps.csv", steps)

rules = read("rules.csv")
for row in rules:
    if row["ruleId"] == "SRS_NF010.R01":
        assert row["status"] == "NOT_RUN"
        row.update(status="NT", verifiedBy="TC-090.S1", issue="NT-S3-011", evidence=file)
    elif row["ruleId"] == "SRS_NF012.R01":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", verifiedBy="TC-090.S2", evidence=file + ";" + screens)
write("rules.csv", rules)

issues = read("issues.csv")
assert "NT-S3-011" not in {row["编号"] for row in issues}
issues.append(dict(zip(issues[0].keys(), [
    "NT-S3-011", "前置缺口", "待定", "TC-090.S1", "SRS_NF010.R01", "待补交互",
    "双浏览器核心页面和弹窗已打开；配置保存、任务实际提交监控尚未在两浏览器各自执行",
    file, "在Chrome与Edge分别保存隔离配置并提交/监控任务，核对字段提示与按钮",
])))
write("issues.csv", issues)
