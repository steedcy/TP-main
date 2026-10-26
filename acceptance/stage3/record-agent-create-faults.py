"""Record TC-013 scoped collision/insert failures and partial retry coverage."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
evidence = stage / "evidence"
files = ["TC-013-agent-create-faults-20261026T073713Z.json",
         "TC-013-agent-create-faults-20261026T073826Z.json",
         "TC-013-agent-create-faults-20261026T073917Z.json"]
first, failed_capture, ev = (json.loads((evidence / file).read_text(encoding="utf-8"))
                              for file in files)
assert first["cleanup"]["faultFunctionAbsent"] and first["cleanup"]["deviceStatus"] == "DELETED"
assert failed_capture["cleanup"]["faultFunctionAbsent"] and failed_capture["cleanup"]["deviceStatus"] == "DELETED"
assert ev["connectionTest"]["result"] == "PASSED"
for mode in ("collision", "insert_failure"):
    fault = ev["faults"][mode]
    assert fault["request"]["httpStatus"] == 500
    assert fault["request"]["body"]["message"] == "系统繁忙，请稍后重试"
    assert fault["agentCountAfter"] == 0
    assert fault["connectionTestStatusAfter"] == "PASSED"
assert ev["retry"]["httpStatus"] == ev["repeatCreate"]["httpStatus"] == 200
assert ev["agentCountAfterRetry"] == ev["agentCountAfterRepeat"] == 1
assert ev["retry"]["body"]["data"]["agentId"] == ev["repeatCreate"]["body"]["data"]["agentId"]
assert ev["agentAfterBinding"]["agentStatus"] == "ENABLED"
assert ev["agentAfterBinding"]["onlineStatus"] == "ONLINE"
assert ev["agentAfterBinding"]["workStatus"] == "IDLE"
assert ev["simulatorHealth"]["deviceCode"] == ev["deviceCode"]
assert ev["cleanup"] == {"faultFunctionAbsent": True, "deviceStatus": "DELETED", "simulatorStopped": True}
refs = ";".join("acceptance/stage3/evidence/" + name for name in files)
date = datetime.now().astimezone().date().isoformat()

path = stage / "steps.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
for row in rows:
    if row["stepId"] == "TC-013.S1":
        assert row["status"] == "NOT_RUN"
        row.update(status="P", observedAt=date,
            actual="隔离库仅对临时设备定向注入代理编号唯一键冲突及插入异常，两次创建均500并提示稍后重试；连接测试仍PASSED、代理行均为0且无半成品。此为数据库插入层碰撞模拟，未控制UUID随机生成器",
            evidence=refs)
    if row["stepId"] == "TC-013.S2":
        assert row["status"] == "NOT_RUN"
        row.update(status="NT", observedAt=date, issue="NT-S3-023",
            actual="撤除两类注入后重试200，创建唯一启用代理并自动绑定上报为ONLINE/IDLE；再次调用仍返回同一代理且行数1。临时设备未预置已测试启用能力，能力加载至调度候选集合尚未核对",
            evidence=refs)
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

path = stage / "issues.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    assert "NT-S3-023" not in {row["编号"] for row in csv.DictReader(stream)}
with path.open("a", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["NT-S3-023", "前置缺口", "待定", "TC-013.S2", "", "待补能力候选",
        "代理故障撤除后重试创建唯一启用代理并在线绑定已证；临时设备没有预置已测试启用能力，未证明该代理的能力进入任务调度候选池",
        refs, "在隔离设备上预置有效能力、完成测试启用，重做故障恢复重试并生成任务上下文核对候选集合"])
print("recorded TC-013.S1 P and TC-013.S2 NT")
