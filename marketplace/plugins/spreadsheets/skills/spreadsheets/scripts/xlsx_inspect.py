#!/usr/bin/env python3
"""Describe a workbook (.xlsx/.xlsm) or a delimited text file (.csv/.tsv/.txt).

Usage:
    python xlsx_inspect.py FILE.xlsx [--sheet NAME] [--range A1:H30] [--rows 15] [--cols 10] [--json]
    python xlsx_inspect.py FILE.csv [--rows 15]

For workbooks: every sheet's size, visibility, freeze panes, filters, merged
cells, tables, charts, images, validations and conditional formats, the
defined names, and a cell grid where formulas are shown next to their last
calculated (cached) value, plus number formats that are not General.
For CSV: detected encoding, delimiter, header and the first rows.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ENCODINGS = ("utf-8-sig", "cp1251", "latin-1")  # latin-1 never fails, so it is the last resort


def sniff_csv(path: Path, rows: int) -> dict:
    raw = path.read_bytes()
    for encoding in ENCODINGS:
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    sample = text[:65536]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","
    reader = list(csv.reader(text.splitlines(), delimiter=delimiter))
    return {"file": str(path), "encoding": encoding, "delimiter": delimiter,
            "rows": len(reader), "columns": max((len(r) for r in reader), default=0),
            "header": reader[0] if reader else [], "preview": reader[1:rows + 1]}


def cell_repr(formula_cell, value_cell) -> str:
    value = formula_cell.value
    if value is None:
        return ""
    if formula_cell.data_type == "f" or (isinstance(value, str) and value.startswith("=")):
        cached = value_cell.value if value_cell is not None else None
        text = getattr(value, "text", value)  # ArrayFormula keeps its text in .text
        return f"{text} -> {'(not calculated)' if cached is None else cached}"
    return str(value)


def sheet_report(ws, values_ws, cell_range: str | None, rows: int, cols: int) -> dict:
    info = {
        "title": ws.title, "state": ws.sheet_state, "dimensions": ws.dimensions,
        "max_row": ws.max_row, "max_column": ws.max_column,
        "freeze_panes": ws.freeze_panes, "auto_filter": ws.auto_filter.ref,
        "merged": [str(r) for r in ws.merged_cells.ranges][:20],
        "tables": dict(ws.tables.items()),  # TableList.items() yields (name, ref)
        "charts": len(getattr(ws, "_charts", [])), "images": len(getattr(ws, "_images", [])),
        "data_validations": len(ws.data_validations.dataValidation),
        "conditional_formats": len(list(ws.conditional_formatting)),
        "print_area": ws.print_area, "names": list(ws.defined_names.keys()),
    }
    if cell_range:
        min_col, min_row, max_col, max_row = _bounds(cell_range)
    else:
        min_row, min_col = ws.min_row, ws.min_column
        max_row, max_col = min(ws.max_row, min_row + rows - 1), min(ws.max_column, min_col + cols - 1)
    grid, formats, formulas = [], {}, 0
    for row in ws.iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col):
        line = []
        for cell in row:
            value_cell = values_ws[cell.coordinate] if values_ws is not None else None
            line.append(cell_repr(cell, value_cell))
            if cell.data_type == "f":
                formulas += 1
            if cell.value is not None and cell.number_format != "General":
                formats[cell.coordinate] = cell.number_format
        grid.append({"row": row[0].row, "cells": line})
    from openpyxl.utils import get_column_letter
    info["grid_origin"] = f"{get_column_letter(min_col)}{min_row}"
    info["grid_columns"] = [get_column_letter(c) for c in range(min_col, max_col + 1)]
    info["grid"] = grid
    info["number_formats"] = dict(list(formats.items())[:40])
    info["formulas_in_grid"] = formulas
    return info


def _bounds(cell_range: str):
    from openpyxl.utils.cell import range_boundaries
    return range_boundaries(cell_range)


def workbook_report(path: Path, sheet: str | None, cell_range: str | None, rows: int, cols: int) -> dict:
    import openpyxl
    keep_vba = path.suffix.lower() == ".xlsm"
    wb = openpyxl.load_workbook(path, keep_vba=keep_vba)
    try:
        values = openpyxl.load_workbook(path, data_only=True)
    except Exception:
        values = None
    names = {name: dn.attr_text for name, dn in wb.defined_names.items()}
    sheets = [wb[sheet]] if sheet else wb.worksheets
    report = {"file": str(path), "sheets": wb.sheetnames, "active": wb.active.title if wb.active else None,
              "defined_names": names, "external_links": len(getattr(wb, "_external_links", [])),
              "details": []}
    for ws in sheets:
        values_ws = values[ws.title] if values is not None else None
        report["details"].append(sheet_report(ws, values_ws, cell_range, rows, cols))
    if wb.chartsheets:
        report["chartsheets"] = [cs.title for cs in wb.chartsheets]
    return report


def print_workbook(report: dict) -> None:
    print(f"# {report['file']}")
    print(f"sheets: {', '.join(report['sheets'])} (active: {report['active']})")
    if report["defined_names"]:
        print("defined names: " + ", ".join(f"{k}={v}" for k, v in report["defined_names"].items()))
    if report["external_links"]:
        print(f"external links: {report['external_links']}")
    for sheet in report["details"]:
        print(f"\n## {sheet['title']} [{sheet['state']}] {sheet['dimensions']} "
              f"({sheet['max_row']} rows x {sheet['max_column']} cols)")
        extras = []
        for key in ("freeze_panes", "auto_filter", "print_area"):
            if sheet[key]:
                extras.append(f"{key}={sheet[key]}")
        for key in ("charts", "images", "data_validations", "conditional_formats"):
            if sheet[key]:
                extras.append(f"{key}={sheet[key]}")
        if sheet["tables"]:
            extras.append("tables=" + ", ".join(f"{k}({v})" for k, v in sheet["tables"].items()))
        if sheet["merged"]:
            extras.append("merged=" + ", ".join(sheet["merged"]))
        if extras:
            print("  " + "; ".join(extras))
        print("  " + " | ".join(["row"] + sheet["grid_columns"]))
        for line in sheet["grid"]:
            print(f"  {line['row']} | " + " | ".join(line["cells"]))
        if sheet["number_formats"]:
            by_format: dict[str, list[str]] = {}
            for coordinate, fmt in sheet["number_formats"].items():
                by_format.setdefault(fmt, []).append(coordinate)
            for fmt, cells in by_format.items():
                more = f" (+{len(cells) - 8})" if len(cells) > 8 else ""
                print(f"  format {fmt!r}: {', '.join(cells[:8])}{more}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", type=Path)
    parser.add_argument("--sheet")
    parser.add_argument("--range", dest="cell_range", help="cells to show, e.g. A1:H30")
    parser.add_argument("--rows", type=int, default=15)
    parser.add_argument("--cols", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.file.suffix.lower() in (".csv", ".tsv", ".txt"):
        report = sniff_csv(args.file, args.rows)
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(f"# {report['file']}: encoding={report['encoding']} delimiter={report['delimiter']!r} "
                  f"rows={report['rows']} columns={report['columns']}")
            print("header: " + " | ".join(report["header"]))
            for row in report["preview"]:
                print("  " + " | ".join(row))
        return 0
    if args.file.suffix.lower() == ".xls":
        print("error: .xls (Excel 97-2003) is not readable by openpyxl; convert it first: "
              "python convert.py FILE.xls --to xlsx (or pandas.read_excel with the xlrd package)", file=sys.stderr)
        return 1
    report = workbook_report(args.file, args.sheet, args.cell_range, args.rows, args.cols)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    else:
        print_workbook(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
