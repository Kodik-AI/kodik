#!/usr/bin/env python3
"""Page operations on PDFs with pypdf.

Usage:
    python pdf_pages.py merge OUT.pdf A.pdf B.pdf:1-3 C.pdf     # FILE:PAGES takes only those pages
    python pdf_pages.py split IN.pdf OUTDIR [--every 1 | --ranges "1-3,4-10"]
    python pdf_pages.py select IN.pdf OUT.pdf --pages "3,1-2,10-"  # extract / reorder (order kept)
    python pdf_pages.py delete IN.pdf OUT.pdf --pages "2,5-6"
    python pdf_pages.py rotate IN.pdf OUT.pdf --angle 90 [--pages "1,3"]
    python pdf_pages.py stamp IN.pdf OUT.pdf --overlay mark.pdf [--under] [--pages ...]
    python pdf_pages.py encrypt IN.pdf OUT.pdf        # password from PDF_PASSWORD env var
    python pdf_pages.py decrypt IN.pdf OUT.pdf        # password from PDF_PASSWORD env var

Pages are 1-based; "8-" means 8 to the end. Bookmarks are kept by merge
and select where pypdf can map them. Encrypted inputs are opened with the
PDF_PASSWORD environment variable when it is set.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter


def page_list(spec: str | None, count: int) -> list[int]:
    """'3,1-2,10-' -> zero-based indexes in the given order."""
    if not spec:
        return list(range(count))
    out: list[int] = []
    for part in (p.strip() for p in spec.split(",")):
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start, end = int(start_s or 1), int(end_s or count)
        else:
            start = end = int(part)
        if not (1 <= start <= count and 1 <= end <= count):
            raise ValueError(f"page {part} is outside 1-{count}")
        step = 1 if end >= start else -1
        out.extend(n - 1 for n in range(start, end + step, step))
    return out


def open_pdf(path: Path) -> PdfReader:
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        password = os.environ.get("PDF_PASSWORD", "")
        if not reader.decrypt(password):
            raise PermissionError(f"{path} is encrypted; set PDF_PASSWORD to the password the user gave you")
    return reader


def save(writer: PdfWriter, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as handle:
        writer.write(handle)
    print(f"wrote {out} ({len(writer.pages)} pages)")


def cmd_merge(args) -> None:
    writer = PdfWriter()
    for item in args.inputs:
        # rpartition keeps Windows drive letters (C:\a.pdf:1-3) intact
        path, _, spec = (item, "", "") if Path(item).exists() else item.rpartition(":")
        reader = open_pdf(Path(path))
        writer.append(reader, pages=page_list(spec or None, len(reader.pages)))
    save(writer, args.output)


def cmd_split(args) -> None:
    reader = open_pdf(args.input)
    count = len(reader.pages)
    if args.ranges:
        groups = [page_list(part, count) for part in args.ranges.split(",")]
    else:
        groups = [list(range(i, min(i + args.every, count))) for i in range(0, count, args.every)]
    for group in groups:
        writer = PdfWriter()
        for index in group:
            writer.add_page(reader.pages[index])
        name = f"{args.input.stem}-p{group[0] + 1}" + (f"-{group[-1] + 1}" if len(group) > 1 else "") + ".pdf"
        save(writer, args.outdir / name)


def cmd_select(args) -> None:
    reader = open_pdf(args.input)
    writer = PdfWriter()
    writer.append(reader, pages=page_list(args.pages, len(reader.pages)))
    save(writer, args.output)


def cmd_delete(args) -> None:
    reader = open_pdf(args.input)
    drop = set(page_list(args.pages, len(reader.pages)))
    writer = PdfWriter()
    writer.append(reader, pages=[i for i in range(len(reader.pages)) if i not in drop])
    save(writer, args.output)


def cmd_rotate(args) -> None:
    if args.angle % 90:
        raise ValueError("angle must be a multiple of 90")
    writer = PdfWriter(clone_from=open_pdf(args.input))
    for index in page_list(args.pages, len(writer.pages)):
        writer.pages[index].rotate(args.angle)
    save(writer, args.output)


def cmd_stamp(args) -> None:
    overlay = open_pdf(args.overlay).pages[0]
    writer = PdfWriter(clone_from=open_pdf(args.input))
    for index in page_list(args.pages, len(writer.pages)):
        writer.pages[index].merge_page(overlay, over=not args.under)
    save(writer, args.output)


def cmd_encrypt(args) -> None:
    password = os.environ.get("PDF_PASSWORD")
    if not password:
        raise ValueError("set PDF_PASSWORD to the password the user chose")
    writer = PdfWriter(clone_from=open_pdf(args.input))
    writer.encrypt(password, algorithm="AES-256")
    save(writer, args.output)


def cmd_decrypt(args) -> None:
    writer = PdfWriter(clone_from=open_pdf(args.input))
    save(writer, args.output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("merge"); p.add_argument("output", type=Path); p.add_argument("inputs", nargs="+")
    p.set_defaults(func=cmd_merge)
    p = sub.add_parser("split"); p.add_argument("input", type=Path); p.add_argument("outdir", type=Path)
    p.add_argument("--every", type=int, default=1); p.add_argument("--ranges"); p.set_defaults(func=cmd_split)
    for name, func in (("select", cmd_select), ("delete", cmd_delete)):
        p = sub.add_parser(name); p.add_argument("input", type=Path); p.add_argument("output", type=Path)
        p.add_argument("--pages", required=True); p.set_defaults(func=func)
    p = sub.add_parser("rotate"); p.add_argument("input", type=Path); p.add_argument("output", type=Path)
    p.add_argument("--angle", type=int, default=90); p.add_argument("--pages"); p.set_defaults(func=cmd_rotate)
    p = sub.add_parser("stamp"); p.add_argument("input", type=Path); p.add_argument("output", type=Path)
    p.add_argument("--overlay", type=Path, required=True); p.add_argument("--under", action="store_true")
    p.add_argument("--pages"); p.set_defaults(func=cmd_stamp)
    for name, func in (("encrypt", cmd_encrypt), ("decrypt", cmd_decrypt)):
        p = sub.add_parser(name); p.add_argument("input", type=Path); p.add_argument("output", type=Path)
        p.set_defaults(func=func)
    args = parser.parse_args()
    inputs = [getattr(args, "input", None), getattr(args, "output", None)]
    if inputs[0] is not None and inputs[1] is not None and Path(inputs[0]).resolve() == Path(inputs[1]).resolve():
        parser.error("write to a new file, not over the input")
    try:
        args.func(args)
    except (ValueError, PermissionError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
