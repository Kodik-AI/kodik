#!/usr/bin/env python3
"""Find and replace text in a .docx without losing formatting.

Usage:
    python docx_replace.py IN.docx OUT.docx -r OLD NEW [-r OLD2 NEW2 ...]
    python docx_replace.py IN.docx OUT.docx --pairs replacements.json   # {"OLD": "NEW", ...}
    python docx_replace.py IN.docx --dry-run -r OLD NEW                  # count only

Word splits text into runs at arbitrary points (spell check, edits, styles), so
"Acme Corp" may be stored as "Ac" + "me Corp". This script matches across runs
inside each paragraph and writes the replacement into the run where the match
starts, so that run's font, size, color and so on carry over; the rest of the
paragraph is untouched. It covers the body, tables, text boxes, headers,
footers, footnotes, endnotes and comments. Matches never span paragraphs, and
a replacement cannot add line or paragraph breaks.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from lxml import etree

TEXT_PART_SUFFIXES = (
    "document.main+xml", "header+xml", "footer+xml", "footnotes+xml", "endnotes+xml", "comments+xml",
    "template.main+xml",
)
W_P, W_T = qn("w:p"), qn("w:t")
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def paragraph_text_nodes(p) -> list:
    """w:t elements that belong to this paragraph (not to a nested text-box paragraph)."""
    nodes = []
    for t in p.iter(W_T):
        owner = t.getparent()
        while owner is not None and owner.tag != W_P:
            owner = owner.getparent()
        if owner is p:
            nodes.append(t)
    return nodes


def replace_in_paragraph(p, old: str, new: str) -> int:
    nodes = paragraph_text_nodes(p)
    if not nodes:
        return 0
    texts = [t.text or "" for t in nodes]
    full = "".join(texts)
    if old not in full:
        return 0
    starts, position = [], 0
    for text in texts:
        starts.append(position)
        position += len(text)

    def locate(offset: int, is_end: bool) -> tuple[int, int]:
        """Node holding character `offset` (a start), or ending at/after it (an exclusive end)."""
        for i, text in enumerate(texts):
            low, high = starts[i], starts[i] + len(text)
            if (low <= offset < high) if not is_end else (low < offset <= high):
                return i, offset - low
        raise ValueError(offset)

    matches, search_from = [], 0
    while True:
        found = full.find(old, search_from)
        if found < 0:
            break
        matches.append(found)
        search_from = found + len(old)
    # Back to front: an edit only changes text at or after its own match, so the
    # offsets of the earlier matches stay valid.
    for start in reversed(matches):
        first, first_off = locate(start, is_end=False)
        last, last_off = locate(start + len(old), is_end=True)
        if first == last:
            texts[first] = texts[first][:first_off] + new + texts[first][last_off:]
        else:
            texts[first] = texts[first][:first_off] + new
            for middle in range(first + 1, last):
                texts[middle] = ""
            texts[last] = texts[last][last_off:]
    for node, text in zip(nodes, texts):
        if node.text != text:
            node.text = text
            if text != text.strip():
                node.set(XML_SPACE, "preserve")
    return len(matches)


def replace_in_tree(root, pairs: list[tuple[str, str]]) -> dict:
    counts = {old: 0 for old, _ in pairs}
    for p in root.iter(W_P):
        for old, new in pairs:
            counts[old] += replace_in_paragraph(p, old, new)
    return counts


def run(src: Path, dst: Path | None, pairs: list[tuple[str, str]]) -> dict:
    document = Document(str(src))
    totals = {old: 0 for old, _ in pairs}
    for part in document.part.package.iter_parts():
        if not part.content_type.endswith(TEXT_PART_SUFFIXES):
            continue
        element = getattr(part, "_element", None)
        if element is not None:
            counts = replace_in_tree(element, pairs)
        else:  # parts python-docx keeps as raw bytes (footnotes, endnotes)
            root = etree.fromstring(part.blob)
            counts = replace_in_tree(root, pairs)
            if any(counts.values()):
                part._blob = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
        for old, count in counts.items():
            totals[old] += count
    if dst is not None:
        document.save(str(dst))
    return totals


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("-r", "--replace", nargs=2, action="append", metavar=("OLD", "NEW"), default=[])
    parser.add_argument("--pairs", type=Path, help="JSON object {old: new}")
    parser.add_argument("--dry-run", action="store_true", help="count matches, write nothing")
    args = parser.parse_args()

    pairs = [tuple(pair) for pair in args.replace]
    if args.pairs:
        pairs += list(json.loads(args.pairs.read_text(encoding="utf-8")).items())
    pairs = [(old, new) for old, new in pairs if old]
    if not pairs:
        parser.error("give at least one -r OLD NEW or --pairs")
    if not args.dry_run and args.output is None:
        parser.error("OUTPUT is required unless --dry-run")
    if args.output is not None and args.output.resolve() == args.input.resolve():
        parser.error("write to a new file, then replace the original once it is verified")
    totals = run(args.input, None if args.dry_run else args.output, pairs)
    for old, count in totals.items():
        print(f"{count:5d}  {old!r}")
    missing = [old for old, count in totals.items() if count == 0]
    if missing:
        print(f"not found: {', '.join(repr(m) for m in missing)}", file=sys.stderr)
    if not args.dry_run:
        print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
