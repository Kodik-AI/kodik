#!/usr/bin/env python3
"""Build a .pptx from a JSON outline, using a template's layouts and placeholders.

Usage:
    python pptx_from_outline.py outline.json OUT.pptx [--template brand.pptx] [--keep-template-slides]

Outline format (paths are relative to the outline file):
{
  "widescreen": true,                       # 16:9 when no template is given (default true)
  "slides": [
    {"layout": "Title Slide", "title": "Q3 Review", "subtitle": "Board meeting", "notes": "Open with the headline"},
    {"layout": "Title and Content", "title": "Highlights",
     "bullets": ["Revenue up 18%", ["New regions", 1], "Churn down"]},   # [text, level] for sub-bullets
    {"layout": "Title Only", "title": "Trend", "image": "chart.png"},
    {"layout": "Title Only", "title": "By region", "table": [["Region", "Revenue"], ["North", "1.2M"]]},
    {"layout": "Title Only", "title": "Mix", "chart": {"type": "column", "categories": ["Q1", "Q2"],
                                                       "series": {"2025": [1, 2], "2026": [2, 3]}}}
  ]
}
"layout" is a layout name or a 0-based index. Text goes into the layout's
title / subtitle / body placeholders; images, tables and charts fill the body
area (or a picture placeholder). Unused placeholders are removed. Chart types:
column, bar, line, pie, area, doughnut.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pptx import Presentation  # noqa: E402
from pptx.chart.data import CategoryChartData  # noqa: E402
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION  # noqa: E402
from pptx.enum.shapes import PP_PLACEHOLDER  # noqa: E402
from pptx.util import Emu  # noqa: E402
from pptx_helpers import (BODY_TYPES, TITLE_TYPES, add_picture_fit, delete_slide, layout_by_name,  # noqa: E402
                          placeholder_of, remove_empty_placeholders, remove_shape, set_widescreen)

CHART_TYPES = {"column": XL_CHART_TYPE.COLUMN_CLUSTERED, "bar": XL_CHART_TYPE.BAR_CLUSTERED,
               "line": XL_CHART_TYPE.LINE_MARKERS, "pie": XL_CHART_TYPE.PIE, "area": XL_CHART_TYPE.AREA,
               "doughnut": XL_CHART_TYPE.DOUGHNUT}


def resolve_layout(prs, spec):
    if isinstance(spec, int):
        return prs.slide_layouts[spec]
    return layout_by_name(prs, spec)


def content_box(prs, slide):
    """Area for a picture/table/chart: the body placeholder's box, else below the title."""
    body = placeholder_of(slide, BODY_TYPES)
    if body is not None:
        box = (body.left, body.top, body.width, body.height)
        remove_shape(body)
        return box
    margin = int(prs.slide_width * 0.05)
    title = placeholder_of(slide, TITLE_TYPES)
    top = (title.top + title.height + margin // 2) if title is not None else margin
    return margin, top, prs.slide_width - 2 * margin, prs.slide_height - top - margin


def fill_bullets(placeholder, bullets) -> None:
    frame = placeholder.text_frame
    frame.clear()  # keeps one empty paragraph
    for index, item in enumerate(bullets):
        text, level = (item[0], int(item[1])) if isinstance(item, (list, tuple)) else (str(item), 0)
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = text
        paragraph.level = level


def add_table(slide, rows, box) -> None:
    left, top, width, height = box
    n_rows, n_cols = len(rows), max(len(r) for r in rows)
    row_height = min(int(height / n_rows), Emu(457200))  # at most 1.27 cm per row
    shape = slide.shapes.add_table(n_rows, n_cols, left, top, width, row_height * n_rows)
    for r, values in enumerate(rows):
        for c in range(n_cols):
            shape.table.cell(r, c).text = str(values[c]) if c < len(values) else ""


def add_chart(slide, spec, box) -> None:
    data = CategoryChartData()
    data.categories = spec["categories"]
    for name, values in spec["series"].items():
        data.add_series(name, values)
    chart_type = CHART_TYPES[spec.get("type", "column")]
    chart = slide.shapes.add_chart(chart_type, *box, data).chart
    chart.has_legend = len(spec["series"]) > 1 or chart_type in (XL_CHART_TYPE.PIE, XL_CHART_TYPE.DOUGHNUT)
    if chart.has_legend:
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False
    if spec.get("title"):
        chart.has_title = True
        chart.chart_title.text_frame.text = spec["title"]


def build(outline: dict, base: Path, template: Path | None, keep_template_slides: bool):
    prs = Presentation(str(template)) if template else Presentation()
    if template and not keep_template_slides:
        for index in range(len(prs.slides) - 1, -1, -1):
            delete_slide(prs, index)
    if not template and outline.get("widescreen", True):
        set_widescreen(prs)
    for number, spec in enumerate(outline["slides"], start=1):
        slide = prs.slides.add_slide(resolve_layout(prs, spec.get("layout", 1)))
        title = placeholder_of(slide, TITLE_TYPES)
        if spec.get("title"):
            if title is None:
                raise ValueError(f"slide {number}: layout {slide.slide_layout.name!r} has no title placeholder")
            title.text = spec["title"]
        if spec.get("subtitle"):
            target = placeholder_of(slide, (PP_PLACEHOLDER.SUBTITLE,)) or placeholder_of(slide, BODY_TYPES)
            if target is None:
                raise ValueError(f"slide {number}: no subtitle or body placeholder for the subtitle")
            target.text = spec["subtitle"]
        if spec.get("bullets"):
            body = placeholder_of(slide, BODY_TYPES)
            if body is None:
                raise ValueError(f"slide {number}: layout {slide.slide_layout.name!r} has no body placeholder")
            fill_bullets(body, spec["bullets"])
        if spec.get("image"):
            image = str((base / spec["image"]).resolve())
            picture_ph = placeholder_of(slide, (PP_PLACEHOLDER.PICTURE,))
            if picture_ph is not None:
                picture_ph.insert_picture(image)  # crops to fill the placeholder
            else:
                add_picture_fit(slide, image, *content_box(prs, slide))
        if spec.get("table"):
            add_table(slide, spec["table"], content_box(prs, slide))
        if spec.get("chart"):
            add_chart(slide, spec["chart"], content_box(prs, slide))
        if spec.get("notes"):
            slide.notes_slide.notes_text_frame.text = spec["notes"]
        remove_empty_placeholders(slide)
    return prs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("outline", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--template", type=Path, help=".pptx whose masters and layouts to use")
    parser.add_argument("--keep-template-slides", action="store_true", help="keep the template's own slides")
    args = parser.parse_args()
    outline = json.loads(args.outline.read_text(encoding="utf-8"))
    try:
        prs = build(outline, args.outline.resolve().parent, args.template, args.keep_template_slides)
    except (KeyError, ValueError, IndexError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    prs.save(str(args.output))
    print(f"wrote {args.output} ({len(prs.slides)} slides)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
