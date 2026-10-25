"""Record newly observed scene failures and partial successful branches."""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EV = HERE / "evidence"


def load(name):
    return json.loads((EV / name).read_text(encoding="utf-8"))


bag_first = load("TC-072-073-baggage-202230.json")
bag_normal = load("TC-072-073-baggage-202259.json")
special = load("TC-077-special-202424.json")
flight = load("TC-080-081-flight-202550.json")
assert bag_first["results"][1]["task"]["status"] == "COMPLETED"
assert bag_first["results"][1]["task"]["id"] == 19
normal = bag_normal["results"][0]["task"]
assert normal["status"] == "PENDING_MANUAL"
assert normal["sceneParams"]["baggageLocation"] == "F2_BAGGAGE_POINT"
assert any("缺少required参数baggageLocation" in q for q in normal["missingInfoQuestions"])
assert special["task"]["status"] == "PENDING_MANUAL" and special["task"]["id"] == 22
assert special["task"]["sceneParams"]["assistanceType"] == "轮椅协助"
assert flight["task"]["status"] == "PENDING_MANUAL" and flight["task"]["id"] == 24
assert flight["invalidGateHttpStatus"] == 400
assert flight["task"]["sceneParams"]["newGate"] == "F2_TEST_GATE"
assert len(flight["channels"]) == 0

updates = {
    "TC-072.S1": ("NT", "本轮操作员目标和仿真测量样本已设置，超规任务19完成；未独立验证模拟测量事件自动触发与柜台可选表单", "TC-072-073-baggage-202230.json", "NT-S3-004"),
    "TC-072.S2": ("NT", "任务19经候选校验失败切合格基线，完成测量、上报、航显和机器人业务引导；页面办理说明及另一风险判定分支未观察", "TC-072-073-baggage-202230.json", "NT-S3-005"),
    "TC-072.S3": ("P", "超规任务19完成，计划/设备步骤/测量阈值/发布/引导结果和事件时间线均保留", "TC-072-073-baggage-202230.json", ""),
    "TC-073.S1": ("F", "非超规任务20提交了baggageLocation=F2_BAGGAGE_POINT与55×40×20cm/10kg，仍连续三轮误报缺少baggageLocation，未测量", "TC-072-073-baggage-202259.json", "DEF-S3-003"),
    "TC-073.S2": ("F", "非超规任务20最终PENDING_MANUAL，未记录测量结果，未按要求完成", "TC-072-073-baggage-202259.json", "DEF-S3-003"),
    "TC-077.S1": ("F", "任务22具备轮椅协助、F2预置起点目的地和虚构服务编号；三轮追问任务定义外参数及身份确认后转人工", "TC-077-special-202424.json", "DEF-S3-004"),
    "TC-077.S2": ("F", "完整场景输入的任务22未生成会合提示/陪同计划，未执行航显或机器人", "TC-077-special-202424.json", "DEF-S3-004"),
    "TC-077.S3": ("F", "任务22为PENDING_MANUAL，只有目标/澄清/转人工事件，无陪同进度与完成时间", "TC-077-special-202424.json", "DEF-S3-004"),
    "TC-080.S1": ("NT", "本轮仅结构化登机口变更事件；未执行延误、提前、取消及两种触发方式、完整页面边界", "TC-080-081-flight-202500.json", "NT-S3-006"),
    "TC-080.S2": ("F", "任务24已提交航班号、原时间、原/新登机口、变更内容；模型仍要求指定机器人ID和路线编码，三轮后转人工", "TC-080-081-flight-202550.json", "DEF-S3-005"),
    "TC-081.S1": ("F", "六台标准仿真体在线但完整登机口事件任务24未生成三渠道计划，转人工", "TC-080-081-flight-202550.json", "DEF-S3-005"),
    "TC-081.S2": ("F", "任务24无航延屏、智慧航显或机器人步骤结果", "TC-080-081-flight-202550.json", "DEF-S3-005"),
    "TC-081.S3": ("F", "任务24无实际渠道内容、响应时间或完成时间", "TC-080-081-flight-202550.json", "DEF-S3-005"),
}

path = HERE / "steps.csv"
with path.open(encoding="utf-8-sig", newline="") as source:
    rows = list(csv.DictReader(source))
for row in rows:
    if row["stepId"] not in updates:
        continue
    assert row["status"] == "NOT_RUN"
    status, actual, file, issue = updates[row["stepId"]]
    row.update(status=status, observedAt="2026-10-25", actual=actual,
               evidence="acceptance/stage3/evidence/" + file, issue=issue)
with path.open("w", encoding="utf-8-sig", newline="") as target:
    writer = csv.DictWriter(target, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

ac_path = HERE / "ac.csv"
with ac_path.open(encoding="utf-8-sig", newline="") as source:
    acs = list(csv.DictReader(source))
ac_updates = {
    "AC-017": ("NT", "超规目标任务19完成；缺模拟测量事件自动触发和柜台可选分支", "TC-072-073-baggage-202230.json", "NT-S3-004"),
    "AC-018": ("F", "两个扫描仿真体设为非超规样本；任务20在测量前误报缺少已提交的baggageLocation而转人工", "TC-072-073-baggage-202259.json", "DEF-S3-003"),
    "AC-020": ("F", "已具备轮椅协助、预置起终点和虚构服务编号，任务22无法生成正常陪同计划", "TC-077-special-202424.json", "DEF-S3-004"),
    "AC-021": ("F", "完整登机口变更输入任务24仍要求指定机器人ID和路线编码，无法规划；其余三类事件待执行", "TC-080-081-flight-202550.json", "DEF-S3-005"),
    "AC-022": ("F", "完整登机口变更任务24未生成三渠道执行结果", "TC-080-081-flight-202550.json", "DEF-S3-005"),
}
for row in acs:
    if row["acId"] in ac_updates:
        assert row["status"] == "NOT_RUN"
        status, actual, file, issue = ac_updates[row["acId"]]
        row.update(status=status, observedAt="2026-10-25", actual=actual,
                   evidence="acceptance/stage3/evidence/" + file, issue=issue)
with ac_path.open("w", encoding="utf-8-sig", newline="") as target:
    writer = csv.DictWriter(target, fieldnames=acs[0].keys())
    writer.writeheader()
    writer.writerows(acs)

rule_path = HERE / "rules.csv"
with rule_path.open(encoding="utf-8-sig", newline="") as source:
    rules = list(csv.DictReader(source))
rule_updates = {
    "SRS_F024.R03": ("TC-073.S1", "DEF-S3-003", "TC-072-073-baggage-202259.json"),
    "SRS_F025.R01": ("TC-077.S1", "DEF-S3-004", "TC-077-special-202424.json"),
    "SRS_F026.R04": ("TC-081.S1", "DEF-S3-005", "TC-080-081-flight-202550.json"),
}
for row in rules:
    if row["ruleId"] in rule_updates:
        assert row["status"] == "NOT_RUN"
        step, issue, file = rule_updates[row["ruleId"]]
        row.update(status="F", verifiedBy=step, issue=issue,
                   evidence="acceptance/stage3/evidence/" + file)
with rule_path.open("w", encoding="utf-8-sig", newline="") as target:
    writer = csv.DictWriter(target, fieldnames=rules[0].keys())
    writer.writeheader()
    writer.writerows(rules)
print(json.dumps({"steps": {state: sum(r["status"] == state for r in rows) for state in ("P", "F", "NT", "NOT_RUN")},
                  "ac": {state: sum(r["status"] == state for r in acs) for state in ("P", "F", "NT", "NOT_RUN")},
                  "rules": {state: sum(r["status"] == state for r in rules) for state in ("P", "F", "NT", "NOT_RUN")}}, ensure_ascii=False))
