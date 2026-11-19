# Documents

Create, read and edit Word documents (`.docx`) with `python-docx`.

## Skill

- `word-documents`: build reports, letters and contracts on real styles (headings, lists, tables, captions, table of contents, page numbers, hyperlinks); extract text and tables; edit existing files while keeping their formatting; convert to PDF and render pages for a visual check.

## Scripts

| Script | Purpose |
|--------|---------|
| `check_env.py docx` | Reports Python, required and optional packages, and LibreOffice. Installs nothing. |
| `docx_inspect.py` | Outline of a document in reading order: styles, lists, tables, headers/footers, sections, comments, tracked changes. |
| `docx_replace.py` | Find and replace across runs, tables, headers, footers, text boxes and footnotes without losing formatting. |
| `docx_helpers.py` | Page number and TOC fields, hyperlinks, cell shading, repeating header rows, inserting/cloning/deleting paragraphs, opening `.dotx` templates. |
| `convert.py` | LibreOffice conversion (`.doc`/`.odt` to `.docx`, `.docx` to PDF) and PDF to PNG rendering. |

## Requirements

Python 3.9+ and `python-docx`; the skill asks before installing into a project-local virtual environment. LibreOffice is optional and only needed for conversion and rendering.
