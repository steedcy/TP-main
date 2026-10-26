"""Record TC-095.S1 and NF018.R01 as NT for missing external handover."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
ev = stage / "evidence"
first = ev / "TC-095-maintenance-handover-20261026T224209Z.json"
latest = ev / "TC-095-maintenance-handover-20261026T224227Z.json"
old = json.loads(first.read_text(encoding="utf-8"))
data = json.loads(latest.read_text(encoding="utf-8"))
assert old["sourceSrs"]["sha256"] == data["sourceSrs"]["sha256"]
table = data["sourceSrs"]["maintenanceTable"]
assert all(party in table for party in
           ("系统管理员", "配置管理员", "运行操作员", "项目开发团队", "外部模型服务提供方"))
assert len(data["deliveryInventory"]) == 8
assert data["assessment"]["roleAndDeliveryMaterialsAvailable"]
assert not data["assessment"]["developerSupportHandoverVerified"]
assert not data["assessment"]["externalModelProviderCommitmentVerified"]
assert data["handoverFilenameCandidates"] == [
    "acceptance/stage0/阶段交接与门槛.md",
    "acceptance/stage1/阶段1-缺陷修复与交接.md",
    "acceptance/stage2/阶段2-环境与数据准入交接.md"]
assert data["handoverContentSearch"]["candidatePaths"] == [
    "document/formal-test-evidence/B12-detail.md"]
refs = ";".join("acceptance/stage3/evidence/" + path.name for path in (first, latest))
today = datetime.now().astimezone().date().isoformat()

def update(path, key, target, changes):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    row = next(r for r in rows if r[key] == target)
    assert row["status"] == "NOT_RUN", (target, row["status"])
    row.update(changes)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

update(stage / "steps.csv", "stepId", "TC-095.S1", dict(
    status="NT", observedAt=today,
    actual="本轮直接读取桌面SRS V1.0第1.6节，五方维护职责文字齐全；工作区README、部署手册、发布包、模型接入报告及阶段3角色/任务证据均存在。检索document与acceptance中的交接、签收、承诺类文件名及相关正文，只找到内部阶段交接和历史测试说明，未找到开发团队支持责任接收凭证或外部模型提供方可用性、固定版本维护及故障恢复承诺。不能以源码、报告和单次服务成功替代实际交付；本步待补独立交接证据。",
    evidence=refs, issue="NT-S3-025"))
update(stage / "rules.csv", "ruleId", "SRS_NF018.R01", dict(
    status="NT", verifiedBy="TC-095.S1", evidence=refs, issue="NT-S3-025"))

issues = stage / "issues.csv"
with issues.open(encoding="utf-8-sig", newline="") as stream:
    assert "NT-S3-025" not in {row["编号"] for row in csv.DictReader(stream)}
with issues.open("a", encoding="utf-8", newline="") as stream:
    csv.writer(stream, lineterminator="\n").writerow([
        "NT-S3-025", "前置缺口", "待定", "TC-095.S1", "SRS_NF018.R01", "待补交接",
        "SRS V1.0第1.6节规定五方维护职责；本轮有平台、源码、部署及模型接入材料，但工作区检索未找到开发团队技术支持责任接收或外部模型服务提供方可用性、固定版本维护和故障恢复承诺的独立交付凭证，无法确认五方职责均已交接。",
        refs,
        "提供开发支持责任/联系人/响应安排的接收记录，以及模型服务方可用性、版本维护、故障恢复与变更评审承诺或交接记录，再复核五方职责。"])

progress = stage / "阶段3-复测进度.md"
body = progress.read_text(encoding="utf-8")
body = body.replace("P 41、F 59、NT 19、未执行 81", "P 41、F 59、NT 20、未执行 80", 1)
body = body.replace("P 85、F 39、NT 9、未执行 148", "P 85、F 39、NT 10、未执行 147", 1)
heading = "## 已执行\n\n"
assert heading in body
note = ("- TC-095.S1及`SRS_NF018.R01`：本轮直接读取桌面SRS V1.0第1.6节五方维护职责，"
        "核对README、部署手册、发布包、模型接入报告和阶段3角色/任务证据；工作区交接、签收与承诺文件名及正文检索"
        "仅见内部阶段交接和历史测试说明。开发团队技术支持责任接收、外部模型服务方可用性/固定版本维护/"
        "故障恢复承诺缺独立交付凭证，不能从代码和一次调用推断实际交接，故步骤及规则均判NT（`NT-S3-025`）。"
        "两次原始清单见`evidence/TC-095-maintenance-handover-*`；未改动未跟踪`document/`。\n")
body = body.replace(heading, heading + note, 1)
body = body.replace("2026-10-27 05:49（Asia/Shanghai）", "2026-10-27 06:43（Asia/Shanghai）", 1)
progress.write_text(body, encoding="utf-8")
print("recorded TC-095.S1 NT, SRS_NF018.R01 NT, NT-S3-025")
