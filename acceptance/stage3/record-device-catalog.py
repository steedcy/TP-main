"""Record live TC-008 form/list findings while preserving untested branches."""
import csv
import json
from pathlib import Path

here = Path(__file__).resolve().parent
ev = json.loads((here / "evidence/TC-008-device-catalog.json").read_text(encoding="utf-8"))
assert ev["defaultVirtuality"] == "真实设备"
assert ev["defaultType"] == "智慧航显"
assert ev["regionInputVisible"] and not ev["regionPresetDropdownVisible"]
assert not ev["onlineFilterVisible"] and not ev["onlineColumnVisible"]


def read(name):
    with (here / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(name, rows):
    with (here / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


steps = read("steps.csv")
for row in steps:
    if row["stepId"] == "TC-008.S1":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", observedAt="2026-10-25", issue="DEF-S3-011;DEF-S3-012",
                   actual="新增表单默认真实设备及智慧航显，非仿真体；所属区域为自由文本而非预置项。其他字段边界尚未穷尽",
                   evidence="acceptance/stage3/evidence/TC-008-device-catalog.json;acceptance/stage3/evidence/TC-008-create-defaults.png")
    elif row["stepId"] == "TC-008.S2":
        assert row["status"] == "NOT_RUN"
        row.update(status="F", observedAt="2026-10-25", issue="DEF-S3-013",
                   actual="六台在线对象列表有类型与名称/编码检索，但无在线状态筛选及在线状态列；只显示启停状态",
                   evidence="acceptance/stage3/evidence/TC-008-device-catalog.json;acceptance/stage3/evidence/TC-008-device-list.png")
write("steps.csv", steps)

issues = read("issues.csv")
for ident, step, fact, action, file in [
    ("DEF-S3-011", "TC-008.S1", "新增设备表单默认真实设备和智慧航显；原步骤要求虚实属性默认仿真体、其余录入项默认空", "按原用例设置仿真体默认并保留模拟类型必选；复测表单默认值", "TC-008-create-defaults.png"),
    ("DEF-S3-012", "TC-008.S1", "所属区域是自由文本输入而不是预置区域选项", "使用预置区域选择器并在服务端验证；复测合法/非法区域", "TC-008-create-defaults.png"),
    ("DEF-S3-013", "TC-008.S2", "设备列表缺在线状态筛选和在线状态列，仅有启停状态", "从代理/设备心跳提供在线状态并实现筛选；复测在线离线样本", "TC-008-device-list.png"),
]:
    assert ident not in {row["编号"] for row in issues}
    issues.append(dict(zip(issues[0].keys(), [ident, "缺陷", "中", step, "SRS_F003", "待修复", fact,
                                             "acceptance/stage3/evidence/" + file, action])))
write("issues.csv", issues)
