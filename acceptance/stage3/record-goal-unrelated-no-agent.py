"""Record TC-033.S1 after verifying both independent live branches and restoration."""
import csv
import json
from datetime import datetime
from pathlib import Path

stage = Path(__file__).resolve().parent
ev = json.loads((stage / "evidence/TC-033-unrelated-no-agent.json").read_text(encoding="utf-8"))
assert "可支持范围" in ev["unrelated"]["error"]
assert ev["unrelated"]["task"]["status"] == "FAILED"
assert not ev["unrelated"]["planVersions"]
assert ev["noAgent"]["enabledOnlineCount"] == 0
assert "无启用且在线的设备代理" in ev["noAgent"]["error"]
assert ev["noAgent"]["taskIdAfter"] == ev["noAgent"]["taskIdBefore"]
assert ev["restore"]["allSixOnlineIdle"]
path = stage / "steps.csv"
with path.open(encoding="utf-8-sig", newline="") as handle:
    reader = csv.DictReader(handle)
    fields, rows = reader.fieldnames, list(reader)
row = next(item for item in rows if item["stepId"] == "TC-033.S1")
assert row["status"] == "NOT_RUN"
row.update(status="P", observedAt=datetime.now().astimezone().date().isoformat(),
           actual="范围外目标返回400及三类可支持范围，任务36标记失败且计划0；六代理全停用时返回无可用代理且未建新任务，随后六代理恢复在线空闲",
           evidence="acceptance/stage3/evidence/TC-033-unrelated-no-agent.json", issue="")
with path.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print("recorded TC-033.S1")
