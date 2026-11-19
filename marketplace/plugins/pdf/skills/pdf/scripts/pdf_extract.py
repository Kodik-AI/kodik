#!/usr/bin/env python3
"""Extract text, tables or images from a PDF.

Usage:
    python pdf_extract.py text IN.pdf [--pages 1-3] [--layout] [--out text.txt]
    python pdf_extract.py tables IN.pdf OUTDIR [--pages 2] [--text-strategy]
    python pdf_extract.py images IN.pdf OUTDIR [--pages 1-]

text: pdfplumber when installed (--layout keeps columns and spacing), else
pypdf. Pages are separated by a "=== page N ===" line.
tables: pdfplumber finds tables from ruling lines (default) or from text
alignment (--text-strategy, for tables without borders); each table becomes
OUTDIR/<name>-p<page>-t<n>.csv (UTF-8 with BOM, so Excel opens it correctly).
images: the embedded images as files, via pypdf.
An empty text result usually means a scanned PDF: run OCR first (see SKILL.md).
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

from pypdf import PdfReader


def page_indexes(spec: str | None, count: int) -> list[int]:
    if not spec:
        return list(range(count))
    out: list[int] = []
    for part in (p.strip() for p in spec.split(",")):
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            out.extend(range(int(start_s or 1) - 1, min(int(end_s or count), count)))
        elif part:
            out.append(int(part) - 1)
    return [i for i in out if 0 <= i < count]


def password() -> str | None:
    return os.environ.get("PDF_PASSWORD")


def extract_text(path: Path, pages: str | None, layout: bool) -> str:
    chunks = []
    try:
        import pdfplumber
    except ImportError:
        pdfplumber = None
    if pdfplumber is not None:
        with pdfplumber.open(str(path), password=password()) as pdf:
            for index in page_indexes(pages, len(pdf.pages)):
                text = pdf.pages[index].extract_text(layout=layout) or ""
                chunks.append(f"=== page {index + 1} ===\n{text}")
    else:
        reader = PdfReader(str(path), password=password())
        for index in page_indexes(pages, len(reader.pages)):
            mode = "layout" if layout else "plain"
            text = reader.pages[index].extract_text(extraction_mode=mode) or ""
            chunks.append(f"=== page {index + 1} ===\n{text}")
    return "\n".join(chunks)


def extract_tables(path: Path, outdir: Path, pages: str | None, text_strategy: bool) -> list[Path]:
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError("table extraction needs pdfplumber (pip install pdfplumber)") from exc
    settings = {"vertical_strategy": "text", "horizontal_strategy": "text"} if text_strategy else {}
    outdir.mkdir(parents=True, exist_ok=True)
    written = []
    with pdfplumber.open(str(path), password=password()) as pdf:
        for index in page_indexes(pages, len(pdf.pages)):
            for number, table in enumerate(pdf.pages[index].extract_tables(settings), start=1):
                rows = [["" if cell is None else str(cell).replace("\n", " ") for cell in row] for row in table]
                if not any(any(cell.strip() for cell in row) for row in rows):
                    continue
                target = outdir / f"{path.stem}-p{index + 1}-t{number}.csv"
                with open(target, "w", newline="", encoding="utf-8-sig") as handle:
                    csv.writer(handle).writerows(rows)
                written.append(target)
                print(f"page {index + 1} table {number}: {len(rows)} rows x {max(map(len, rows))} cols -> {target}")
    return written


def extract_images(path: Path, outdir: Path, pages: str | None) -> list[Path]:
    reader = PdfReader(str(path), password=password())
    outdir.mkdir(parents=True, exist_ok=True)
    written = []
    for index in page_indexes(pages, len(reader.pages)):
        for number, image in enumerate(reader.pages[index].images, start=1):
            suffix = Path(image.name).suffix or ".png"
            target = outdir / f"{path.stem}-p{index + 1}-i{number}{suffix}"
            target.write_bytes(image.data)
            written.append(target)
            print(f"page {index + 1} image {number} -> {target}")
    return written


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("text"); p.add_argument("input", type=Path); p.add_argument("--pages")
    p.add_argument("--layout", action="store_true"); p.add_argument("--out", type=Path)
    p = sub.add_parser("tables"); p.add_argument("input", type=Path); p.add_argument("outdir", type=Path)
    p.add_argument("--pages"); p.add_argument("--text-strategy", action="store_true")
    p = sub.add_parser("images"); p.add_argument("input", type=Path); p.add_argument("outdir", type=Path)
    p.add_argument("--pages")
    args = parser.parse_args()
    try:
        if args.command == "text":
            text = extract_text(args.input, args.pages, args.layout)
            if args.out:
                args.out.write_text(text, encoding="utf-8")
                print(f"wrote {args.out} ({len(text)} chars)")
            else:
                print(text)
            body = "".join(line for line in text.splitlines() if not line.startswith("=== page "))
            if not body.strip():
                print("note: no text layer found; the PDF is probably scanned and needs OCR", file=sys.stderr)
        elif args.command == "tables":
            if not extract_tables(args.input, args.outdir, args.pages, args.text_strategy):
                print("no tables found; try --text-strategy for tables without ruling lines", file=sys.stderr)
        else:
            if not extract_images(args.input, args.outdir, args.pages):
                print("no embedded images found", file=sys.stderr)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
