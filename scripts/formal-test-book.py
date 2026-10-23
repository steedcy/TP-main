"""Maintain the supplied legacy XLS test case template during formal execution.

The original Desktop workbook is read-only. Each batch writes to a temporary
copy, validates every case and unaffected source cell, then replaces the
working result workbook. Use one writer at a time.
"""

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "Documents/Codex/TIP-prep-deps"))
import xlrd
from xlutils.copy import copy as copy_workbook

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path.home() / "Desktop/测试用例V2.xls"
OUTPUT = ROOT / "document/正式测试用例V2-执行结果.xls"
CASE_SHEET = "项目测试用例"
CASE_COUNT = 95
CASE_STRIDE = 14
RESULT_COLS = {"conclusion": 2, "step_result": 4, "step_note": 5}


def open_book(path):
    return xlrd.open_workbook(str(path), formatting_info=True)


def check_source(book):
    sheet = book.sheet_by_name(CASE_SHEET)
    if sheet.nrows != CASE_COUNT * CASE_STRIDE:
        raise ValueError(f"unexpected case sheet rows: {sheet.nrows}")
    for index in range(CASE_COUNT):
        actual = str(sheet.cell_value(index * CASE_STRIDE + 3, 5))
        expected = f"TC-{index + 1:03d}"
        if actual != expected:
            raise ValueError(f"case order mismatch: {expected} != {actual}")
    return sheet


def verify_preservation(source, current):
    if source.sheet_names() != current.sheet_names():
        raise ValueError("worksheet list changed")
    allowed = {(0, 1)}  # document property "用例总数" C? set below dynamically
    src_attr = source.sheet_by_name("文档属性")
    count_row = next(i for i in range(src_attr.nrows) if src_attr.cell_value(i, 0) == "用例总数：")
    allowed = {("文档属性", count_row, 1)}
    for si in range(CASE_COUNT):
        base = si * CASE_STRIDE
        allowed.update({(CASE_SHEET, base + r, c) for r in (5, 6, 7) for c in (2,)})
        allowed.update({(CASE_SHEET, base + r, c) for r in range(9, 14) for c in (4, 5)})
    for name in source.sheet_names():
        a, b = source.sheet_by_name(name), current.sheet_by_name(name)
        if (a.nrows, a.ncols) != (b.nrows, b.ncols):
            raise ValueError(f"worksheet dimensions changed: {name}")
        for row in range(a.nrows):
            for col in range(a.ncols):
                if (name, row, col) in allowed:
                    continue
                if a.cell_value(row, col) != b.cell_value(row, col):
                    raise ValueError(f"source cell changed: {name}!R{row+1}C{col+1}")


def apply_results(read, write, results, allow_amend=False):
    sheet = read.sheet_by_name(CASE_SHEET)
    writable = write.get_sheet(read.sheet_names().index(CASE_SHEET))
    seen = set()
    for item in results:
        code = item["id"]
        if code in seen:
            raise ValueError(f"duplicate case {code}")
        seen.add(code)
        index = int(code.removeprefix("TC-")) - 1
        if index < 0 or index >= CASE_COUNT or sheet.cell_value(index * CASE_STRIDE + 3, 5) != code:
            raise ValueError(f"unknown case {code}")
        base = index * CASE_STRIDE
        previous = str(sheet.cell_value(base + 7, 2)).strip()
        if previous and not allow_amend:
            raise ValueError(f"existing result must not be overwritten: {code}")
        if allow_amend and not previous:
            raise ValueError(f"amend requires an existing result: {code}")
        conclusion = item["conclusion"]
        if conclusion not in ("P", "F", "NT"):
            raise ValueError(f"invalid conclusion for {code}: {conclusion}")
        steps = item["steps"]
        active_rows = [r for r in range(base + 9, base + 14) if str(sheet.cell_value(r, 1)).strip() != "—"]
        if len(steps) != len(active_rows):
            raise ValueError(f"expected {len(active_rows)} steps for {code}; got {len(steps)}")
        if conclusion == "P" and any(s["result"] != "P" for s in steps):
            raise ValueError(f"PASS requires all steps PASS: {code}")
        if conclusion == "F" and not any(s["result"] == "F" for s in steps):
            raise ValueError(f"FAIL requires failed step: {code}")
        if conclusion == "NT" and (any(s["result"] == "F" for s in steps) or not any(s["result"] == "NT" for s in steps)):
            raise ValueError(f"NT requires an untested step and no observed failure: {code}")
        when = dt.date.fromisoformat(item["date"])
        writable.write(base + 5, 2, item.get("tester", "Codex（自动执行）"))
        writable.write(base + 6, 2, xlrd.xldate.xldate_from_date_tuple((when.year, when.month, when.day), read.datemode))
        writable.write(base + 7, 2, conclusion)
        for row, step in zip(active_rows, steps):
            if step["result"] not in ("P", "F", "NT"):
                raise ValueError(f"invalid step result for {code}")
            note = str(step.get("note", "")).strip()
            if step["result"] != "P" and not note:
                raise ValueError(f"non-pass step requires note: {code}")
            if len(note) > 1500:
                raise ValueError(f"step note too long: {code}")
            writable.write(row, RESULT_COLS["step_result"], step["result"])
            writable.write(row, RESULT_COLS["step_note"], note)
    return seen


def verify_results(book, requested=None):
    source = open_book(SOURCE)
    verify_preservation(source, book)
    sheet = check_source(book)
    counts = {"P": 0, "F": 0, "NT": 0, "blank": 0}
    for index in range(CASE_COUNT):
        code = f"TC-{index + 1:03d}"
        value = str(sheet.cell_value(index * CASE_STRIDE + 7, 2)).strip()
        if value not in ("P", "F", "NT", ""):
            raise ValueError(f"unexpected conclusion {code}: {value}")
        counts[value or "blank"] += 1
        if requested is not None and code in requested and not value:
            raise ValueError(f"requested case still blank: {code}")
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("init", "update", "amend", "check"))
    parser.add_argument("--input", help="JSON file with batch and results array")
    args = parser.parse_args()
    source = open_book(SOURCE)
    check_source(source)
    if args.action == "init":
        if OUTPUT.exists():
            raise SystemExit(f"working book already exists: {OUTPUT}")
        write = copy_workbook(source)
        attr = source.sheet_by_name("文档属性")
        row = next(i for i in range(attr.nrows) if attr.cell_value(i, 0) == "用例总数：")
        write.get_sheet(source.sheet_names().index("文档属性")).write(row, 1, CASE_COUNT)
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        write.save(str(OUTPUT))
        print(json.dumps({"output": str(OUTPUT), "counts": verify_results(open_book(OUTPUT))}, ensure_ascii=False))
        return
    if not OUTPUT.exists():
        raise SystemExit("run init first")
    if args.action == "check":
        print(json.dumps({"output": str(OUTPUT), "counts": verify_results(open_book(OUTPUT))}, ensure_ascii=False))
        return
    if not args.input:
        raise SystemExit("--input is required for update/amend")
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    results = payload["results"]
    current = open_book(OUTPUT)
    verify_results(current)
    write = copy_workbook(current)
    requested = apply_results(current, write, results, allow_amend=args.action == "amend")
    temp = OUTPUT.with_suffix(".tmp.xls")
    try:
        write.save(str(temp))
        counts = verify_results(open_book(temp), requested)
        os.replace(temp, OUTPUT)
    finally:
        if temp.exists():
            temp.unlink()
    print(json.dumps({"batch": payload.get("batch"), "updated": sorted(requested), "counts": counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
