#!/usr/bin/env python3
"""Audit the formulas in a workbook.

Usage:
    python xlsx_check.py FILE.xlsx [--recalc] [--json] [--limit 30]

Reports, per sheet:
  - formulas whose stored result is an error (#REF!, #DIV/0!, #NAME?, ...)
  - formulas that have no stored result (the file was written by code and
    never calculated, so readers such as pandas see empty cells)
  - formulas that point at a sheet that does not exist
  - formulas that contain an error literal such as #REF! in their text
With --recalc, a temporary copy is recalculated by LibreOffice (if installed)
and the results are taken from that copy; the input file is never modified.
Exit code: 0 no problems, 1 errors / missing sheets / error literals found,
2 --recalc asked but LibreOffice is missing or failed (the check still runs on
the stored results). Formulas without a stored result are reported as a note.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

import openpyxl
from openpyxl.formula import Tokenizer
from openpyxl.formula.tokenizer import Token

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_env import find_soffice  # noqa: E402

ERRORS = ("#NULL!", "#DIV/0!", "#VALUE!", "#REF!", "#NAME?", "#NUM!", "#N/A", "#SPILL!", "#CALC!", "#GETTING_DATA")


def referenced_sheets(formula: str) -> set[str]:
    sheets = set()
    try:
        tokens = Tokenizer(formula).items
    except Exception:
        return sheets
    for token in tokens:
        if token.type == Token.OPERAND and token.subtype == Token.RANGE and "!" in token.value:
            sheet = token.value.rsplit("!", 1)[0]
            if sheet.startswith("'") and sheet.endswith("'"):
                sheet = sheet[1:-1].replace("''", "'")
            if sheet.startswith("["):  # external workbook reference
                continue
            if ":" in sheet:  # 3-D reference Sheet1:Sheet3!A1
                sheets.update(part.strip("'") for part in sheet.split(":"))
            else:
                sheets.add(sheet)
    return sheets


def recalculated_copy(path: Path, workdir: Path) -> Path:
    """Recalculate a copy of the workbook with LibreOffice and return the copy's path."""
    import subprocess
    soffice = find_soffice()
    if not soffice:
        raise FileNotFoundError("LibreOffice is not installed")
    source = workdir / f"source{path.suffix}"
    wb = openpyxl.load_workbook(path, keep_vba=path.suffix.lower() == ".xlsm")
    wb.calculation.fullCalcOnLoad = True  # ask the loader to recompute everything
    wb.save(source)
    outdir = workdir / "out"
    outdir.mkdir()
    profile = workdir / "profile"
    cmd = [soffice, f"-env:UserInstallation={profile.resolve().as_uri()}", "--headless", "--norestore",
           "--convert-to", path.suffix.lstrip(".").lower(), "--outdir", str(outdir), str(source)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    produced = list(outdir.glob("*"))
    if not produced:
        raise RuntimeError(f"LibreOffice produced no output (exit {result.returncode}) {result.stderr.strip()}")
    return produced[0]


def audit(path: Path, values_path: Path) -> dict:
    formulas_wb = openpyxl.load_workbook(path)
    values_wb = openpyxl.load_workbook(values_path, data_only=True)
    sheet_names = set(formulas_wb.sheetnames)
    report = {"file": str(path), "formulas": 0, "sheets": {}}
    for ws in formulas_wb.worksheets:
        values_ws = values_wb[ws.title] if ws.title in values_wb.sheetnames else None
        issues = {"errors": [], "not_calculated": [], "missing_sheet": [], "error_literal": []}
        count = 0
        for row in ws.iter_rows():
            for cell in row:
                if cell.data_type != "f":
                    continue
                count += 1
                text = getattr(cell.value, "text", cell.value) or ""
                cached = values_ws[cell.coordinate].value if values_ws is not None else None
                where = f"{cell.coordinate}: {text}"
                if isinstance(cached, str) and cached.startswith(ERRORS):
                    issues["errors"].append(f"{where} -> {cached}")
                elif cached is None:
                    issues["not_calculated"].append(where)
                missing = sorted(s for s in referenced_sheets(text) if s not in sheet_names)
                if missing:
                    issues["missing_sheet"].append(f"{where} (no sheet {', '.join(missing)})")
                if any(err in text.upper() for err in ERRORS):
                    issues["error_literal"].append(where)
        report["formulas"] += count
        report["sheets"][ws.title] = {"formulas": count, **issues}
    return report


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", type=Path)
    parser.add_argument("--recalc", action="store_true", help="recalculate a copy with LibreOffice first")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--limit", type=int, default=30, help="cells listed per issue type (default 30)")
    args = parser.parse_args()

    exit_code = 0
    workdir = Path(tempfile.mkdtemp(prefix="xlsx-check-"))
    try:
        values_path, recalculated = args.file, False
        if args.recalc:
            try:
                values_path, recalculated = recalculated_copy(args.file, workdir), True
            except FileNotFoundError:
                print("note: LibreOffice not found; checking the results stored in the file instead", file=sys.stderr)
                exit_code = 2
            except Exception as exc:
                print(f"note: recalculation failed ({exc}); checking the stored results", file=sys.stderr)
                exit_code = 2
        report = audit(args.file, values_path)
        report["recalculated"] = recalculated
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    problems = sum(len(s[k]) for s in report["sheets"].values() for k in ("errors", "missing_sheet", "error_literal"))
    uncalculated = sum(len(s["not_calculated"]) for s in report["sheets"].values())
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        source = "recalculated by LibreOffice" if recalculated else "results stored in the file"
        print(f"# {report['file']}: {report['formulas']} formulas, checked against {source}")
        labels = {"errors": "error results", "not_calculated": "no stored result (never calculated)",
                  "missing_sheet": "reference a missing sheet", "error_literal": "contain an error literal"}
        for title, sheet in report["sheets"].items():
            print(f"## {title}: {sheet['formulas']} formulas")
            for key, label in labels.items():
                if sheet[key]:
                    print(f"  {len(sheet[key])} {label}:")
                    shown = min(args.limit, 5) if key == "not_calculated" else args.limit
                    for line in sheet[key][:shown]:
                        print(f"    {line}")
                    if len(sheet[key]) > shown:
                        print(f"    ... {len(sheet[key]) - shown} more")
        print("OK: no formula problems found" if problems == 0 else f"{problems} problem(s) found")
        if recalculated and uncalculated:
            print(f"warning: {uncalculated} formula(s) still have no result after recalculation; "
                  "LibreOffice may not support them (or did not recalculate). Check them by hand.")
        elif uncalculated:
            print(f"note: {uncalculated} formula(s) have no stored result; Excel computes them on open. "
                  "Run with --recalc (needs LibreOffice) to check their values.")
    return 1 if problems else exit_code


if __name__ == "__main__":
    sys.exit(main())
