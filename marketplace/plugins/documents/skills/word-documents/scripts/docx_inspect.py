#!/usr/bin/env python3
"""Print the structure and text of a .docx in reading order.

Usage:
    python docx_inspect.py FILE.docx [--json] [--max-rows 20] [--no-text]

Shows paragraphs (index, style, list level, text), tables (as rows), images,
page and section breaks, headers/footers, sections (page size, orientation,
margins), core properties, comments, and tracked changes. Paragraph indexes
match `Document(...).paragraphs`, so they can be used to target edits.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docx.oxml.ns import qn  # noqa: E402
from docx.table import Table  # noqa: E402
from docx.text.paragraph import Paragraph  # noqa: E402
from docx_helpers import open_document  # noqa: E402

EMU_PER_CM = 360000


def paragraph_info(paragraph: Paragraph, index: int | None) -> dict:
    p = paragraph._p
    num_pr = p.find(qn("w:pPr") + "/" + qn("w:numPr"))
    level = None
    if num_pr is not None:
        ilvl = num_pr.find(qn("w:ilvl"))
        level = int(ilvl.get(qn("w:val"))) if ilvl is not None else 0
    info = {"type": "paragraph", "index": index, "style": paragraph.style.name if paragraph.style is not None else None,
            "text": paragraph.text}
    if level is not None:
        info["list_level"] = level
    images = len(p.findall(".//" + qn("a:blip")))
    if images:
        info["images"] = images
    if p.findall(".//" + qn("w:br")) and any(br.get(qn("w:type")) == "page" for br in p.iter(qn("w:br"))):
        info["page_break"] = True
    if p.find(qn("w:pPr") + "/" + qn("w:sectPr")) is not None:
        info["section_break"] = True
    if p.findall(".//" + qn("w:hyperlink")):
        info["hyperlinks"] = len(p.findall(".//" + qn("w:hyperlink")))
    return info


def table_info(table: Table, max_rows: int) -> dict:
    rows = []
    for row in table.rows[:max_rows]:
        cells = []
        for cell in row.cells:
            cells.append(cell.text)
        rows.append(cells)
    return {"type": "table", "style": table.style.name if table.style is not None else None,
            "rows": len(table.rows), "columns": len(table.columns), "preview": rows}


def body_blocks(document, max_rows: int):
    paragraph_index = 0
    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield paragraph_info(Paragraph(child, document), paragraph_index)
            paragraph_index += 1
        elif child.tag == qn("w:tbl"):
            yield table_info(Table(child, document), max_rows)


def section_info(document) -> list[dict]:
    out = []
    for number, section in enumerate(document.sections):
        def cm(value):
            return round(value / EMU_PER_CM, 2) if value is not None else None
        entry = {"section": number, "orientation": "landscape" if section.orientation == 1 else "portrait",
                 "page_cm": [cm(section.page_width), cm(section.page_height)],
                 "margins_cm": {"top": cm(section.top_margin), "bottom": cm(section.bottom_margin),
                                "left": cm(section.left_margin), "right": cm(section.right_margin)},
                 "different_first_page": section.different_first_page_header_footer}
        for kind in ("header", "first_page_header", "even_page_header", "footer", "first_page_footer", "even_page_footer"):
            part = getattr(section, kind)
            if not part.is_linked_to_previous:
                text = "\n".join(p.text for p in part.paragraphs if p.text)
                for table in part.tables:
                    text += "\n" + " | ".join(c.text for row in table.rows for c in row.cells)
                entry[kind] = text.strip()
        out.append(entry)
    return out


def inspect(path: Path, max_rows: int) -> dict:
    document = open_document(path)
    body = document.element.body
    props = document.core_properties
    report = {
        "file": str(path),
        "properties": {"title": props.title, "author": props.author, "subject": props.subject,
                       "modified": props.modified.isoformat() if props.modified else None},
        "sections": section_info(document),
        "blocks": list(body_blocks(document, max_rows)),
        "tracked_changes": {"insertions": len(body.findall(".//" + qn("w:ins"))),
                            "deletions": len(body.findall(".//" + qn("w:del")))},
        "text_boxes": len(body.findall(".//" + qn("w:txbxContent"))),
    }
    try:
        report["comments"] = [{"author": c.author, "text": c.text} for c in document.comments]
    except AttributeError:  # python-docx older than 1.2
        report["comments"] = None
    report["styles_used"] = sorted({b["style"] for b in report["blocks"] if b.get("style")})
    return report


def print_text(report: dict, show_text: bool) -> None:
    print(f"# {report['file']}")
    props = {k: v for k, v in report["properties"].items() if v}
    if props:
        print("properties: " + ", ".join(f"{k}={v}" for k, v in props.items()))
    for section in report["sections"]:
        line = (f"section {section['section']}: {section['orientation']} {section['page_cm'][0]}x{section['page_cm'][1]} cm, "
                f"margins {section['margins_cm']}")
        print(line)
        for kind in ("header", "first_page_header", "even_page_header", "footer", "first_page_footer", "even_page_footer"):
            if section.get(kind):
                print(f"  {kind}: {section[kind]!r}")
    print()
    for block in report["blocks"]:
        if block["type"] == "table":
            print(f"[table {block['rows']}x{block['columns']} style={block['style']}]")
            for row in block["preview"]:
                print("  | " + " | ".join(cell.replace("\n", " / ") for cell in row) + " |")
            if block["rows"] > len(block["preview"]):
                print(f"  ... {block['rows'] - len(block['preview'])} more rows")
            continue
        flags = []
        if "list_level" in block:
            flags.append(f"list L{block['list_level']}")
        for key in ("images", "hyperlinks"):
            if block.get(key):
                flags.append(f"{key}={block[key]}")
        for key in ("page_break", "section_break"):
            if block.get(key):
                flags.append(key)
        extra = f" ({', '.join(flags)})" if flags else ""
        text = block["text"] if show_text else f"{len(block['text'])} chars"
        print(f"[p{block['index']}] {block['style']}{extra}: {text}")
    changes = report["tracked_changes"]
    if changes["insertions"] or changes["deletions"]:
        print(f"\ntracked changes: {changes['insertions']} insertions, {changes['deletions']} deletions")
    if report["text_boxes"]:
        print(f"text boxes: {report['text_boxes']} (their text is not in the paragraph list above)")
    if report["comments"]:
        print(f"comments: {len(report['comments'])}")
        for comment in report["comments"]:
            print(f"  {comment['author']}: {comment['text']}")
    print(f"styles used: {', '.join(report['styles_used'])}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--max-rows", type=int, default=20, help="table rows to preview (default 20)")
    parser.add_argument("--no-text", action="store_true", help="print lengths instead of paragraph text")
    args = parser.parse_args()
    report = inspect(args.file, args.max_rows)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    else:
        print_text(report, not args.no_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
