# Presentations

Create, read and edit PowerPoint decks (`.pptx`) with `python-pptx`.

## Skill

- `presentations`: decks built from layouts and placeholders (your template or the default theme in 16:9), bullets, native charts, tables, images and speaker notes; extracting slide text and notes; editing existing decks (rewording, reordering, duplicating, replacing images) without breaking the design; rendering slides for a visual check.

## Scripts

| Script | Purpose |
|--------|---------|
| `check_env.py pptx` | Reports Python, required and optional packages, and LibreOffice. Installs nothing. |
| `pptx_inspect.py` | Layouts with placeholder ids, and every slide's shapes, positions, text and notes, with warnings for off-slide shapes and empty placeholders. |
| `pptx_from_outline.py` | Builds a deck from a JSON outline (titles, bullets, images, tables, charts, notes), optionally on a template. |
| `pptx_helpers.py` | Widescreen resize that moves the template's placeholders, layout lookup, slide delete/move/duplicate, text replace that keeps formatting, aspect-preserving pictures. |
| `convert.py` | LibreOffice conversion (`.ppt`/`.odp` to `.pptx`, deck to PDF) and PDF to PNG rendering. |

## Requirements

Python 3.9+ and `python-pptx`; the skill asks before installing into a project-local virtual environment. LibreOffice is optional and only needed for conversion and rendering.
