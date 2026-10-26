"""Record TC-006.S1 from the isolated live reset preview and role checks."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
evidence = stage / "evidence"
ui = json.loads((evidence / "TC-006-reset-preview-ui.json").read_text(encoding="utf-8"))
roles = json.loads((evidence / "TC-006-reset-menu-roles.json").read_text(encoding="utf-8"))
assert ui["adminPreviewHttpStatus"] == 200
assert ui["configPreviewHttpStatus"] == ui["operatorPreviewHttpStatus"] == 403
assert ui["preview"]["enabled"] is True
assert ui["preview"]["version"] and ui["preview"]["generatedAt"]
assert ui["preview"]["sourceDigest"] and ui["preview"]["currentContentDigest"]
assert ui["preview"]["impactScope"] and ui["preview"]["preservedScope"]
assert ui["preview"]["postResetState"] and ui["preview"]["confirmationPhraseLength"] > 0
assert ui["adminMenuVisible"] and ui["confirmationPhraseShown"]
assert len(ui["visibleFields"]) == 7
assert ui["emptyPhraseButtonDisabled"] and ui["wrongPhraseButtonDisabled"]
assert ui["correctPhraseWithAcknowledgementEnabled"]
assert "再次确认恢复" in ui["confirmationTitle"]
assert ui["modalClosedAfterCancel"] and ui["resetPostCount"] == 0
assert ui["afterVersion"] == ui["preview"]["version"]
assert ui["afterSourceDigest"] == ui["preview"]["sourceDigest"]
assert ui["afterContentDigest"] == ui["preview"]["currentContentDigest"]
for role in ("配置管理员", "运行操作员"):
    assert not roles["roles"][role]["menuVisible"]
    assert roles["roles"][role]["routeAfterDirectNavigation"] == "/overview"
    assert not roles["roles"][role]["resetCardVisible"]
refs = ";".join("acceptance/stage3/evidence/" + name for name in [
    "TC-006-reset-preview-ui.json", "TC-006-reset-menu-roles.json",
    "TC-006-reset-confirm-initial.png", "TC-006-reset-confirm-cancel.png",
    "TC-006-reset-canceled.png"])
path = stage / "steps.csv"
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    fields, rows = reader.fieldnames, list(reader)
row = next(row for row in rows if row["stepId"] == "TC-006.S1")
assert row["status"] == "NOT_RUN"
row.update(status="P", observedAt=datetime.now().astimezone().date().isoformat(),
           actual="系统管理员页面显示数据集版本、生成时间、源/当前摘要、影响和保留范围及复位后状态；配置管理员和操作员菜单不可见、直达被重定向且API403。空/错误短语禁用按钮，正确短语加确认勾选后才出现二次确认；取消无复位POST，前后版本和摘要一致。首次浏览器定位取消按钮失败截图保留，成功重试已核实取消",
           evidence=refs)
with path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print("recorded TC-006.S1")
