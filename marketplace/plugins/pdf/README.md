# PDF

Read, create and modify PDF files with `pypdf`, `pdfplumber` and `reportlab`.

## Skill

- `pdf`: extract text, tables and images; merge, split, reorder, rotate, watermark and password-protect; fill and flatten forms, or write onto flat forms; generate new PDFs with fonts that cover Cyrillic; detect scanned pages and point to OCR.

## Scripts

| Script | Purpose |
|--------|---------|
| `check_env.py pdf` | Reports Python, required and optional packages, and LibreOffice. Installs nothing. |
| `pdf_inspect.py` | Pages, paper sizes, rotation, metadata, encryption, form fields, outline, and pages without a text layer. |
| `pdf_extract.py` | Text (plain or layout), tables to CSV, embedded images. |
| `pdf_pages.py` | merge, split, select, delete, rotate, stamp (watermark or letterhead), encrypt, decrypt. |
| `pdf_form.py` | List form fields, write a values template, fill, flatten. |
| `pdf_helpers.py` | Finds and registers a Unicode TrueType font for reportlab; writes text overlays for flat forms. |
| `convert.py` | Renders PDF pages to PNG (pypdfium2 or pdftoppm); converts office files to PDF with LibreOffice. |

## Requirements

Python 3.9+ and `pypdf` (`pdfplumber`, `reportlab`, `pypdfium2` optional); the skill asks before installing into a project-local virtual environment. OCR needs `ocrmypdf` or Tesseract, which the skill only suggests.
