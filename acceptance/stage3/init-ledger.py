"""Create the stage-3 execution register without carrying forward old verdicts.

Run once against the frozen stage-0 inputs. Execution evidence is added
separately; a row marked NOT_RUN is never counted as a retest.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "acceptance/stage0"
OUT = Path(__file__).resolve().parent


def read_csv(name):
    with (BASE / name).open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


steps = read_csv("用例逐步执行口径-V2.1.csv")
rules = read_csv("30功能18非功能-规则追踪矩阵-V2.1.csv")
cases = read_csv("用例状态与证据索引-V2.1.csv")
assert len(steps) == 200 and len(rules) == 281 and len(cases) == 95
assert len({row["步骤"] for row in steps}) == 200
assert len({row["规则编号"] for row in rules}) == 281
assert len({row["用例"] for row in cases}) == 95

step_rows = [{
    "stepId": row["步骤"], "caseId": row["用例"],
    "action": row["操作"], "expected": row["预期"],
    "status": "NOT_RUN", "observedAt": "", "actual": "",
    "evidence": "", "issue": "",
} for row in steps]
rule_rows = [{
    "ruleId": row["规则编号"], "requirement": row["需求编号"],
    "text": row["具体规则（原文）"],
    "candidateStep": row["优先核验步骤（文本匹配建议）"],
    "status": "NOT_RUN", "verifiedBy": "", "evidence": "", "issue": "",
} for row in rules]
ac_rows = [{"acId": f"AC-{n:03}", "status": "NOT_RUN",
            "observedAt": "", "actual": "", "evidence": "", "issue": ""}
           for n in range(1, 28)]

OUT.mkdir(exist_ok=True)
for name, rows in (("steps.csv", step_rows), ("rules.csv", rule_rows),
                   ("ac.csv", ac_rows)):
    path = OUT / name
    if path.exists():
        raise SystemExit(f"Refusing to overwrite {path}")
    with path.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
manifest = {"source": "V1.5", "sourceCommit": "0d798ceb53bc37498f353b4796f2081b92e2011b",
            "steps": len(steps), "cases": len(cases), "rules": len(rules),
            "additionalChecks": len(ac_rows),
            "warning": "All rows start NOT_RUN; historical results and stage-2 smoke are excluded."}
(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(manifest, ensure_ascii=False))
