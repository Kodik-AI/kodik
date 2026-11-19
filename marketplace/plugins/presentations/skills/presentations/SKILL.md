---
name: presentations
description: Create, read, and edit PowerPoint presentations (.pptx; .ppt/.odp via conversion) with python-pptx. Use when the user asks for a slide deck or pitch, wants slides built from notes, data or a document, wants a deck based on their company template, needs text, notes or images extracted from a .pptx, or wants an existing deck changed (rewording, new slides, replaced images, speaker notes) without breaking its design.
---

# Presentations (.pptx)

Work on decks with `python-pptx`. Paths like `scripts/x.py` are relative to
this skill's folder; run them with that folder's absolute path.

## 1. Check the environment first

```bash
python scripts/check_env.py pptx        # use python3 on macOS/Linux if python is missing
```

If `python-pptx` is missing, ask the user before installing, then install into
a project-local virtual environment, never into the system Python:

```bash
python -m venv .venv
.venv/bin/python -m pip install python-pptx          # Windows: .venv\Scripts\python -m pip install python-pptx
# or: uv venv .venv && uv pip install --python .venv python-pptx
```

LibreOffice (`soffice`) is optional; it renders slides to PDF/PNG so you can
look at them, and converts `.ppt`/`.odp` to `.pptx`. Without it, verify with
`pptx_inspect.py` (section 6) and tell the user the slides were not rendered.

## 2. How a deck is built

A presentation has slide masters; each master has layouts ("Title Slide",
"Title and Content", "Two Content", "Title Only", "Blank", ...); each layout
has placeholders identified by `idx` and type (TITLE, BODY, PICTURE, ...). A
slide is created from a layout and inherits its placeholders, fonts, colors and
background. Filling placeholders is what keeps a deck on-brand; free-floating
text boxes placed by hand drift from the design.

```bash
python scripts/pptx_inspect.py brand.pptx --layouts     # layouts with placeholder idx:type and names
python scripts/pptx_inspect.py deck.pptx                # every slide: shapes, boxes in cm, text, notes
python scripts/pptx_inspect.py deck.pptx --slide 4 --json
```

Placeholder `idx` values are not consecutive (0 title, 1 body, 10-12 date/
footer/number in the default template, anything in custom ones). Always look
them up; never assume `placeholders[1]` exists.

## 3. Read and extract

```python
from pptx import Presentation
prs = Presentation("deck.pptx")
for number, slide in enumerate(prs.slides, start=1):
    texts = [shape.text_frame.text for shape in slide.shapes if shape.has_text_frame]
    notes = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ""
    print(number, slide.slide_layout.name, texts, notes)
```

Tables are in `shape.table` (`shape.has_table`), charts in `shape.chart`
(`shape.has_chart`; data in `chart.plots[0].categories` and `series.values`),
grouped shapes in `shape.shapes`. Pictures expose `shape.image.blob` and
`shape.image.ext` to save them. `pptx_inspect.py` walks all of these.

## 4. Create a deck

Quickest path: write a JSON outline and build it. The script picks
placeholders by type, adds sub-bullets, pictures (fit or into a picture
placeholder), tables, native charts and speaker notes, and removes unused
placeholders. Its `--help` shows the full format.

```bash
python scripts/pptx_from_outline.py outline.json deck.pptx                      # default theme, 16:9
python scripts/pptx_from_outline.py outline.json deck.pptx --template brand.pptx  # user's layouts
```

When you need more control, use python-pptx directly:

```python
import sys
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Cm, Pt

sys.path.insert(0, "SKILL_FOLDER/scripts")      # this skill's scripts folder
from pptx_helpers import set_widescreen, layout_by_name, add_picture_fit, remove_empty_placeholders

prs = Presentation()                 # or Presentation("brand.pptx") to use the user's template
set_widescreen(prs)                  # default template is 4:3; this also moves its placeholders

slide = prs.slides.add_slide(layout_by_name(prs, "Title Slide"))
slide.shapes.title.text = "Q3 Review"
slide.placeholders[1].text = "Board meeting, October 2026"

slide = prs.slides.add_slide(layout_by_name(prs, "Title and Content"))
slide.shapes.title.text = "Highlights"
body = slide.placeholders[1].text_frame
body.text = "Revenue up 18% year over year"
sub = body.add_paragraph()
sub.text, sub.level = "Driven by two new regions", 1
point = body.add_paragraph()
point.text = "Support load down 30%"
point.runs[0].font.bold = True
slide.notes_slide.notes_text_frame.text = "Pause here for questions about the regions."

slide = prs.slides.add_slide(layout_by_name(prs, "Title Only"))
slide.shapes.title.text = "Revenue by quarter"
data = CategoryChartData()
data.categories = ["Q1", "Q2", "Q3"]
data.add_series("2025", (1.1, 1.3, 1.2))
data.add_series("2026", (1.4, 1.6, 1.9))
left, top = Cm(2), Cm(4)
chart = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, left, top,
                               prs.slide_width - 2 * left, prs.slide_height - top - Cm(1.5), data).chart
chart.has_legend = True

box = slide.shapes.add_textbox(Cm(2), prs.slide_height - Cm(1.5), Cm(20), Cm(1))
box.text_frame.text = "Source: finance export, 15 Oct 2026"
box.text_frame.paragraphs[0].runs[0].font.size = Pt(11)
box.text_frame.paragraphs[0].runs[0].font.color.rgb = RGBColor(0x60, 0x60, 0x60)
box.text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT

# slide = prs.slides.add_slide(layout_by_name(prs, "Title Only"))
# add_picture_fit(slide, "photo.jpg", Cm(2), Cm(4), Cm(29.8), Cm(13.5))  # keeps the aspect ratio

for each in prs.slides:
    remove_empty_placeholders(each)
prs.save("deck.pptx")
```

Design rules that make decks readable:
- One message per slide; the title states it ("Revenue grew 18%"), the body
  supports it. Three to six bullets, short lines, at most two levels.
- Keep body text 18 pt or larger and titles 28 pt or larger on 16:9 slides; if
  text does not fit, split the slide instead of shrinking the font.
- Use the template's colors and fonts. Native charts (`add_chart`) stay
  editable and match the theme; prefer them over chart images.
- Leave margins (about 1.5-2 cm) and align shapes to the same left edge.
- Put the talk track in speaker notes, not on the slide.
- Units: `Cm`, `Inches`, `Pt` from `pptx.util`; raw numbers are EMU (360000 per cm).

## 5. Edit an existing deck

Save to a new file, verify, then replace the original only if the user wants.

- Reword while keeping formatting: change `run.text`, not `shape.text` or
  `text_frame.text` (both reset the runs). For find-and-replace across all
  slides, tables, groups and notes:
  ```python
  from pptx_helpers import replace_text
  count = replace_text(prs, "FY2025", "FY2026")      # keeps the formatting of the run where each match starts
  ```
- Add slides with the deck's own layouts (`pptx_inspect.py --layouts`), never by
  copying text boxes from other slides.
- Reorder, delete, duplicate (python-pptx has no API for these):
  ```python
  from pptx_helpers import move_slide, delete_slide, duplicate_slide
  move_slide(prs, 5, 1)          # 0-based indexes
  delete_slide(prs, 3)
  copy = duplicate_slide(prs, 2) # appended at the end; charts stay shared with the original
  ```
- Replace a picture: note its box (`left/top/width/height`), delete the shape
  (`pptx_helpers.remove_shape`), add the new image into the same box with
  `add_picture_fit`. For a picture placeholder, use `placeholder.insert_picture`.
- Update chart data in place: `chart.replace_data(new_chart_data)` keeps the
  chart's formatting.
- Speaker notes: `slide.notes_slide.notes_text_frame.text = "..."` (creates the
  notes page when missing).
- A template (`.potx`) or old `.ppt`: convert first with
  `python scripts/convert.py brand.potx --to pptx` (needs LibreOffice), or ask
  the user to save it as `.pptx`.

## 6. Verify before you report success

1. Structure: `python scripts/pptx_inspect.py deck.pptx`. Check the slide count,
   titles, bullets, notes, and the WARNING lines (shapes past the slide edge,
   empty placeholders).
2. Render when LibreOffice exists:
   `python scripts/convert.py deck.pptx --png --outdir preview`, then look at
   each PNG: text overflowing its box, overlapping shapes, unreadable contrast,
   distorted images, empty slides. Fix and re-render.
3. Without LibreOffice, check text length per placeholder (roughly 6 bullets of
   up to 60 characters for a full-width body at 18-20 pt) and say the visual
   check was not possible.
4. Report the file path, the slide list, and anything left for the user (for
   example, fonts the template uses that are not installed).

## Gotchas

- `slide.shapes.title` is None on layouts without a title placeholder.
- `text_frame.fit_text()` picks one font size for the whole shape and needs the
  font file (pass `font_file=` on Linux); shortening or splitting text is better.
- Pictures: give only a width or a height to keep the aspect ratio, or use
  `add_picture_fit`. SVG is not supported; convert to PNG first.
- Large images make large decks; resize photos to about 2000 px wide before
  adding them.
