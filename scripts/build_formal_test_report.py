"""Build the final formal-test report from the checked result workbook.

Run only after all 95 cases have a conclusion. The source XLS and evidence
files remain untouched. This script intentionally omits account credentials,
device tokens, and model keys.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path.home() / "Documents/Codex/TIP-prep-deps"))
import xlrd
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "document/正式测试用例V2-执行结果.xls"
CASES = ROOT / ".local-test/source-review/cases.json"
REQUIREMENTS = ROOT / ".local-test/source-review/requirements.txt"
EVIDENCE = ROOT / "document/formal-test-evidence"
PROGRESS = ROOT / "document/正式测试进度-20261022.md"
OUTPUT = ROOT / "document/项目正式测试报告.docx"
FONT = "Microsoft YaHei"
INK = RGBColor(0, 0, 0)
BLUE = "DCE9F4"
PALE = "F5F8FB"
LINE = "D9D9D9"


def short(text: str, limit: int = 105) -> str:
    text = re.sub(r"\s+", " ", str(text)).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def load_data():
    case_bodies = json.loads(CASES.read_text(encoding="utf-8"))
    book = xlrd.open_workbook(str(BOOK), formatting_info=True)
    sheet = book.sheet_by_name("项目测试用例")
    if sheet.nrows != 95 * 14:
        raise ValueError("case sheet does not contain 95 unchanged case blocks")
    rows = []
    for index, body in enumerate(case_bodies):
        base = index * 14
        code = body["id"]
        if str(sheet.cell_value(base + 3, 5)) != code:
            raise ValueError(f"case order mismatch at {code}")
        result = str(sheet.cell_value(base + 7, 2)).strip()
        if result not in {"P", "F", "NT"}:
            raise ValueError(f"case {code} lacks a formal conclusion")
        steps = []
        for row in range(base + 9, base + 14):
            if str(sheet.cell_value(row, 1)).strip() == "—":
                continue
            steps.append({
                "result": str(sheet.cell_value(row, 4)).strip(),
                "note": str(sheet.cell_value(row, 5)).strip(),
            })
        refs = list(dict.fromkeys(re.findall(r"SRS_(?:F|NF)\d{3}[A-Z]?", body["description"])))
        if code in {"TC-006", "TC-007"}:
            refs.append("SRS_F002A")
        if code == "TC-017":
            refs.append("SRS_F006A")
        rows.append({"id": code, "name": body["name"], "refs": refs,
                     "result": result, "steps": steps})

    requirements = []
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        parts = [piece.strip() for piece in line.split("|")]
        if len(parts) >= 5 and re.fullmatch(r"SRS_F\d{3}[A-Z]?", parts[0]):
            requirements.append({"id": parts[0], "name": parts[1], "priority": parts[4]})
        elif len(parts) >= 5 and re.fullmatch(r"SRS_NF\d{3}", parts[0]):
            requirements.append({"id": parts[0], "name": parts[1], "priority": parts[3]})
    if len([r for r in requirements if r["id"].startswith("SRS_F")]) != 30:
        raise ValueError("functional requirement baseline must be 30")
    # The nonfunctional detailed table has four columns and does not place a
    # short name in column 2; keep the exact SRS wording as the report name.
    nf = []
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        parts = [piece.strip() for piece in line.split("|")]
        if len(parts) >= 4 and re.fullmatch(r"SRS_NF\d{3}", parts[0]):
            nf.append({"id": parts[0], "name": short(parts[2], 70), "priority": parts[3]})
    if len(nf) != 18:
        raise ValueError("nonfunctional requirement baseline must be 18")
    requirements = [r for r in requirements if r["id"].startswith("SRS_F")] + nf
    return rows, requirements


def shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def borders(cell):
    tc_pr = cell._tc.get_or_add_tcPr()
    node = tc_pr.first_child_found_in("w:tcBorders")
    if node is None:
        node = OxmlElement("w:tcBorders")
        tc_pr.append(node)
    for edge in ("top", "left", "bottom", "right"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:color"), LINE)
        node.append(element)


def cell_text(cell, value, bold=False, center=False, size=8.5):
    cell.text = str(value)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    for para in cell.paragraphs:
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
        para.paragraph_format.space_after = Pt(0)
        para.paragraph_format.line_spacing = 1.14
        for run in para.runs:
            run.bold = bold
            run.font.name = FONT
            run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
            run.font.size = Pt(size)
            run.font.color.rgb = INK
    borders(cell)
    margins = cell._tc.get_or_add_tcPr()
    mar = margins.first_child_found_in("w:tcMar")
    if mar is None:
        mar = OxmlElement("w:tcMar")
        margins.append(mar)
    for edge in ("top", "left", "bottom", "right"):
        elem = OxmlElement(f"w:{edge}")
        elem.set(qn("w:w"), "90" if edge in ("top", "bottom") else "100")
        elem.set(qn("w:type"), "dxa")
        mar.append(elem)


def table(doc, headers, records, widths, text_size=8.5):
    t = doc.add_table(rows=1, cols=len(headers))
    t.autofit = False
    t.style = "Table Grid"
    for idx, (title, width) in enumerate(zip(headers, widths)):
        t.columns[idx].width = Inches(width)
        cell_text(t.rows[0].cells[idx], title, bold=True, center=True, size=text_size)
        shade(t.rows[0].cells[idx], BLUE)
    header_pr = t.rows[0]._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    header_pr.append(repeat)
    for row_idx, values in enumerate(records):
        cells = t.add_row().cells
        for idx, val in enumerate(values):
            cell_text(cells[idx], val, center=(idx == 0 or str(val) in {"P", "F", "NT"}), size=text_size)
            if row_idx % 2:
                shade(cells[idx], PALE)
    for row in t.rows:
        row_pr = row._tr.get_or_add_trPr()
        row_pr.append(OxmlElement("w:cantSplit"))
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return t


def heading(doc, text, level=1):
    p = doc.add_paragraph(text, style=f"Heading {level}")
    p.paragraph_format.keep_with_next = True
    return p


def para(doc, text, bold_lead=None):
    p = doc.add_paragraph()
    if bold_lead:
        r = p.add_run(bold_lead)
        r.bold = True
    p.add_run(text)
    return p


def status_for_requirement(code, by_ref):
    linked = by_ref.get(code, [])
    values = [r["result"] for r in linked]
    if not values:
        return "未覆盖"
    if "F" in values:
        return "F"
    if "NT" in values:
        return "NT"
    return "P"


def add_page_number(section):
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("第 ")
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    run._r.addnext(fld)
    p.add_run(" 页")


def build(rows, reqs, report_date: str, stability: str):
    counts = Counter(r["result"] for r in rows)
    by_ref = defaultdict(list)
    for row in rows:
        for ref in row["refs"]:
            by_ref[ref].append(row)
    req_counts = Counter(status_for_requirement(r["id"], by_ref) for r in reqs)
    doc = Document()
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.72)
    section.bottom_margin = Inches(0.68)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)
    add_page_number(section)

    styles = doc.styles
    for style_name, size, bold, before, after in [
        ("Normal", 10.5, False, 0, 6),
        ("Title", 19, True, 0, 15),
        ("Heading 1", 13.5, True, 15, 6),
        ("Heading 2", 11.5, True, 11, 4),
    ]:
        style = styles[style_name]
        style.font.name = FONT
        style.font.size = Pt(size)
        style.font.bold = bold
        style.font.color.rgb = INK
        style._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.line_spacing = 1.18
    title_pr = styles["Title"]._element.get_or_add_pPr()
    title_border = title_pr.find(qn("w:pBdr"))
    if title_border is not None:
        title_pr.remove(title_border)

    doc.add_paragraph("项目正式测试报告", style="Title")
    para(doc, f"项目：面向智慧机场的人工智能集群协同服务关键技术研究\n报告日期：{report_date}\n需求基线：2026年9月10日《需求规格说明书》V1.0\n测试边界：30项功能需求、18项非功能需求、原表95条测试用例")
    para(doc, "本报告汇总本机系统及四类实体设备对应仿真体的正式测试结果。结论来自逐步骤执行记录、原始请求与事件、浏览器截图和结果工作簿；未执行或证据不足的步骤均标为待验证。")
    para(doc, f"95条用例中，通过{counts['P']}条、失败{counts['F']}条、待验证{counts['NT']}条。按至少一条失败即需求未通过的汇总规则，48项需求中通过{req_counts['P']}项、含失败用例{req_counts['F']}项、仅有未覆盖步骤{req_counts['NT']}项、无关联用例{req_counts['未覆盖']}项。当前不能据此宣布项目已满足完整需求基线。")

    heading(doc, "一 测试依据与结论口径")
    para(doc, "唯一需求依据为用户指定的2026年9月10日V1.0规格说明书。测试步骤与预期沿用《测试用例V2.xls》95条原文；《总体测试计划V2.doc》用于环境、阶段与记录口径。SRS_F002A和SRS_F006A分别纳入独立需求编号，功能需求因此为30项。")
    para(doc, "P表示该用例全部要求步骤及分支都有符合预期的实测证据；F表示至少一个预期被实际结果否定；NT表示尚有必须执行的步骤或前置条件未覆盖，且没有已证实不符合项。需求级结论取其关联用例中最严格的状态：任一F则F；否则任一NT则NT；全部P才为P。该状态描述本轮验证结果，并不等同于静态源码实现判定。")
    table(doc, ["对象", "数量", "通过 P", "失败 F", "待验证 NT"], [
        ("测试用例", "95", str(counts["P"]), str(counts["F"]), str(counts["NT"])),
        ("功能需求", "30", str(sum(status_for_requirement(r["id"], by_ref) == "P" for r in reqs if r["id"].startswith("SRS_F"))), str(sum(status_for_requirement(r["id"], by_ref) == "F" for r in reqs if r["id"].startswith("SRS_F"))), str(sum(status_for_requirement(r["id"], by_ref) == "NT" for r in reqs if r["id"].startswith("SRS_F")))),
        ("非功能需求", "18", str(sum(status_for_requirement(r["id"], by_ref) == "P" for r in reqs if r["id"].startswith("SRS_NF"))), str(sum(status_for_requirement(r["id"], by_ref) == "F" for r in reqs if r["id"].startswith("SRS_NF"))), str(sum(status_for_requirement(r["id"], by_ref) == "NT" for r in reqs if r["id"].startswith("SRS_NF")))),
    ], [1.6, 0.65, 1.5, 1.5, 1.55], 9)

    heading(doc, "二 环境 方法与证据")
    para(doc, "测试在本机单套开发验证环境执行：前端、后端、PostgreSQL、Redis及Moonshot/Kimi规划服务共同运行。四类实体设备由航班信息、信息显示、行李扫描和移动机器人仿真体及其设备代理替代；部分规模与候选切换测试使用同类多实例，共观察20对象状态上报。兼容性检查使用本机Chrome和Edge。")
    para(doc, "每批不超过10条用例，单独聊天与独立批次证据记录。先执行B01至B12覆盖除8小时稳定性外的94条，再通过R01及后续复测补充缺失分支。浏览器交互、API请求响应、数据库只读核验、任务事件、代理反馈和可控离线/失败/超时注入分别用于对应步骤；仿真夹具证据仅证明受控分支，不作为真实模型质量或实体硬件性能证据。")
    para(doc, "可追溯资料位于 document/formal-test-evidence；每个批次的 detail.md、results.json 和原始证据文件保留。连续结果工作簿为 document/正式测试用例V2-执行结果.xls；桌面原始95条工作簿没有修改。敏感账号、口令、设备令牌与模型密钥未列入报告。")
    para(doc, "证据复核纠正了一项重要误判：R03/R04若干任务的GOAL_CLARIFIED事件含INFO_INCOMPLETE及明确的待补充问题，等待补充时不生成规划快照属于流程规定；不能仅凭PLANNING状态认定规划服务故障。有关原始事件、更正文字及补测记录均保留，最终结论以本报告及最新工作簿为准。")
    para(doc, "R07期间按原需求补齐三份预置基线，并由管理接口真实试运行通过后启用超规行李V1.6、特殊旅客V1.10、航班变更V1.8。修订前配置和失败结果均保留；修订后真实Kimi及仿真设备仍观察到展示步骤被派给航延屏而非智慧航显，以及超规判定阈值来源缺失，故不能以模板试运行或任务COMPLETED状态代替场景验收。")
    heading(doc, "执行批次与结果回填", 2)
    batches = []
    for line in PROGRESS.read_text(encoding="utf-8").splitlines():
        if not re.match(r"\| (?:B|R)\d{2} \|", line):
            continue
        parts = [piece.strip() for piece in line.strip("|").split("|")]
        if len(parts) >= 7 and parts[3].startswith("已"):
            batches.append((parts[0], short(parts[1], 35), parts[4], parts[5], parts[6]))
    batch_order = {**{f"B{i:02d}": i for i in range(1, 13)},
                   **{f"R{i:02d}": 12 + i for i in range(1, 8)},
                   "B13": 20}
    batches.sort(key=lambda row: batch_order.get(row[0], 99))
    table(doc, ["批次", "用例范围", "P", "F", "NT"], batches,
          [0.70, 4.15, 0.65, 0.65, 0.75], 8.5)
    para(doc, "补测批次与首轮批次可能覆盖同一用例，表内各批次数不得相加。唯一最终统计以结果工作簿每条用例的最新结论为准。所有修订前版本另存备份，批次详情保留原始观察与更正说明。")

    heading(doc, "三 需求追踪与验证状态")
    for label, items in [("功能需求 30项", [r for r in reqs if r["id"].startswith("SRS_F")]),
                         ("非功能需求 18项", [r for r in reqs if r["id"].startswith("SRS_NF")])]:
        heading(doc, label, 2)
        table(doc, ["需求编号", "需求名称或核心要求", "对应测试用例", "结论"], [
            (r["id"], short(r["name"], 64), "、".join(x["id"].removeprefix("TC-") for x in by_ref[r["id"]]) or "—", status_for_requirement(r["id"], by_ref))
            for r in items
        ], [1.12, 2.95, 2.18, 0.65], 8.1)

    heading(doc, "四 失败用例与缺陷处理")
    para(doc, f"本轮有{counts['F']}条失败用例。多条用例可能指向同一根因，故失败用例数不作为独立缺陷数。以下逐条列出已观察到的不符合项，完整步骤结果与请求、事件和截图以结果工作簿及批次证据为准。修复后须在相同基线、相同或等效数据下复测相关用例及相邻流程。")
    failures = []
    for row in rows:
        if row["result"] != "F":
            continue
        failing = next((s["note"] for s in row["steps"] if s["result"] == "F"), "见结果工作簿")
        failures.append((row["id"], row["name"], "、".join(row["refs"]), short(failing, 115)))
    table(doc, ["用例", "检查点", "需求", "已确认差异摘要"], failures,
          [0.68, 1.45, 1.10, 3.67], 7.9)

    heading(doc, "五 待验证用例与补测条件")
    para(doc, f"{counts['NT']}条用例仍有必测步骤缺少执行证据。下列摘要只列未覆盖的主要原因；某些用例的其他步骤已经通过，但不能因此将整条用例改记P。")
    untested = []
    for row in rows:
        if row["result"] != "NT":
            continue
        pending = next((s["note"] for s in row["steps"] if s["result"] == "NT"), "见结果工作簿")
        untested.append((row["id"], row["name"], short(pending, 130)))
    table(doc, ["用例", "检查点", "仍需补测的主要条件"], untested,
          [0.70, 1.60, 4.60], 8.1)

    heading(doc, "六 8小时稳定性专项")
    para(doc, stability)

    heading(doc, "七 修复与再验证安排")
    para(doc, "先由项目开发团队按用例失败证据定位并修复核心流程与安全边界，配置管理员同步核对四类仿真体、三份基线、能力和场景数据。随后由测试执行方复测所有受影响用例与相邻流程，先补齐三类场景冒烟，再执行需要连续观察的稳定性专项。系统管理员配合账号、审计及恢复核验；模型服务提供方仅负责其接口可用性和返回数据问题。责任分工是报告建议，具体负责人由项目方确认。")
    table(doc, ["顺序", "工作", "建议责任", "完成判据"], [
        ("1", "修复已确认的流程、权限、状态和页面差异", "项目开发团队", "每条失败用例回归P或保留新失败证据"),
        ("2", "补齐可控故障、同族模板、设备反馈和页面场景", "配置管理员与测试执行方", "所有NT步骤具备可重复前置条件并实测"),
        ("3", "复核四类仿真体与三核心场景冒烟", "配置管理员与测试执行方", "三类正常核心任务均完成且追溯可查"),
        ("4", "复测8小时稳定性与恢复", "测试执行方与系统管理员", "记录真实连续起止时间、任务结果和故障"),
        ("5", "外部职责与交付凭据确认", "项目开发团队与服务提供方", "交接文件、职责和运行记录可核对"),
    ], [0.45, 2.2, 1.55, 2.70], 8.2)

    heading(doc, "附录 95条用例结论索引")
    table(doc, ["用例", "名称", "需求映射", "结论"], [
        (r["id"], r["name"], "、".join(r["refs"]), r["result"]) for r in rows
    ], [0.70, 3.05, 2.45, 0.70], 8.0)

    heading(doc, "证据与文件位置")
    para(doc, "原始需求：桌面《20260910-面向智慧机场的人工智能集群协同服务关键技术研究-需求规格说明书-V1.0.docx》。原始计划与用例：桌面《总体测试计划V2.doc》《测试用例V2.xls》。结果工作簿：tip/document/正式测试用例V2-执行结果.xls。批次索引：tip/document/正式测试进度-20261022.md。批次原始记录：tip/document/formal-test-evidence。")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT)
    return {"output": str(OUTPUT), "cases": dict(counts), "requirements": dict(req_counts), "pages_unverified": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--stability-file", type=Path, required=True)
    args = parser.parse_args()
    rows, requirements = load_data()
    summary = build(rows, requirements, args.date, args.stability_file.read_text(encoding="utf-8"))
    print(json.dumps(summary, ensure_ascii=False))
