"""reportlab helpers: a Unicode font that exists on this machine, and text overlays.

Import from a script:
    import sys; sys.path.insert(0, "<this folder>")
    from pdf_helpers import register_unicode_font, write_text_overlay
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# (regular, bold) pairs; the first pair whose regular file exists wins.
_FONT_CANDIDATES = [
    ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
    ("NotoSans-Regular.ttf", "NotoSans-Bold.ttf"),
    ("LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf"),
    ("arial.ttf", "arialbd.ttf"),
    ("Arial.ttf", "Arial Bold.ttf"),
    ("Arial Unicode.ttf", None),
]


def _font_dirs() -> list[Path]:
    if os.name == "nt":
        return [Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts"]
    if sys.platform == "darwin":
        return [Path("/System/Library/Fonts/Supplemental"), Path("/Library/Fonts"), Path.home() / "Library/Fonts"]
    return [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), Path.home() / ".local/share/fonts",
            Path.home() / ".fonts"]


def find_font_file(filename: str) -> Path | None:
    for base in _font_dirs():
        if not base.is_dir():
            continue
        direct = base / filename
        if direct.is_file():
            return direct
        for found in base.rglob(filename):
            return found
    return None


def register_unicode_font(regular: str | None = None, bold: str | None = None) -> tuple[str, str]:
    """Register a TrueType font that covers Cyrillic and most Latin scripts; return (regular, bold) names.

    The built-in PDF fonts (Helvetica, Times) only cover Western European
    characters; anything else prints as black boxes. Pass explicit .ttf paths to
    use a specific font. Falls back to Helvetica (with a warning) if no font is found.
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    pairs = [(Path(regular), Path(bold) if bold else None)] if regular else [
        (find_font_file(r), find_font_file(b) if b else None) for r, b in _FONT_CANDIDATES]
    for regular_path, bold_path in pairs:
        if regular_path is None or not regular_path.is_file():
            continue
        pdfmetrics.registerFont(TTFont("DocSans", str(regular_path)))
        bold_name = "DocSans"
        if bold_path is not None and bold_path.is_file():
            pdfmetrics.registerFont(TTFont("DocSans-Bold", str(bold_path)))
            bold_name = "DocSans-Bold"
        from reportlab.lib.fonts import addMapping
        addMapping("DocSans", 0, 0, "DocSans")
        addMapping("DocSans", 1, 0, bold_name)
        addMapping("DocSans", 0, 1, "DocSans")
        addMapping("DocSans", 1, 1, bold_name)
        return "DocSans", bold_name
    print("warning: no Unicode TrueType font found; using Helvetica (Latin-1 only)", file=sys.stderr)
    return "Helvetica", "Helvetica-Bold"


def write_text_overlay(path: str | Path, page_size: tuple[float, float], items: list[dict], font: str | None = None) -> Path:
    """Write a one-page PDF with text at given positions, to stamp onto another PDF.

    items: [{"x": 72, "y": 700, "text": "Ivanov I.I.", "size": 11}, ...] in points
    (1/72 inch) measured from the bottom-left corner, as pdfplumber reports
    them with y = page height - top.
    """
    from reportlab.pdfgen import canvas

    font = font or register_unicode_font()[0]
    pdf = canvas.Canvas(str(path), pagesize=page_size)
    for item in items:
        pdf.setFont(item.get("font", font), item.get("size", 10))
        pdf.drawString(item["x"], item["y"], item["text"])
    pdf.save()
    return Path(path)
