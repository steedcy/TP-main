"""Generate the stage-0 trace from the supplied, read-only baseline extracts.

Run with the bundled Python runtime. This does not change source workbooks.
"""
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SRC = ROOT / '.local-test/source-review'
sys.path.insert(0, str(Path.home() / 'Documents/Codex/TIP-prep-deps'))
import xlrd


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(name, fields, rows):
    with (OUT / name).open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(rows)


requirement_text = (SRC / 'requirements.txt').read_text(encoding='utf-8')
cases = json.loads((SRC / 'cases.json').read_text(encoding='utf-8'))
book_path = ROOT / 'document/正式测试用例V2-执行结果.xls'
sheet = xlrd.open_workbook(str(book_path)).sheet_by_name('项目测试用例')
assert len(cases) == 95

# Source-case group boundaries are copied from the original V2 plan, with the
# two A-numbered requirements restored as separate requirements.
groups = [
    ('F001', 1, 3), ('F002', 4, 5), ('F002A', 6, 7),
    ('F003', 8, 10), ('F004', 11, 13), ('F005', 14, 16),
    ('F006A', 17, 19), ('F006', 20, 22), ('F007', 23, 24),
    ('F008', 25, 27), ('F009', 28, 30), ('F010', 31, 34),
    ('F011', 35, 36), ('F012', 37, 38), ('F013', 39, 42),
    ('F014', 43, 46), ('F015', 47, 50), ('F016', 51, 53),
    ('F017', 54, 56), ('F018', 57, 59), ('F019', 60, 62),
    ('F020', 63, 65), ('F021', 66, 67), ('F022', 68, 69),
    ('F023', 70, 71), ('F024', 72, 76), ('F025', 77, 79),
    ('F026', 80, 83), ('F027', 84, 84), ('F028', 85, 85),
]
nf_cases = {
    'NF001': [86], 'NF002': [87], 'NF003': [31, 77, 86],
    'NF004': [3, 85, 86], 'NF005': [24, 40, 56],
    'NF006': [88], 'NF007': [88], 'NF008': [37, 47],
    'NF009': [89], 'NF010': [90], 'NF011': [91],
    'NF012': [90], 'NF013': [92], 'NF014': [93],
    'NF015': [47, 56], 'NF016': [2], 'NF017': [94],
    'NF018': [95],
}
case_map = {f'SRS_{key}': [f'TC-{n:03}' for n in range(start, end + 1)] for key, start, end in groups}
case_map.update({f'SRS_{key}': [f'TC-{n:03}' for n in nums] for key, nums in nf_cases.items()})

result = {}
steps = []
for index, case in enumerate(cases):
    base = index * 14
    case_id = case['id']
    conclusion = str(sheet.cell_value(base + 7, 2)).strip()
    assert case_id == f'TC-{index+1:03}' and conclusion in ('P', 'F', 'NT')
    result[case_id] = conclusion
    active = [r for r in range(base + 9, base + 14) if str(sheet.cell_value(r, 1)).strip() != '—']
    assert len(active) == len(case['steps'])
    for number, (row, step) in enumerate(zip(active, case['steps']), 1):
        steps.append({
            '用例': case_id, '步骤': f'{case_id}.S{number}', '用例名称': case['name'],
            '前置条件': case['preconditions'], '操作': step['action'],
            '预期': step['expected'], '首轮及R07后结果': conclusion,
            '历史步骤结果': str(sheet.cell_value(row, 4)).strip(),
            '历史备注': str(sheet.cell_value(row, 5)).strip(),
            '下一轮状态': '必须按冻结版本完整复测',
        })
assert {v: list(result.values()).count(v) for v in ('P', 'F', 'NT')} == {'P': 23, 'F': 51, 'NT': 21}
write_csv('用例逐步执行口径-V2.1.csv', list(steps[0]), steps)

source_lines = requirement_text.splitlines()
starts = [(i, re.search(r'需求编号：(SRS_F\d{3}A?)', line).group(1))
          for i, line in enumerate(source_lines)
          if re.search(r'需求编号：(SRS_F\d{3}A?)', line)]
starts = [(i, code) for i, code in starts if i > 250]
assert len(starts) == 30, starts
reqs = {}
for pos, (start, code) in enumerate(starts):
    end = starts[pos + 1][0] if pos + 1 < len(starts) else next(i for i, line in enumerate(source_lines) if i > start and line.startswith('六、非功能需求'))
    chunk = source_lines[start:end]
    title = source_lines[start - 1].split(' | ')[0].removeprefix('功能需求名称：')
    rule_start = chunk.index('业务规则') + 2
    rule_end = chunk.index('流程描述')
    rules = [m.group(2) for line in chunk[rule_start:rule_end]
             if (m := re.match(r'^(\d+) \| (.+)$', line))]
    assert rules, code
    reqs[code] = (title, rules)
nf_lines = [line for line in source_lines if re.match(r'^SRS_NF\d{3} \|', line)]
assert len(nf_lines) == 18
for line in nf_lines:
    code, title, rule, *_ = line.split(' | ')
    reqs[code] = (title, [rule])

evidence_dir = ROOT / 'document/formal-test-evidence'
remediation_dir = ROOT / 'remediation'
remediation_docs = sorted(remediation_dir.glob('*.md'))
remediation_text = {p: p.read_text(encoding='utf-8') for p in remediation_docs}
rows = []
def similarity(a, b):
    # Rank only within a requirement's original steps. The result is an
    # inspection aid; the full original action and expectation remain in the
    # adjacent step sheet, and a low score is not treated as coverage.
    stop = {'系统', '任务', '设备', '结果', '状态', '步骤', '记录', '信息', '显示', '进行'}
    def grams(value):
        value = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', value)
        return {value[i:i+2] for i in range(len(value)-1)} - stop
    x, y = grams(a), grams(b)
    return len(x & y) / max(1, len(x | y))

for code, (title, rules) in reqs.items():
    ids = case_map[code]
    related_steps = [s for s in steps if s['用例'] in ids]
    remediation = [p.relative_to(ROOT).as_posix() for p, body in remediation_text.items()
                   if any(case_id in body for case_id in ids)]
    first = int(ids[0][3:])
    batch = next((name for name, lo, hi in [
        ('B01', 1, 7), ('B02', 8, 16), ('B03', 17, 24), ('B04', 25, 34),
        ('B05', 35, 42), ('B06', 43, 50), ('B07', 51, 59), ('B08', 60, 69),
        ('B09', 70, 79), ('B10', 80, 87), ('B11', 88, 90),
        ('B13', 91, 91), ('B12', 92, 95)] if lo <= first <= hi), '')
    for n, rule in enumerate(rules, 1):
        ranked = sorted(related_steps, key=lambda s: similarity(rule, s['操作'] + s['预期']), reverse=True)
        primary = ranked[0]
        score = similarity(rule, primary['操作'] + primary['预期'])
        rows.append({
            '需求编号': code, '需求名称': title, '规则编号': f'{code}.R{n:02}',
            '具体规则（原文）': rule, '关联原用例': '、'.join(ids),
            '关联步骤（需求级候选，需按规则核验）': '、'.join(s['步骤'] for s in related_steps),
            '优先核验步骤（文本匹配建议）': primary['步骤'],
            '优先步骤操作': primary['操作'], '优先步骤预期': primary['预期'],
            '文本匹配分数': f'{score:.3f}',
            '操作与预期索引': '用例逐步执行口径-V2.1.csv',
            '夹具/前置（原用例）': ' | '.join(dict.fromkeys(s['前置条件'] for s in related_steps)),
            '历史结果': '、'.join(f'{case_id}:{result[case_id]}' for case_id in ids),
            '第一轮证据': f'document/formal-test-evidence/{batch}-detail.md',
            '定向整改依据': '；'.join(remediation),
            '缺陷与待办索引': '阶段0-遗留与裁决.md；用例状态与证据索引-V2.1.csv',
            '覆盖判定': '低匹配，需独立子检查或裁决' if score < .08 else '需求级关联；规则对应子检查须在复测时逐项证实',
        })
write_csv('30功能18非功能-规则追踪矩阵-V2.1.csv', list(rows[0]), rows)

case_rows = []
for case in cases:
    case_id = case['id']
    n = int(case_id[3:])
    owner = [code for code, ids in case_map.items() if case_id in ids]
    batch = next(name for name, lo, hi in [
        ('B01', 1, 7), ('B02', 8, 16), ('B03', 17, 24), ('B04', 25, 34),
        ('B05', 35, 42), ('B06', 43, 50), ('B07', 51, 59),
        ('B08', 60, 69), ('B09', 70, 79), ('B10', 80, 87),
        ('B11', 88, 90), ('B13', 91, 91), ('B12', 92, 95)] if lo <= n <= hi)
    r_files = sorted(p.name for p in evidence_dir.glob('R*-detail.md')
                     if case_id in p.read_text(encoding='utf-8'))
    fix_docs = [p.relative_to(ROOT).as_posix() for p, body in remediation_text.items() if case_id in body]
    state = '待完整复测（历史P，复核未测子项）' if result[case_id] == 'P' else (
        '待修复并完整复测' if result[case_id] == 'F' else '前置/分支/证据待补并完整复测')
    if case_id == 'TC-031': state = '重开：动态场景参数与TC-068矛盾，按F处理并复测'
    case_rows.append({
        '用例': case_id, '名称': case['name'], '关联需求': '、'.join(owner),
        '历史结论': result[case_id], '阶段0状态': state,
        '原用例步骤数': len(case['steps']),
        '第一轮证据': f'document/formal-test-evidence/{batch}-detail.md',
        '定向轮次': '、'.join(r_files), '整改检查点': '、'.join(fix_docs),
        '原始结果簿': 'document/正式测试用例V2-执行结果.xls',
        '下一动作': '依据步骤表逐步执行，记录实际结果、时间、证据与缺陷；不可沿用历史P',
    })
write_csv('用例状态与证据索引-V2.1.csv', list(case_rows[0]), case_rows)

defect_files = sorted(evidence_dir.glob('B*-detail.md')) + sorted(evidence_dir.glob('R*-detail.md'))
defects = {}
for path in defect_files:
    for line_number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        for defect_id in re.findall(r'DEF-(?:B\d{2}|R\d{2})-\d{3}', line):
            if defect_id not in defects:
                defects[defect_id] = {
                    '缺陷编号': defect_id, '首次记录': f'{path.relative_to(ROOT).as_posix()}:{line_number}',
                    '原文摘录': line.strip().strip('| ')[:500],
                    '关联用例（原文命中）': '、'.join(dict.fromkeys(re.findall(r'TC-\d{3}', line))),
                    '阶段0处置': '保持打开：定向修复需核对，原用例和邻接流程尚未按冻结版本完整复测',
                    '整改依据（若有）': '、'.join(p.relative_to(ROOT).as_posix() for p, body in remediation_text.items() if defect_id in body),
                }
assert len(defects) == 50, len(defects)
write_csv('历史缺陷索引-V2.1.csv', list(next(iter(defects.values()))), list(defects.values()))

sources = [
    Path.home() / 'Desktop/20260910-面向智慧机场的人工智能集群协同服务关键技术研究-需求规格说明书-V1.0.docx',
    Path.home() / 'Desktop/总体测试计划V2.doc',
    Path.home() / 'Desktop/测试用例V2.xls',
    Path.home() / 'Desktop/人工智能集群协同服务平台-95项测试验收与人工演示实施方案-20261025.docx',
    book_path,
]
(OUT / 'source-manifest.json').write_text(json.dumps({
    'source_sha256': {str(p): sha(p) for p in sources},
    'requirements': len(reqs), 'functional': len(starts), 'nonfunctional': len(nf_lines),
    'business_rule_rows': len(rows), 'original_cases': len(cases), 'historical_defect_ids': len(defects),
    'original_steps': len(steps), 'historical_results': {v: list(result.values()).count(v) for v in ('P', 'F', 'NT')},
}, ensure_ascii=False, indent=2), encoding='utf-8')
runtime_evidence = ROOT / 'remediation/evidence'
browser = json.loads((runtime_evidence / 'environment-browser-compatibility-20261025.json').read_text(encoding='utf-8'))
snapshot = json.loads((runtime_evidence / 'environment-final-snapshot-20261025.json').read_text(encoding='utf-8'))
source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
f2_files = sorted((ROOT / 'backend/src/main/resources/demo-f2').glob('*.json'))
migrations = sorted((ROOT / 'backend/src/main/resources/db/migration').glob('V*.sql'))
(OUT / 'frozen-baseline.json').write_text(json.dumps({
    'phase0_source_commit': source_commit,
    'source_tag': 'V1.2',
    'software_sha': source_commit,
    'database': {
        'migration_files_latest': 'V16',
        'migration_sha256': {p.name: sha(p) for p in migrations},
        'runtime_schema_version': 'historical evidence says V16 applied; stage2 must query Flyway history again',
    },
    'f2': {
        'dataset_version': 'F2-DEMO-20261024',
        'resource_sha256': {p.name: sha(p) for p in f2_files},
        'runtime_snapshot_at': snapshot['recordedAt'],
        'runtime_template_versions': {p['templateIntent']: p['templateVersion'] for p in snapshot['presetTemplates']},
        'runtime_agents': [p['deviceCode'] for p in snapshot['originalAgents']],
    },
    'simulator': {'source_commit': source_commit, 'historical_instances': len(snapshot['simulators']),
                  'runtime_binary_hash': 'unverified; stage2 capture built JAR SHA-256'},
    'model': {'source_default_identifier': 'kimi-k2.6', 'historical_provider': 'Moonshot/Kimi',
              'runtime_identifier_endpoint_parameters': 'unverified; stage2 capture masked live config and request metadata'},
    'browser_historical': sorted({f"{c['browser']} {c['version']}" for c in browser['cases']}),
    'browser_stage3': 'capture installed versions again at execution',
}, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'requirements': len(reqs), 'rules': len(rows), 'cases': len(cases), 'steps': len(steps)}, ensure_ascii=False))
