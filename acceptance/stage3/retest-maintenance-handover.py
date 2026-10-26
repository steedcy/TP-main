"""TC-095.S1: fresh SRS 1.6 duties and local delivery evidence inventory."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(__file__).resolve().parent
source = Path(r"C:\Users\savy\Desktop\20260910-面向智慧机场的人工智能集群协同服务关键技术研究-需求规格说明书-V1.0.docx")
assert source.is_file()
ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
with zipfile.ZipFile(source) as archive:
    xml = ET.fromstring(archive.read("word/document.xml"))
lines = ["".join(paragraph.itertext()).strip() for paragraph in xml.findall(".//w:p", ns)]
start = next(i for i, line in enumerate(lines) if line == "运行维护职责")
assert lines[start + 1:start + 13] == [
    "责任方", "维护职责",
    "系统管理员", "账号、角色、基础配置、账号解锁和操作记录管理",
    "配置管理员", "设备、设备代理、能力边界、能力画像、基线模板、任务定义和风险规则维护",
    "运行操作员", "日常任务提交、监控、异常处置和业务终止",
    "项目开发团队", "软件缺陷修复、版本发布和技术支持",
    "外部模型服务提供方", "模型服务可用性、固定版本维护和服务故障恢复；版本变更须配合项目变更评审"]

artifacts = [
    "README.md", "document/部署实施手册.md",
    "backend/target/airport-ai-app-1.0.0.jar",
    "document/Kimi规划模型服务接入核查报告-20261022.md",
    "acceptance/stage3/evidence/TC-003-role-menus.json",
    "acceptance/stage3/evidence/TC-064-pending-manual-ui.json",
    "acceptance/stage3/evidence/TC-066-terminate-live-20261026T174242Z.json",
    "acceptance/stage3/evidence/TC-084-trace-permissions-20261026T204811Z.json",
]
inventory = []
for relative in artifacts:
    path = root / relative
    inventory.append({"path": relative, "exists": path.is_file(),
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None})

name_pattern = re.compile(r"签收|交接|承诺|维护协议|技术支持|SLA", re.IGNORECASE)
candidates = sorted(str(path.relative_to(root)).replace("\\", "/")
                    for parent in (root / "document", root / "acceptance")
                    for path in parent.rglob("*") if path.is_file() and name_pattern.search(path.name))
content_pattern = re.compile(r"签收人|服务级别承诺|服务提供方.{0,30}承诺|支持联系人|故障恢复.{0,30}承诺")
text_files = [root / "README.md", *(root / "document").rglob("*.md"),
              *(root / "acceptance/stage1").rglob("*.md"),
              *(root / "acceptance/stage2").rglob("*.md")]
content_candidates = sorted(str(path.relative_to(root)).replace("\\", "/")
                            for path in text_files if path.is_file() and
                            content_pattern.search(path.read_text(encoding="utf-8", errors="replace")))
ev = {"observedAt": datetime.now(timezone.utc).isoformat(),
      "sourceSrs": {"path": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                    "heading": lines[start - 1], "maintenanceTable": lines[start:start + 13]},
      "deliveryInventory": inventory,
      "handoverFilenameSearchScope": ["document/", "acceptance/"],
      "handoverFilenameCandidates": candidates,
      "handoverContentSearch": {"textFileCount": len(text_files),
                                 "patterns": content_pattern.pattern,
                                 "candidatePaths": content_candidates},
      "assessment": {
          "roleAndDeliveryMaterialsAvailable": all(item["exists"] for item in inventory),
          "developerSupportHandoverVerified": False,
          "externalModelProviderCommitmentVerified": False,
          "reason": "本轮检索到内部阶段交接和部署/模型接入说明，但未找到开发团队技术支持责任接收或外部模型服务提供方可用性、固定版本维护与故障恢复承诺的独立交付凭证；文件名检索范围限本工作区。"}}
out = stage / "evidence" / ("TC-095-maintenance-handover-" +
                            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out), "maintenanceParties": 5,
                  "availableMaterials": sum(item["exists"] for item in inventory),
                  "candidateNames": candidates,
                  "contentCandidates": content_candidates,
                  "developerSupportHandoverVerified": False,
                  "externalModelProviderCommitmentVerified": False}, ensure_ascii=False))
