---
name: word-documents
description: Create, read, and edit Word documents (.docx, also .dotx templates and legacy .doc via conversion) with python-docx. Use when the user asks to write a report, letter, contract, or other Word file; to extract text or tables from a .docx; to fill or change an existing document while keeping its formatting; or to convert a document to PDF. Not for PDFs (use the pdf skill) or Markdown-only notes.
---

# Word documents (.docx)

Work on `.docx` files with Python and `python-docx`. Paths like `scripts/x.py`
are relative to this skill's folder; run them with that folder's absolute path.

## 1. Check the environment first

```bash
python scripts/check_env.py docx        # use python3 on macOS/Linux if python is missing
```

It reports Python, `python-docx`, the optional `pypdfium2` (PNG previews), and
LibreOffice. If something required is missing, ask the user before installing,
then install into a project-local virtual environment, never into the system
Python:

```bash
python -m venv .venv
.venv/bin/python -m pip install python-docx          # Windows: .venv\Scripts\python -m pip install python-docx
# or: uv venv .venv && uv pip install --python .venv python-docx
```

Then run every script with that interpreter (`.venv/bin/python`,
`.venv\Scripts\python`). Add `.venv/` to `.gitignore` if the project is a repo.

LibreOffice (`soffice`) is optional. It converts `.doc`/`.odt`/`.rtf` to `.docx`,
`.docx` to PDF, and lets you look at the rendered pages. When it is missing, skip
rendering and verify structurally (section 6); tell the user the visual check
was not possible and that installing LibreOffice would enable it.

## 2. Read and extract

```bash
python scripts/docx_inspect.py report.docx            # outline: styles, lists, tables, headers, sections
python scripts/docx_inspect.py report.docx --json     # the same as JSON for further processing
```

The `[pN]` indexes it prints are positions in `Document(path).paragraphs`, so
you can target edits with them. It also flags tracked changes, comments and text
boxes, whose content is easy to miss.

For plain text in Python:

```python
from docx import Document
doc = Document("report.docx")
text = "\n".join(p.text for p in doc.paragraphs)
tables = [[[cell.text for cell in row.cells] for row in table.rows] for table in doc.tables]
```

`doc.paragraphs` and `doc.tables` only hold top-level body content; nested tables
live in `cell.tables`, and headers/footers in `doc.sections[i].header`. Merged
cells repeat the same cell object across the merged range, so deduplicate when
you count cells.

Legacy `.doc`, `.rtf`, `.odt`: convert first with
`python scripts/convert.py old.doc --to docx`. Without LibreOffice, ask the user
to save the file as `.docx`.

## 3. Create a document from scratch

Build on the default template's built-in styles (`Title`, `Heading 1..9`,
`List Bullet`, `List Number`, `Table Grid`, `Caption`, `Quote`) instead of
formatting every run by hand: styles keep the document consistent, produce a
real outline, and feed the table of contents.

```python
import sys
from datetime import datetime, timezone
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.shared import Cm, Pt, RGBColor

sys.path.insert(0, "SKILL_FOLDER/scripts")      # this skill's scripts folder
from docx_helpers import add_page_number_field, add_table_of_contents, add_hyperlink, set_cell_background, repeat_as_header_row

doc = Document()
section = doc.sections[0]
section.page_width, section.page_height = Cm(21.0), Cm(29.7)   # A4; Letter is 21.59 x 27.94
for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
    setattr(section, side, Cm(2.0))

normal = doc.styles["Normal"]
normal.font.name = "Calibri"
normal.font.size = Pt(11)

doc.add_paragraph("Quarterly Report", style="Title")
doc.add_paragraph("Prepared for the board, Q3 2026").alignment = WD_ALIGN_PARAGRAPH.CENTER
add_table_of_contents(doc.add_paragraph())
doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

doc.add_heading("Summary", level=1)
p = doc.add_paragraph("Revenue grew ")
p.add_run("18%").bold = True
p.add_run(" year over year. Details: ")
add_hyperlink(p, "https://example.com/q3", "full dashboard")
doc.add_paragraph("New enterprise customers", style="List Bullet")
doc.add_paragraph("Lower support load", style="List Bullet")
doc.add_paragraph("Hire two engineers", style="List Number")

doc.add_heading("Figures", level=1)
rows = [("Region", "Revenue", "Change"), ("North", "1,200,000", "+12%"), ("South", "950,000", "+25%")]
table = doc.add_table(rows=len(rows), cols=3, style="Table Grid")
table.alignment = WD_TABLE_ALIGNMENT.CENTER
for r, values in enumerate(rows):
    for c, value in enumerate(values):
        cell = table.cell(r, c)
        cell.text = value
        if c > 0:
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
for cell in table.rows[0].cells:
    cell.paragraphs[0].runs[0].bold = True
    set_cell_background(cell, "D9E2F3")
repeat_as_header_row(table.rows[0])
doc.add_paragraph("Table 1. Revenue by region", style="Caption")

# doc.add_picture("chart.png", width=Cm(15))   # give only a width to keep the aspect ratio

wide = doc.add_section()                          # a landscape section for a wide table
wide.orientation = WD_ORIENT.LANDSCAPE
wide.page_width, wide.page_height = section.page_height, section.page_width
doc.add_heading("Appendix", level=1)

footer = section.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
footer.text = "Page "
add_page_number_field(footer, with_total=True)

props = doc.core_properties                       # the blank template carries placeholder metadata
props.title, props.author = "Quarterly Report", "Finance team"
props.created = props.modified = datetime.now(timezone.utc)
doc.save("report.docx")
```

Notes:
- `doc.add_heading(text, level)` uses `Heading N`; level 0 is `Title`.
- `RGBColor(0x1F, 0x4E, 0x79)` on `run.font.color.rgb` for colored text; set
  fonts on styles when the change should apply everywhere.
- A new section inherits the previous section's header/footer
  (`is_linked_to_previous` is True) until you set its own.
- Fields (page numbers, TOC) are computed by Word or LibreOffice when the file
  is opened or printed; python-docx cannot compute them. Word may ask to update
  fields when it opens a file with a TOC; that is expected.
- Non-Latin text (Cyrillic, CJK) works as normal strings; pick a font that has
  the glyphs (Calibri, Arial, Times New Roman, Noto) if you set one.

## 4. Edit an existing document and keep its formatting

Always write to a new file (`report-edited.docx`), verify it, and only then
replace the original if the user wants that.

Rules that keep formatting intact:
- Change text at the run level. `paragraph.text = "..."` deletes every run and
  its formatting; prefer editing `run.text` of the run that should keep its look.
- For find-and-replace (names, dates, placeholders like `{{client}}`) use the
  script, which handles text that Word split across runs and covers tables,
  headers, footers, text boxes, footnotes and comments:

  ```bash
  python scripts/docx_replace.py contract.docx contract-filled.docx -r "{{client}}" "Acme LLC" -r "{{date}}" "1 December 2026"
  python scripts/docx_replace.py contract.docx --dry-run -r "Acme" "Acme LLC"   # count first
  python scripts/docx_replace.py contract.docx out.docx --pairs values.json     # {"old": "new"}
  ```
  The replacement takes the formatting of the run where the match starts.
- Reuse the document's own styles (`docx_inspect.py` lists the ones in use)
  rather than adding direct formatting. `doc.styles` lists every defined style.
- To add content in the middle, insert relative to an existing paragraph:

  ```python
  from docx_helpers import insert_paragraph_after, clone_paragraph_after, delete_paragraph
  anchor = doc.paragraphs[12]
  anchor.insert_paragraph_before("New paragraph above", style=anchor.style)
  insert_paragraph_after(anchor, "New paragraph below", style="Normal")
  clone_paragraph_after(doc.paragraphs[20], "Another list item like the one above")  # same numbering + run look
  delete_paragraph(doc.paragraphs[30])
  ```
  `doc.add_paragraph` always appends at the end of the body (after the last
  table or section break).
- Tables: `table.add_row()` appends a row that copies nothing but the grid; copy
  formatting from the row above by setting the same style, or deep-copy the row
  element (`copy.deepcopy(row._tr)` then `table._tbl.append(...)`) and change
  its cell texts through `run.text`.
- Templates: `Document()` cannot open `.dotx`/`.dotm`. Use
  `from docx_helpers import open_document; doc = open_document("letterhead.dotx")`,
  which opens the template as a new document; save it as `.docx`.
- Tracked changes and comments: python-docx does not accept or reject
  revisions. `docx_inspect.py` tells you they exist; mention that to the user
  before editing such text. Comments can be read (`doc.comments`) and added
  with `doc.add_comment(runs, text=..., author=...)` in python-docx 1.2+.
- Images: `run.add_picture(path, width=Cm(8))` inside an existing paragraph;
  replacing an existing image is easiest by deleting its paragraph and adding a
  new picture at the same position.

## 5. Convert

```bash
python scripts/convert.py report.docx                 # -> report.pdf next to it
python scripts/convert.py report.docx --png --pages 1-2 --outdir preview
python scripts/convert.py notes.odt --to docx
```

Exit code 2 means LibreOffice (or a PNG renderer) is missing. There is no
faithful pure-Python `.docx` to PDF converter; if the user needs a PDF and
LibreOffice is unavailable, say so and suggest installing it or exporting from
Word. For Markdown output, `pandoc report.docx -t gfm -o report.md` works when
pandoc is installed.

## 6. Verify before you report success

1. Re-open the saved file: `python scripts/docx_inspect.py out.docx`. Check that
   headings, list items, tables, headers/footers and replaced values are what
   you intended and nothing else changed (compare with the inspect output of
   the original when editing).
2. If LibreOffice is available, render and look at the pages:
   `python scripts/convert.py out.docx --png --outdir preview`, then open the
   PNGs. Look for overflowing tables, wrong page orientation, empty pages,
   missing images and broken fonts (boxes instead of letters).
3. Without LibreOffice, state that the layout was checked structurally only.
4. Tell the user where the file is and what changed; mention anything you could
   not do (fields not computed, tracked changes left as they were).

## Gotchas

- Units: use `Cm`, `Inches`, `Pt` from `docx.shared`; raw numbers are EMU.
- `style=` names are the English built-in names even in localized Word.
  A style that the document never defined raises `KeyError`; check `doc.styles`.
- Line break inside a paragraph: `run.add_break()` (python-docx also turns
  `\n` in `run.text` into one); page break: `run.add_break(WD_BREAK.PAGE)`.
  For a new paragraph use `add_paragraph`, not `\n`.
- Lists: `List Bullet 2` / `List Number 2` for nested levels. Restarting numbering
  needs numbering XML; if exact numbering matters, copy an existing numbered
  paragraph with `clone_paragraph_after`.
- Large documents: python-docx loads everything in memory; that is fine up to
  hundreds of pages.
