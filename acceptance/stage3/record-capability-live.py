"""Record live agent capability testing and browser result gaps for TC-020/021/022."""
import csv
import json
from pathlib import Path

here = Path(__file__).resolve().parent
ev = json.loads((here / "evidence/TC-020-021-capability-live.json").read_text(encoding="utf-8"))
ui = json.loads((here / "evidence/TC-020-capability-test-modal.json").read_text(encoding="utf-8"))
obs = ev["observations"]
assert ev["runtimeInput"] == ui["runtimeInput"] == "V1.5"
assert obs["createdStatus"] == "UNTESTED"
assert obs["enableUntested"][0] == obs["enableAfterEdit"][0] == 400
assert obs["firstTestStatus"] == obs["retestStatus"] == "TESTED_PASSED"
assert obs["firstCommandRecord"].startswith("CAPABILITY_TEST|SUCCEEDED|")
assert obs["retestCommandRecord"].startswith("CAPABILITY_TEST|SUCCEEDED|")
assert obs["statusAfterEnable"] == "ENABLED"
assert obs["statusAfterEdit"] == "UNTESTED" and obs["editClearedTestResult"]
assert obs["statusAfterDisable"] == "DISABLED"
assert obs["auditTypes"] == ["DEVICE_CAPABILITY_CREATE", "DEVICE_CAPABILITY_STATUS_CHANGE",
                              "DEVICE_CAPABILITY_TEST", "DEVICE_CAPABILITY_UPDATE"]
assert ev["cleanup"] == {"temporaryCapabilityAbsent": True,
                         "originalCapabilityCodesUnchanged": True,
                         "agentStatus": ["ENABLED", "ONLINE", "IDLE"]}
assert ui["beforeStatus"] == ui["afterRestoreStatus"] == "ENABLED"
assert ui["afterTestStatus"] == "TESTED_PASSED" and ui["restoreHttpStatus"] == 200
assert ui["modalLabels"] == ["测试结果", "详情", "测试时间"]
assert not ui["hasRequestPayload"] and not ui["hasResponsePayload"] and not ui["hasElapsedTime"]


def read(name):
    with (here / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(name, rows):
    with (here / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


files = ("acceptance/stage3/evidence/TC-020-021-capability-live.json;"
         "acceptance/stage3/evidence/TC-020-capability-test-modal.json;"
         "acceptance/stage3/evidence/TC-020-capability-test-modal.png")
steps = read("steps.csv")
for row in steps:
    if row["stepId"] == "TC-020.S2":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", observedAt="2026-10-26", issue="DEF-S3-024",
            actual="在线航显代理实际能力测试成功，命令表有两条独立成功响应，测试后可启用；浏览器结果弹窗仅有结果、详情、测试时间，缺请求、响应及耗时",
            evidence=files)
    elif row["stepId"] == "TC-021.S1":
        assert row["status"] == "NOT_RUN"
        row.update(status="NT", observedAt="2026-10-26", issue="NT-S3-015",
            actual="临时已启用能力修改输入后重置UNTESTED，启用被拒，重测通过后才可再启用；占用中能力停用与异常恢复尚无进行中任务夹具",
            evidence=files)
    elif row["stepId"] == "TC-021.S2":
        assert row["status"] == "NOT_RUN"
        row.update(status="NT", observedAt="2026-10-26", issue="NT-S3-016",
            actual="临时能力新增、修改、测试、启用、停用审计类型齐全，停用状态DISABLED；规划候选集合和进行中步骤切换尚未实测",
            evidence=files)
    elif row["stepId"] == "TC-022.S2":
        assert row["status"] == "NOT_RUN"
        row.update(status="NT", observedAt="2026-10-26", issue="NT-S3-017",
            actual="未经测试或修改后未重测的能力启用均400；正常代理调用成功并留指令；超时、非法参数、设备拒绝以及失败测试后的启用分支未注入",
            evidence=files)
write("steps.csv", steps)

rules = read("rules.csv")
for row in rules:
    if row["ruleId"] == "SRS_F006.R04":
        assert row["status"] == "NOT_RUN"
        row.update(status="NT", verifiedBy="TC-022.S2", evidence=files, issue="NT-S3-017")
    elif row["ruleId"] == "SRS_F006.R05":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", verifiedBy="TC-021.S1", evidence=files)
    elif row["ruleId"] == "SRS_F006.R06":
        assert row["status"] == "NOT_RUN"
        row.update(status="NT", verifiedBy="TC-021.S2", evidence=files, issue="NT-S3-016")
    elif row["ruleId"] == "SRS_F006.R07":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", verifiedBy="TC-021.S2", evidence=files)
    elif row["ruleId"] == "SRS_F006.R08":
        assert row["status"] == "NOT_RUN"
        row.update(status="NT", verifiedBy="TC-022.S2", evidence=files, issue="NT-S3-017")
write("rules.csv", rules)

issues = read("issues.csv")
for ident, kind, level, related, rule, state, fact, action in [
    ("DEF-S3-024", "缺陷", "中", "TC-020.S2", "SRS_F006", "待修复",
     "能力模拟调用结果弹窗只有结果、详情、测试时间，缺调用请求、设备响应和耗时；后端命令记录有响应可追溯",
     "在结果页显示脱敏请求、响应、耗时并用在线代理重新测试"),
    ("NT-S3-015", "前置缺口", "待定", "TC-021.S1", "SRS_F006.R05", "待补占用任务",
     "参数编辑重置未测试和重测启用已证；占用中能力停用及异常恢复未执行",
     "用隔离进行中任务占用临时能力后停用，检查5.5.3恢复"),
    ("NT-S3-016", "前置缺口", "待定", "TC-021.S2", "SRS_F006.R06", "待补候选快照",
     "停用状态和五类操作审计已证；规划候选排除与进行中步骤处理未实测",
     "在停用前后生成候选快照并执行占用中场景"),
    ("NT-S3-017", "前置缺口", "待定", "TC-022.S2", "SRS_F006.R04;SRS_F006.R08", "待补代理故障注入",
     "未测试能力启用拒绝、正常代理测试已证；超时、非法参数、拒绝及失败后启用未执行",
     "对隔离代理注入三类失败并核对测试结果、启用拒绝及统一消息记录"),
]:
    assert ident not in {row["编号"] for row in issues}
    issues.append(dict(zip(issues[0].keys(), [ident, kind, level, related, rule, state, fact, files, action])))
write("issues.csv", issues)
