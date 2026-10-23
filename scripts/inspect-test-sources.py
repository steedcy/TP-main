"""Read the supplied baseline files without modifying the originals."""
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "Documents/Codex/TIP-prep-deps"))
import xlrd
import olefile
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".local-test/source-review"
OUT.mkdir(parents=True, exist_ok=True)
desktop = Path.home() / "Desktop"

workbook = xlrd.open_workbook(str(desktop / "测试用例V2.xls"))
sheets = []
for sheet in workbook.sheets():
    rows = [[str(sheet.cell_value(r, c)).strip() for c in range(sheet.ncols)] for r in range(sheet.nrows)]
    sheets.append({"name": sheet.name, "rows": rows})
(OUT / "test-cases.json").write_text(json.dumps(sheets, ensure_ascii=False, indent=2), encoding="utf-8")
rows = next(s["rows"] for s in sheets if s["name"] == "项目测试用例")
cases = [{"id": rows[i + 3][5], "name": rows[i + 3][2], "preconditions": rows[i + 2][2],
          "description": rows[i + 4][2], "steps": [{"action": row[2], "expected": row[3]}
          for row in rows[i + 9:i + 14] if row[1] != "—"]} for i in range(0, len(rows), 14)]
(OUT / "cases.json").write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"caseCount": len(cases), "sheets": [s["name"] for s in sheets]}, ensure_ascii=False))

source = desktop / "20260910-面向智慧机场的人工智能集群协同服务关键技术研究-需求规格说明书-V1.0.docx"
document = Document(str(source))
blocks = []
for child in document.element.body:
    if child.tag.endswith("}p"):
        blocks.append(Paragraph(child, document).text)
    elif child.tag.endswith("}tbl"):
        table = Table(child, document)
        blocks.extend(" | ".join(c.text for c in row.cells) for row in table.rows)
text = "\n".join(blocks)
(OUT / "requirements.txt").write_text(text, encoding="utf-8")
print(json.dumps({"requirementsChars": len(text), "tables": len(document.tables)}, ensure_ascii=False))

with olefile.OleFileIO(str(desktop / "总体测试计划V2.doc")) as ole:
    data = ole.openstream("WordDocument").read()
    flags = struct.unpack_from("<H", data, 10)[0]
    table = ole.openstream("1Table" if flags & 0x200 else "0Table").read()
    # FibRgFcLcb97's fcClx/lcbClx describe the piece table, including mixed compressed/Unicode text.
    offset = 32
    count = struct.unpack_from("<H", data, offset)[0]
    offset += 2 + count * 2
    count = struct.unpack_from("<H", data, offset)[0]
    offset += 2 + count * 4
    pair_count = struct.unpack_from("<H", data, offset)[0]
    offset += 2
    assert pair_count > 33, "Unsupported Word FIB"
    fc, length = struct.unpack_from("<II", data, offset + 33 * 8)
    clx = table[fc:fc + length]
    index = 0
    while index < len(clx) and clx[index] == 1:
        index += 3 + struct.unpack_from("<H", clx, index + 1)[0]
    assert clx[index] == 2, "Word piece table missing"
    size = struct.unpack_from("<I", clx, index + 1)[0]
    pieces = clx[index + 5:index + 5 + size]
    n = (size - 4) // 12
    parts = []
    for i in range(n):
        first, last = struct.unpack_from("<II", pieces, i * 4)
        compressed_fc = struct.unpack_from("<I", pieces, (n + 1) * 4 + i * 8 + 2)[0]
        file_offset = compressed_fc & 0x3fffffff
        compressed = bool(compressed_fc & 0x40000000)
        if compressed:
            parts.append(data[file_offset // 2:file_offset // 2 + last - first].decode("cp1252", errors="replace"))
        else:
            parts.append(data[file_offset:file_offset + (last - first) * 2].decode("utf-16-le", errors="replace"))
    plan = "".join(parts).replace("\r", "\n").replace("\x07", " | ")
    (OUT / "test-plan.txt").write_text(plan, encoding="utf-8")
    print(json.dumps({"planChars": len(plan), "preview": plan[:80]}, ensure_ascii=False))
