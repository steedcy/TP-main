"""Record only the fully observed TC-093.S1 and narrow NF014 rule."""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

stage = Path(__file__).resolve().parent
root = stage.parents[1]
names = ["TC-093-same-type-new-device-20261027T061308Z.json",
         "TC-093-same-type-new-device-20261027T061359Z.json",
         "TC-093-same-type-new-device-20261027T061502Z.json",
         "TC-093-capability-after-cleanup.json"]
first, second, success, followup = [json.loads((stage / "evidence" / name).read_text(encoding="utf-8"))
                                    for name in names]
assert first["device"]["deviceCode"] == "S3_TC093_DISPLAY"
assert second["device"]["deviceCode"] == "S3_TC093_DISPLAY_B"
assert first["cleanup"]["deviceStatus"] == second["cleanup"]["deviceStatus"] == "DELETED"
assert success["runtimeInput"] == "V1.5" and success["isolatedSchema"] == "tip_stage2_v14"
assert success["device"]["deviceCode"] == "S3_TC093_DISPLAY_C"
assert success["device"]["deviceTypeCode"] == "SIMULATOR"
assert success["device"]["simulatedDeviceType"] == "SMART_DISPLAY"
assert success["connectionTest"]["result"] == "PASSED"
assert success["capabilityCreated"]["capabilityType"] == "CAP_INFO_DISPLAY"
assert success["capabilityTested"]["lastTestAt"] and success["capabilityTested"]["testResult"]
assert followup["capabilities"][0]["capabilityCode"] == "S3_TC093_INFO_C"
assert followup["capabilities"][0]["capabilityStatus"] == "ENABLED"
assert followup["device"]["deviceStatus"] == "DELETED"
assert success["agentBeforeTask"]["onlineStatus"] == "ONLINE"
assert success["task"]["id"] == 88 and success["task"]["status"] == "COMPLETED"
assert success["assignments"][0]["deviceAgentCode"] == success["agentBeforeTask"]["agentId"]
assert success["assignments"][0]["stepStatus"] == "COMPLETED"
assert {x["commandType"]: x["commandStatus"] for x in success["commands"]} == {
    "TASK_ACCEPT": "ACCEPTED", "EXECUTE_CAPABILITY": "SUCCEEDED"}
assert success["assignments"][0]["outputParams"]["displayStatus"] == "SUCCESS"
assert {"AGENT_ASSIGNED", "EXECUTION_FEEDBACK_RECEIVED", "STEP_COMPLETED", "TASK_COMPLETED"}.issubset(
    {x["eventType"] for x in success["events"]})
assert success["sourceHeadBefore"] == success["sourceHeadAfter"]
assert success["simulatorJarShaBefore"] == success["simulatorJarShaAfter"]
assert success["cleanup"]["deviceStatus"] == "DELETED"
assert success["cleanup"]["simulatorStopped"] and success["cleanup"]["originalSixOnlineIdle"]
assert success["cleanup"]["existingTemplateStillDisabled"]
runtime = root / ".local-test/runtime/backend.jar"
runtime_sha = hashlib.sha256(runtime.read_bytes()).hexdigest()
assert runtime_sha == "7f9541e76409afca5656e616b5c6e1737faa545937374c14166130383f829dfd"
runtime_file = stage / "evidence/TC-093-runtime-identity.json"
runtime_file.write_text(json.dumps({
    "observedAt": datetime.now(timezone.utc).isoformat(),
    "runtimeInput": "V1.5", "isolatedSchema": "tip_stage2_v14",
    "backendJarSha256": runtime_sha,
    "previousStage3JarEvidence": "acceptance/stage3/evidence/stage3-service-restart-audit.json",
    "sourceHeadBefore": success["sourceHeadBefore"],
    "sourceHeadAfter": success["sourceHeadAfter"],
    "simulatorJarShaBefore": success["simulatorJarShaBefore"],
    "simulatorJarShaAfter": success["simulatorJarShaAfter"],
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
refs = ";".join("acceptance/stage3/evidence/" + name for name in
                [names[2], names[3], runtime_file.name])

for filename, key, identifier in (("steps.csv", "stepId", "TC-093.S1"),
                                  ("rules.csv", "ruleId", "SRS_NF014.R01")):
    target = stage / filename
    with target.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    row = next(x for x in rows if x[key] == identifier)
    assert row["status"] == "NOT_RUN"
    row["status"] = "P"
    row["evidence"] = refs
    if filename == "steps.csv":
        row["observedAt"] = datetime.now().strftime("%Y-%m-%d")
        row["actual"] = ("新增同类仿真智慧航显，连接测试PASSED，CAP_INFO_DISPLAY能力实测后ENABLED，"
                         "代理ONLINE；以既有模板试运行调用新代理，任务88步骤完成，反馈及事件落库。"
                         "期间业务代码HEAD与后端/仿真JAR标识一致；设备和仿真进程清理，原六代理在线空闲。"
                         "试运行不替代TC-093.S2要求的正式任务，该步仍未执行。")
    else:
        row["verifiedBy"] = "TC-093.S1"
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
assert "原 200 步：P 46、F 67、NT 19、未执行 68" in body
assert "281 条需求规则为 P 105、F 49、NT 11、未执行 116" in body
body = body.replace("原 200 步：P 46、F 67、NT 19、未执行 68",
                    "原 200 步：P 47、F 67、NT 19、未执行 67", 1)
body = body.replace("281 条需求规则为 P 105、F 49、NT 11、未执行 116",
                    "281 条需求规则为 P 106、F 49、NT 11、未执行 115", 1)
note = ("- TC-093.S1与`SRS_NF014.R01`：本轮新增同类仿真航显，连接测试通过，配置的CAP_INFO_DISPLAY"
        "完成真实能力测试并启用，代理ONLINE。用已有模板发起试运行任务88，新代理承接、收到两类指令，"
        "业务反馈SUCCESS，步骤和任务完成；业务代码HEAD、后端及仿真JAR标识保持一致。"
        "设备软删除、仿真进程停止，原六代理在线空闲，步骤和窄范围规则判P。"
        "前两次因测试夹具遗漏模板准备、能力配置而被拒，原始失败证据保留，不记产品缺陷。"
        "TC-093.S2要求正式已有任务调用，试运行不代替该步骤，保持未执行。"
        "见`evidence/TC-093-*`。\n")
body = body.replace("## 已执行\n\n", "## 已执行\n\n" + note, 1)
lines = body.splitlines()
lines[2] = datetime.now().strftime("%Y-%m-%d %H:%M（Asia/Shanghai）") + lines[2][len("2026-10-27 14:09（Asia/Shanghai）"):]
progress.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("recorded TC-093.S1 and SRS_NF014.R01 P; TC-093.S2 remains NOT_RUN")
