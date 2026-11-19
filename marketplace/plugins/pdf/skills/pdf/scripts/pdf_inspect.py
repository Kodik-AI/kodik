#!/usr/bin/env python3
"""Summarize a PDF: pages, sizes, rotation, metadata, encryption, form fields,
outline, attachments, and how much extractable text each page has.

Usage:
    python pdf_inspect.py FILE.pdf [--password PW] [--json]

A page with images but (almost) no extractable text is probably a scan; the
report flags those so you know OCR is needed before text extraction.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from pypdf import PdfReader

POINTS_PER_CM = 72 / 2.54
PAPER = {(595, 842): "A4", (612, 792): "Letter", (612, 1008): "Legal", (420, 595): "A5", (842, 1191): "A3"}


def paper_name(width: float, height: float) -> str:
    key = (round(min(width, height)), round(max(width, height)))
    for (w, h), name in PAPER.items():
        if abs(key[0] - w) <= 2 and abs(key[1] - h) <= 2:
            return name
    return "custom"


def outline_titles(reader: PdfReader, items=None, depth=0, out=None) -> list[str]:
    out = [] if out is None else out
    for item in reader.outline if items is None else items:
        if isinstance(item, list):
            outline_titles(reader, item, depth + 1, out)
        else:
            out.append("  " * depth + str(item.title))
    return out


def inspect(path: Path, password: str | None) -> dict:
    reader = PdfReader(str(path))
    report = {"file": str(path), "encrypted": reader.is_encrypted}
    if reader.is_encrypted:
        if password is None:
            try:
                unlocked = reader.decrypt("")  # many PDFs only restrict permissions
            except Exception as exc:
                report["error"] = f"cannot decrypt: {exc} (AES needs the 'cryptography' package)"
                return report
            if not unlocked:
                report["error"] = "password required; ask the user for it and set PDF_PASSWORD"
                return report
        elif not reader.decrypt(password):
            report["error"] = "wrong password"
            return report
    meta = reader.metadata or {}
    report["metadata"] = {k.lstrip("/"): str(v) for k, v in meta.items()}
    report["pages"] = len(reader.pages)
    pages, scanned = [], []
    for number, page in enumerate(reader.pages, start=1):
        box = page.mediabox
        width, height = float(box.width), float(box.height)
        try:
            chars = len((page.extract_text() or "").strip())
        except Exception:
            chars = -1
        try:
            images = len(page.images)
        except Exception:
            images = -1
        entry = {"page": number, "size_cm": [round(width / POINTS_PER_CM, 1), round(height / POINTS_PER_CM, 1)],
                 "paper": paper_name(width, height), "rotation": page.rotation,
                 "text_chars": chars, "images": images}
        if chars < 20 and images > 0:
            scanned.append(number)
        pages.append(entry)
    report["page_details"] = pages
    report["looks_scanned"] = scanned
    fields = reader.get_fields() or {}
    report["form_fields"] = len(fields)
    try:
        report["outline"] = outline_titles(reader)[:50]
    except Exception:
        report["outline"] = []
    try:
        report["attachments"] = list(reader.attachments.keys())
    except Exception:
        report["attachments"] = []
    return report


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", type=Path)
    parser.add_argument("--password", default=os.environ.get("PDF_PASSWORD"),
                        help="defaults to the PDF_PASSWORD environment variable")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = inspect(args.file, args.password)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1 if "error" in report else 0
    print(f"# {report['file']}" + (" (encrypted)" if report["encrypted"] else ""))
    if "error" in report:
        print(f"error: {report['error']}")
        return 1
    meta = {k: v for k, v in report["metadata"].items() if v}
    if meta:
        print("metadata: " + ", ".join(f"{k}={v}" for k, v in meta.items()))
    print(f"pages: {report['pages']}, form fields: {report['form_fields']}, attachments: {len(report['attachments'])}")
    for page in report["page_details"]:
        rotation = f" rotated {page['rotation']}" if page["rotation"] else ""
        print(f"  p{page['page']}: {page['paper']} {page['size_cm'][0]}x{page['size_cm'][1]} cm{rotation}, "
              f"{page['text_chars']} text chars, {page['images']} images")
    if report["outline"]:
        print("outline:\n  " + "\n  ".join(report["outline"]))
    if report["looks_scanned"]:
        pages = ", ".join(map(str, report["looks_scanned"]))
        print(f"pages {pages} have images but no text layer: probably scanned, OCR needed for their text")
    return 0


if __name__ == "__main__":
    sys.exit(main())
