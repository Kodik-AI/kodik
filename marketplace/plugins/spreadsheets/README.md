# Spreadsheets

Create, analyze and edit Excel workbooks (`.xlsx`, `.xlsm`) and CSV files with `openpyxl` and `pandas`.

## Skill

- `spreadsheets`: workbooks with live formulas, number formats, tables, conditional formatting, validation and charts; reading and analyzing data; CSV encodings and delimiters; editing existing workbooks without breaking formulas; checking formulas before handing a file over.

## Scripts

| Script | Purpose |
|--------|---------|
| `check_env.py xlsx` | Reports Python, required and optional packages, and LibreOffice. Installs nothing. |
| `xlsx_inspect.py` | Sheets, tables, charts, names, and a cell grid with formulas next to their stored results; encoding and delimiter detection for CSV. |
| `xlsx_check.py` | Formula audit: error results, references to missing sheets, error literals, formulas never calculated; optional LibreOffice recalculation of a copy. |
| `convert.py` | LibreOffice conversion (`.xls`/`.ods` to `.xlsx`, workbook to PDF) and PDF to PNG rendering. |

## Requirements

Python 3.9+ and `openpyxl` (`pandas` optional); the skill asks before installing into a project-local virtual environment. LibreOffice is optional and only needed for recalculation, conversion and rendering.
