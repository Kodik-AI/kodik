---
name: spreadsheets
description: Create, read, analyze, and edit spreadsheets (.xlsx, .xlsm, .csv, .tsv; legacy .xls via conversion) with openpyxl and pandas. Use when the user asks for an Excel workbook, a financial model, a report table with formulas, number formats or charts; to extract or analyze data from a spreadsheet or CSV; or to change an existing workbook without breaking its formulas and formatting.
---

# Spreadsheets (.xlsx, .csv)

Work on workbooks with `openpyxl` (cells, formulas, styles, charts) and on data
with `pandas` (analysis, CSV, bulk reads). Paths like `scripts/x.py` are
relative to this skill's folder; run them with that folder's absolute path.

## 1. Check the environment first

```bash
python scripts/check_env.py xlsx        # use python3 on macOS/Linux if python is missing
```

If a required package is missing, ask the user before installing, then install
into a project-local virtual environment, never into the system Python:

```bash
python -m venv .venv
.venv/bin/python -m pip install openpyxl pandas      # Windows: .venv\Scripts\python -m pip install openpyxl pandas
# or: uv venv .venv && uv pip install --python .venv openpyxl pandas
```

LibreOffice (`soffice`) is optional: it recalculates formulas, converts `.xls`
and `.ods` to `.xlsx`, and renders sheets to PDF/PNG. Without it, verify with
the scripts below and say that values were not recalculated by a spreadsheet
application.

## 2. Pick the tool

- **openpyxl** for anything that must stay a real workbook: formulas, styles,
  number formats, merged cells, charts, validation, several sheets, editing a
  file the user made.
- **pandas** for analysis, filtering, joins, aggregation, and CSV. Never use
  `DataFrame.to_excel` to change an existing formatted workbook: it writes a new
  file (or replaces the sheet), losing formatting, formulas and charts. Write
  with pandas only into new files, then style them with openpyxl.
- `.xls` (Excel 97-2003): `python scripts/convert.py old.xls --to xlsx`, or read
  only with `pandas.read_excel(path)` plus the `xlrd` package.

## 3. Read and extract

```bash
python scripts/xlsx_inspect.py book.xlsx                       # every sheet: size, tables, charts, first cells
python scripts/xlsx_inspect.py book.xlsx --sheet Data --range A1:H40
python scripts/xlsx_inspect.py export.csv                      # encoding, delimiter, header, first rows
```

Formulas are printed as `=SUM(B2:B9) -> 4200`: the formula and its stored
result. `(not calculated)` means the file was saved by a program that does not
calculate (openpyxl, many exporters).

```python
import pandas as pd
sheets = pd.read_excel("book.xlsx", sheet_name=None)            # {sheet name: DataFrame}
df = pd.read_excel("book.xlsx", sheet_name="Data", header=2, usecols="A:F", dtype={"Code": str})

from openpyxl import load_workbook
formulas = load_workbook("book.xlsx")                  # cell.value is "=SUM(...)" for formula cells
values = load_workbook("book.xlsx", data_only=True)    # cell.value is the stored result (None if never calculated)
```

pandas reads stored results, not formulas. Header rows above the table, merged
title cells and totals rows are common; inspect first, then set `header=`,
`skiprows=`, `nrows=` or `usecols=`.

## 4. Create a workbook

Put inputs in cells and derive everything else with formulas, so the workbook
stays live when the user changes an input. Compute in Python only to check
results, not to paste them as numbers.

```python
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

wb = Workbook()
ws = wb.active
ws.title = "Sales"
inputs = wb.create_sheet("Inputs")
inputs["A1"], inputs["B1"] = "Tax rate", 0.2
inputs["B1"].number_format = "0%"
wb.defined_names["TaxRate"] = DefinedName("TaxRate", attr_text="Inputs!$B$1")

header = ["Region", "Units", "Price", "Revenue", "Tax", "Status"]
data = [("North", 120, 15.5), ("South", 95, 17.0), ("East", 143, 14.25), ("West", 80, 19.9)]
ws.append(header)
for region, units, price in data:
    ws.append([region, units, price])
last = ws.max_row
for row in range(2, last + 1):
    ws[f"D{row}"] = f"=B{row}*C{row}"
    ws[f"E{row}"] = f"=D{row}*TaxRate"
    ws[f"F{row}"] = f'=IF(D{row}>=1800,"on target","below")'
ws[f"A{last + 1}"] = "Total"
for col in "BDE":
    ws[f"{col}{last + 1}"] = f"=SUM({col}2:{col}{last})"

bold, thin = Font(bold=True), Side(style="thin", color="999999")
for cell in ws[1]:
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="305496")
    cell.alignment = Alignment(horizontal="center")
for cell in ws[last + 1]:
    cell.font = bold
    cell.border = Border(top=thin)
for row in ws.iter_rows(min_row=2, max_row=last + 1):
    row[1].number_format = "#,##0"
    row[2].number_format = "#,##0.00"
    row[3].number_format = row[4].number_format = "#,##0.00"
for index, width in enumerate([14, 10, 10, 14, 12, 12], start=1):
    ws.column_dimensions[get_column_letter(index)].width = width
ws.freeze_panes = "A2"                      # keep the header visible

table = Table(displayName="SalesTable", ref=f"A1:F{last}")   # filters + banded rows; excludes the total row
table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
ws.add_table(table)
ws.conditional_formatting.add(f"D2:D{last}", CellIsRule(operator="lessThan", formula=["1800"],
                              fill=PatternFill("solid", fgColor="F8CBAD")))
regions = DataValidation(type="list", formula1='"North,South,East,West"', allow_blank=False)
ws.add_data_validation(regions)
regions.add(f"A2:A{last}")                 # dropdown on the region cells

chart = BarChart()
chart.title, chart.y_axis.title = "Revenue by region", "Revenue"
chart.add_data(Reference(ws, min_col=4, min_row=1, max_row=last), titles_from_data=True)
chart.set_categories(Reference(ws, min_col=1, min_row=2, max_row=last))
chart.width, chart.height = 16, 8           # centimeters
ws.add_chart(chart, "H2")

wb.save("sales.xlsx")
```

Formula rules:
- Write formulas in English with comma separators (`=IF(A1>0,1,0)`), whatever
  the user's Excel language; the file format stores them that way.
- Quote sheet names with spaces: `='Q3 Plan'!B4`. Use `$B$1` or a defined name
  for constants every row refers to.
- Functions newer than Excel 2010 need their stored prefix in openpyxl, or
  Excel shows `#NAME?`: `_xlfn.XLOOKUP`, `_xlfn.IFS`, `_xlfn.CONCAT`,
  `_xlfn.TEXTJOIN`, `_xlfn.MAXIFS`, `_xlfn.SWITCH`. Dynamic-array functions
  (`FILTER`, `UNIQUE`, `SORT`, `SEQUENCE`) spill and need `_xlfn._xlws.` or
  `_xlfn.` prefixes plus array metadata; prefer classic functions
  (`SUMIFS`, `INDEX`/`MATCH`) unless the user asks for them.
- Avoid volatile functions (`INDIRECT`, `OFFSET`, `NOW`, `TODAY`) in large
  models; they recalculate on every change.
- Dates: write `datetime.date` objects and set `number_format = "yyyy-mm-dd"`
  (or `dd.mm.yyyy`); strings that look like dates stay text.
- Percent cells hold fractions: store `0.2` with format `0%`, not `20`.
- Common formats: `#,##0`, `#,##0.00`, `0.0%`, `#,##0.00 "RUB"`,
  `[$$-409]#,##0.00`, `#,##0;[Red]-#,##0`, `@` (text, keeps leading zeros).

From a DataFrame, write first and style after:

```python
import pandas as pd
from openpyxl import load_workbook
df = pd.DataFrame({"Date": pd.date_range("2026-01-01", periods=3), "Amount": [1200.5, 990.0, 1430.25]})
with pd.ExcelWriter("export.xlsx", engine="openpyxl") as writer:
    df.to_excel(writer, sheet_name="Data", index=False)
wb = load_workbook("export.xlsx")
ws = wb["Data"]
for cell in ws["A"][1:]:
    cell.number_format = "yyyy-mm-dd"
for cell in ws["B"][1:]:
    cell.number_format = "#,##0.00"
ws.column_dimensions["A"].width = 12
wb.save("export.xlsx")
```

Other charts work the same way: `LineChart`, `PieChart`, `ScatterChart`
(needs `Series(yvalues, xvalues)`), `AreaChart`; `chart.type = "bar"` makes a
horizontal bar chart. Charts reference cells, so they update with the data.

## 5. Edit an existing workbook

Write the result to a new file, verify, then replace the original only if the
user wants that.

```python
from openpyxl import load_workbook
wb = load_workbook("model.xlsx")                 # NOT data_only=True: saving that drops every formula
# wb = load_workbook("model.xlsm", keep_vba=True) for macro workbooks; save with the .xlsm suffix
ws = wb["Inputs"]
ws["B3"] = 0.07                                   # change an input; formulas elsewhere stay intact
ws["B3"].number_format = "0.0%"
wb.calculation.fullCalcOnLoad = True              # stored results are stale now; Excel recalculates on open
wb.save("model-updated.xlsx")
```

What to watch:
- openpyxl keeps cell values, formulas, styles, merged cells, defined names,
  tables, validation, conditional formatting, comments, images and charts it
  can parse (chart styling can be simplified), and pivot tables. It drops
  shapes and text boxes, form controls, slicers, timelines, sparklines and
  other extensions. Ask before editing a workbook that relies on those, or
  edit it in Excel/LibreOffice instead.
- `insert_rows`, `delete_rows`, `insert_cols`, `move_range` shift cells but do
  not rewrite formulas, defined names, tables, merged ranges, validation or
  chart references that point at the moved cells. Prefer appending rows at the
  end of a block and extending ranges (`=SUM(B2:B50)` to `B51`, a table's `ref`)
  explicitly; after a structural change, grep the formulas and fix them.
- New cells do not inherit style. Copy it from a neighbor:
  `from copy import copy; new._style = copy(old._style)`.
- Keep the user's conventions: same fonts, fills, number formats, column
  widths, sheet order. Check them with `xlsx_inspect.py` first.
- Do not turn formulas into values unless asked. If you must, keep a copy.

## 6. CSV and other text data

```python
import pandas as pd
df = pd.read_csv("export.csv", sep=None, engine="python", encoding="utf-8-sig",
                 dtype={"inn": str, "zip": str})             # sep=None sniffs , ; tab |
# Russian Excel exports are often cp1251 with ";" and decimal commas:
df = pd.read_csv("export.csv", sep=";", decimal=",", thousands=" ", encoding="cp1251")
df.to_csv("clean.csv", index=False, encoding="utf-8-sig")    # BOM so Excel detects UTF-8
df.to_csv("for-excel-ru.csv", index=False, sep=";", decimal=",", encoding="utf-8-sig")
```

`xlsx_inspect.py` reports the encoding and delimiter it detected; treat the
encoding as a guess and look at the text. Read identifiers (INN, phone, ZIP,
article codes) as strings so leading zeros survive. Parse dates explicitly
(`pd.to_datetime(df["date"], format="%d.%m.%Y")`) instead of guessing.

## 7. Verify before you report success

1. Formula audit:
   ```bash
   python scripts/xlsx_check.py out.xlsx            # error results, missing sheets, #REF! in formulas
   python scripts/xlsx_check.py out.xlsx --recalc   # recalculates a copy with LibreOffice first
   ```
   Fix every error result and broken reference. Without LibreOffice, freshly
   written formulas have no stored result; check the logic by computing the
   expected numbers for a few cells in Python and comparing with what the
   formula would give.
2. Re-open and look: `python scripts/xlsx_inspect.py out.xlsx` (formulas,
   formats, tables, charts present, nothing unexpected on other sheets).
3. Visual check when LibreOffice exists:
   `python scripts/convert.py out.xlsx --png --outdir preview` renders the
   printable area of each sheet; check headers, number formats (`####` means a
   column is too narrow) and charts.
4. Tell the user what changed, where the file is, and whether values were
   recalculated or will be computed when they open it.
