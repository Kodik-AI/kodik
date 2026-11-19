---
name: pdf
description: Read, create, and modify PDF files with pypdf, pdfplumber and reportlab. Use when the user wants text or tables pulled out of a PDF, PDFs merged, split, reordered, rotated, watermarked or password-protected, a PDF form filled in, a new PDF generated (report, invoice, certificate), or a scanned PDF made readable. For converting Word, Excel or PowerPoint files to PDF, use the matching office skill.
---

# PDF files

Paths like `scripts/x.py` are relative to this skill's folder; run them with
that folder's absolute path.

## 1. Check the environment first

```bash
python scripts/check_env.py pdf        # use python3 on macOS/Linux if python is missing
```

`pypdf` is required; `pdfplumber` (layout text, tables), `reportlab` (new
PDFs) and `pypdfium2` (page images) are optional, install what the task needs.
Ask the user before installing, then use a project-local virtual environment,
never the system Python:

```bash
python -m venv .venv
.venv/bin/python -m pip install pypdf pdfplumber      # Windows: .venv\Scripts\python -m pip install pypdf pdfplumber
# or: uv venv .venv && uv pip install --python .venv pypdf pdfplumber reportlab
```

AES-encrypted PDFs also need `cryptography`. Command-line tools that help
when present: `qpdf` (repair, linearize), `pdftotext`/`pdftoppm` (poppler),
`ocrmypdf` (OCR). None is required.

## 2. Look before you work

```bash
python scripts/pdf_inspect.py file.pdf          # pages, paper sizes, rotation, metadata, fields, text per page
```

It tells you whether the file is encrypted, has form fields, and which pages
have no text layer (scans). Passwords: ask the user, then pass the password in
the `PDF_PASSWORD` environment variable (all scripts read it); never guess or
crack passwords.

## 3. Extract text and tables

```bash
python scripts/pdf_extract.py text file.pdf --pages 1-5          # plain text, "=== page N ===" separators
python scripts/pdf_extract.py text file.pdf --layout --out file.txt   # keep columns and spacing
python scripts/pdf_extract.py tables file.pdf tables/             # every table as CSV
python scripts/pdf_extract.py tables file.pdf tables/ --pages 3 --text-strategy   # tables without borders
python scripts/pdf_extract.py images file.pdf images/
```

In Python, for more control:

```python
import pdfplumber
with pdfplumber.open("file.pdf") as pdf:
    page = pdf.pages[0]
    text = page.extract_text()
    words = page.extract_words()                     # each with x0, x1, top, bottom
    region = page.crop((0, 0, page.width, page.height / 2)).extract_text()   # top half only
    tables = page.extract_tables({"vertical_strategy": "lines", "horizontal_strategy": "lines"})
```

Table extraction is heuristic. Check the CSVs: merged header cells become
empty strings, multi-line cells are joined with spaces, and a table that spans
pages comes out as one table per page (concatenate them, dropping the repeated
header). To load into pandas: `pd.read_csv(path, encoding="utf-8-sig")`.

Scanned PDFs (inspect says "probably scanned", text comes back empty): text
extraction cannot work. Options, in order:
1. `ocrmypdf --language rus+eng in.pdf out.pdf` adds a text layer, then extract
   from `out.pdf` (needs ocrmypdf with Tesseract and Ghostscript installed;
   ask before installing system packages).
2. Render the pages (`python scripts/convert.py file.pdf --png --dpi 200`)
   and run `pytesseract` on the PNGs, or read the images directly if you can
   view images.
Tell the user OCR text can contain errors, especially in numbers.

## 4. Merge, split, reorder, rotate, watermark, protect

```bash
python scripts/pdf_pages.py merge all.pdf cover.pdf report.pdf:2- appendix.pdf
python scripts/pdf_pages.py split big.pdf parts/                       # one file per page
python scripts/pdf_pages.py split big.pdf parts/ --ranges "1-3,4-10"   # chosen ranges
python scripts/pdf_pages.py select in.pdf out.pdf --pages "5,1-4"      # extract and reorder
python scripts/pdf_pages.py delete in.pdf out.pdf --pages "2,7-8"
python scripts/pdf_pages.py rotate in.pdf out.pdf --angle 90 --pages "3"
python scripts/pdf_pages.py stamp in.pdf out.pdf --overlay watermark.pdf          # on top
python scripts/pdf_pages.py stamp in.pdf out.pdf --overlay letterhead.pdf --under # behind
PDF_PASSWORD="the user's password" python scripts/pdf_pages.py encrypt in.pdf locked.pdf   # AES-256
```

On Windows PowerShell set the variable with `$env:PDF_PASSWORD = "..."` first.
A watermark or letterhead is just a one-page PDF; make it with reportlab
(section 6), for example large light-gray diagonal text:
`c.saveState(); c.setFillGray(0.85); c.translate(300, 420); c.rotate(45); c.setFont("Helvetica-Bold", 60); c.drawCentredString(0, 0, "DRAFT"); c.restoreState()`.

## 5. Fill forms

```bash
python scripts/pdf_form.py list form.pdf                 # field names, types, allowed values, page
python scripts/pdf_form.py template form.pdf > values.json
# edit values.json: text as strings, check boxes true/false, radio/choice as one listed option
python scripts/pdf_form.py fill form.pdf filled.pdf values.json
python scripts/pdf_form.py fill form.pdf final.pdf values.json --flatten   # no longer editable
```

Field names often differ from the visible labels; match them by the page,
tooltip and order `list` prints, and ask the user when unsure. Do not fill
signature fields.

Without `--flatten` the viewer draws the values, so any language works.
`--flatten` paints the current appearance of every field into the page; the
form's own font usually covers Latin only, so the script refuses to flatten
non-Latin text (Cyrillic and others). For a flat copy with such text, leave
those fields empty, flatten, and write the text with the overlay recipe below.

If `list` finds no fields, the form is flat (printed lines and boxes). Place
text at coordinates instead: find label positions with pdfplumber
(`page.extract_words()` gives `x0`, `top`; PDF coordinates start at the bottom
left, so `y = page.height - top`), write an overlay, and stamp it:

```python
import sys
sys.path.insert(0, "SKILL_FOLDER/scripts")     # this skill's scripts folder
import pdfplumber
from pdf_helpers import write_text_overlay

with pdfplumber.open("flat-form.pdf") as pdf:
    page = pdf.pages[0]
    label = next(w for w in page.extract_words() if w["text"] == "Name:")
    size = (float(page.width), float(page.height))
    y = size[1] - label["bottom"] + 2                # baseline just above the label's bottom edge
write_text_overlay("overlay.pdf", size, [{"x": label["x1"] + 6, "y": y, "text": "Ivan Petrov", "size": 11}])
# then: python scripts/pdf_pages.py stamp flat-form.pdf filled.pdf --overlay overlay.pdf --pages 1
```

## 6. Create a PDF from scratch

Use reportlab's Platypus layer (flowing paragraphs, tables, page breaks). For
any text outside Western European Latin, register a TrueType font first;
`register_unicode_font()` finds DejaVu, Noto, Liberation or Arial on Linux,
macOS and Windows.

```python
import sys
sys.path.insert(0, "SKILL_FOLDER/scripts")     # this skill's scripts folder
from pdf_helpers import register_unicode_font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

regular, bold = register_unicode_font()
styles = getSampleStyleSheet()
body = ParagraphStyle("Body", parent=styles["BodyText"], fontName=regular, fontSize=10.5, leading=14)
title = ParagraphStyle("Title", parent=styles["Title"], fontName=bold)
heading = ParagraphStyle("H2", parent=styles["Heading2"], fontName=bold)

def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(regular, 8)
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
    canvas.restoreState()

doc = SimpleDocTemplate("invoice.pdf", pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                        topMargin=2 * cm, bottomMargin=2 * cm, title="Invoice 42", author="Acme LLC")
rows = [["Item", "Qty", "Price", "Total"], ["Consulting", "10", "150.00", "1,500.00"],
        ["Hosting (Moscow)", "1", "80.00", "80.00"], ["", "", "Total", "1,580.00"]]
table = Table(rows, colWidths=[8 * cm, 2 * cm, 3 * cm, 3 * cm], repeatRows=1)
table.setStyle(TableStyle([
    ("FONTNAME", (0, 0), (-1, -1), regular), ("FONTNAME", (0, 0), (-1, 0), bold),
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCE6F1")),
    ("ALIGN", (1, 1), (-1, -1), "RIGHT"), ("GRID", (0, 0), (-1, -2), 0.5, colors.grey),
    ("FONTNAME", (2, -1), (-1, -1), bold),
]))
story = [Paragraph("Invoice 42", title), Paragraph("Issued 19 November 2026 to <b>Client Ltd</b>.", body),
         Spacer(1, 0.5 * cm), table, PageBreak(), Paragraph("Terms", heading),
         Paragraph("Payment within 14 days. " * 20, body)]
doc.build(story, onFirstPage=footer, onLaterPages=footer)
```

`Paragraph` takes a small XML markup (`<b>`, `<i>`, `<font color="red">`,
`<br/>`, `<a href="...">`): escape `&`, `<`, `>` in user text with
`xml.sax.saxutils.escape`. Images: `reportlab.platypus.Image(path, width=8*cm,
height=5*cm)`; keep the aspect ratio yourself. Charts: draw them with
matplotlib to PNG and add as an image.

Alternatives: if the content is already a Word/Excel/PowerPoint file or the
user wants an editable source, write that file and convert with LibreOffice
(`python scripts/convert.py report.docx`). HTML to PDF needs a browser engine
(headless Chrome `--print-to-pdf`) or WeasyPrint, if installed.

## 7. Verify before you report success

1. Re-open the output: `python scripts/pdf_inspect.py out.pdf` (page count,
   sizes, rotation, field count after filling, encryption as intended).
2. Check the content: `python scripts/pdf_extract.py text out.pdf --pages 1`
   shows the text landed (filled values appear only after flattening or in
   `pdf_form.py list`).
3. Look at it: `python scripts/convert.py out.pdf --png --pages 1-2` renders
   pages to PNG with `pypdfium2` (or `pdftoppm`), no LibreOffice needed. Check
   fonts (no black boxes), overlaps, cut-off tables, stamp position.
4. Report the output path, the page count, and anything not done (OCR quality,
   fields you were unsure about).

## Gotchas

- Write to a new file; the scripts refuse to overwrite their input.
- Page numbers in the scripts are 1-based; in pypdf/pdfplumber code they are
  0-based (`reader.pages[0]`).
- `/Rotate` only changes how a page is shown; extracted coordinates are in the
  unrotated page space.
- Signed PDFs: any change invalidates the signature. Tell the user before
  modifying one (`pdf_form.py list` shows signature fields).
- Large PDFs: process page by page and close files (`with pdfplumber.open(...)`).
