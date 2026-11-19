#!/usr/bin/env python3
"""Describe a .pptx: slide size, layouts, and every slide's shapes, text and notes.

Usage:
    python pptx_inspect.py DECK.pptx [--layouts] [--slide N] [--json]

--layouts lists each layout with its placeholders (idx, type, name), which is
what you need to fill a template. For slides it prints each shape's kind,
placeholder idx/type, position and size in cm, and text; pictures, tables and
charts are marked. Warnings flag shapes that stick out of the slide and
placeholders left empty.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pptx import Presentation
from pptx.shapes.group import GroupShape

EMU_PER_CM = 360000


def cm(value) -> float | None:
    return None if value is None else round(value / EMU_PER_CM, 2)


def placeholder_desc(shape) -> str | None:
    if not shape.is_placeholder:
        return None
    fmt = shape.placeholder_format
    return f"{fmt.idx}:{str(fmt.type).split('.')[-1].split(' ')[0]}"


def shape_kind(shape) -> str:
    if isinstance(shape, GroupShape):
        return "group"
    if getattr(shape, "has_chart", False) and shape.has_chart:
        return f"chart({str(shape.chart.chart_type).split('.')[-1].split(' ')[0]})"
    if getattr(shape, "has_table", False) and shape.has_table:
        return f"table({len(shape.table.rows)}x{len(shape.table.columns)})"
    if shape.shape_type is not None and "PICTURE" in str(shape.shape_type):
        return "picture"
    if shape._element.tag.endswith("}pic"):
        return "picture"
    if shape.is_placeholder:
        return "placeholder"
    if shape.has_text_frame:
        return "text"
    return str(shape.shape_type).split(".")[-1].split(" ")[0].lower()


def shape_text(shape) -> str:
    if getattr(shape, "has_table", False) and shape.has_table:
        return " / ".join(" | ".join(cell.text for cell in row.cells) for row in shape.table.rows)
    if shape.has_text_frame:
        lines = []
        for paragraph in shape.text_frame.paragraphs:
            if paragraph.text:
                lines.append(("  " * paragraph.level) + paragraph.text)
        return "\n".join(lines)
    return ""


def describe_shapes(shapes, slide_w, slide_h, warnings, prefix="") -> list[dict]:
    out = []
    for shape in shapes:
        entry = {"name": prefix + shape.name, "kind": shape_kind(shape), "placeholder": placeholder_desc(shape),
                 "left_cm": cm(shape.left), "top_cm": cm(shape.top), "width_cm": cm(shape.width),
                 "height_cm": cm(shape.height), "text": shape_text(shape)}
        if None not in (shape.left, shape.top, shape.width, shape.height):
            if shape.left < 0 or shape.top < 0 or shape.left + shape.width > slide_w or shape.top + shape.height > slide_h:
                warnings.append(f"{entry['name']} extends past the slide edge")
        if shape.is_placeholder and entry["kind"] == "placeholder" and not entry["text"]:
            warnings.append(f"{entry['name']} is an empty placeholder")
        out.append(entry)
        if isinstance(shape, GroupShape):
            entry["children"] = describe_shapes(shape.shapes, slide_w, slide_h, warnings, prefix=f"{shape.name}/")
    return out


def inspect(path: Path, only_slide: int | None) -> dict:
    prs = Presentation(str(path))
    width, height = prs.slide_width, prs.slide_height
    report = {"file": str(path), "slide_size_cm": [cm(width), cm(height)],
              "aspect": round(width / height, 3), "layouts": [], "slides": []}
    for m_index, master in enumerate(prs.slide_masters):
        for l_index, layout in enumerate(master.slide_layouts):
            report["layouts"].append({"master": m_index, "index": l_index, "name": layout.name,
                                      "placeholders": [f"{placeholder_desc(ph)} {ph.name}" for ph in layout.placeholders]})
    for number, slide in enumerate(prs.slides, start=1):
        if only_slide is not None and number != only_slide:
            continue
        warnings: list[str] = []
        entry = {"number": number, "layout": slide.slide_layout.name,
                 "shapes": describe_shapes(slide.shapes, width, height, warnings),
                 "notes": slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else "",
                 "warnings": warnings}
        report["slides"].append(entry)
    return report


def print_shapes(shapes, indent="  ") -> None:
    for shape in shapes:
        ph = f" ph={shape['placeholder']}" if shape["placeholder"] else ""
        box = f"@({shape['left_cm']},{shape['top_cm']}) {shape['width_cm']}x{shape['height_cm']}cm"
        text = shape["text"].replace("\n", "\n" + indent + "    ")
        print(f"{indent}- {shape['kind']}{ph} '{shape['name']}' {box}" + (f"\n{indent}    {text}" if text else ""))
        if shape.get("children"):
            print_shapes(shape["children"], indent + "  ")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", type=Path)
    parser.add_argument("--layouts", action="store_true", help="list layouts and their placeholders")
    parser.add_argument("--slide", type=int, help="only this slide (1-based)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = inspect(args.file, args.slide)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    print(f"# {report['file']}: {len(report['slides'])} slide(s) shown, size {report['slide_size_cm'][0]}x"
          f"{report['slide_size_cm'][1]} cm (aspect {report['aspect']})")
    if args.layouts:
        print("layouts:")
        for layout in report["layouts"]:
            print(f"  [{layout['master']}.{layout['index']}] {layout['name']}: {', '.join(layout['placeholders']) or '-'}")
    for slide in report["slides"]:
        print(f"\n## slide {slide['number']} (layout: {slide['layout']})")
        print_shapes(slide["shapes"])
        if slide["notes"]:
            print("  notes: " + slide["notes"].replace("\n", " / "))
        for warning in slide["warnings"]:
            print(f"  WARNING: {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
