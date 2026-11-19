#!/usr/bin/env python3
"""Convert an office file with LibreOffice and optionally render pages to PNG.

Usage:
    python convert.py INPUT [--to pdf|docx|xlsx|pptx|csv|odt|...] [--outdir DIR]
                            [--png] [--dpi 100] [--pages 1-3] [--timeout 180]

Examples:
    python convert.py report.docx --png          # report.pdf + report-p1.png ...
    python convert.py old.doc --to docx          # legacy format to OOXML
    python convert.py slides.pdf --png --pages 1 # PDF input skips LibreOffice

LibreOffice runs headless with a throw-away profile, so it works while the
user has LibreOffice open. PNG rendering uses pypdfium2 when installed and
falls back to the pdftoppm command. Exit codes: 0 ok, 1 failure,
2 LibreOffice (or a PNG renderer) is not installed.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_env import find_soffice  # noqa: E402


def parse_pages(spec: str | None, count: int) -> list[int]:
    """'1-3,5,8-' -> zero-based indexes, clamped to the page count."""
    if not spec:
        return list(range(count))
    pages: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start = int(start_s) if start_s else 1
            end = int(end_s) if end_s else count
        else:
            start = end = int(part)
        for number in range(max(start, 1), min(end, count) + 1):
            if number - 1 not in pages:
                pages.append(number - 1)
    return pages


def libreoffice_convert(src: Path, target: str, outdir: Path, timeout: int) -> Path:
    soffice = find_soffice()
    if not soffice:
        raise FileNotFoundError("LibreOffice (soffice) is not installed or not on PATH; set SOFFICE_PATH to its binary")
    outdir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lo-profile-") as profile, \
            tempfile.TemporaryDirectory(prefix="lo-out-") as staging:
        cmd = [soffice, f"-env:UserInstallation={Path(profile).as_uri()}", "--headless",
               "--norestore", "--convert-to", target, "--outdir", staging, str(src)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        produced = sorted(Path(staging).iterdir())
        if result.returncode != 0 or not produced:
            raise RuntimeError(f"LibreOffice conversion failed (exit {result.returncode}):\n"
                               f"{result.stdout.strip()}\n{result.stderr.strip()}".strip())
        # Staging keeps a same-format conversion (x.xlsx -> x.xlsx) from overwriting the source.
        out = outdir / produced[0].name
        if out.resolve() == src.resolve():
            out = outdir / f"{src.stem}.converted{produced[0].suffix}"
        shutil.move(str(produced[0]), out)
        return out


def render_png(pdf: Path, outdir: Path, dpi: int, pages_spec: str | None) -> list[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    try:
        import pypdfium2 as pdfium
    except ImportError:
        pdfium = None
    if pdfium is not None:
        doc = pdfium.PdfDocument(str(pdf))
        if hasattr(doc, "init_forms"):
            doc.init_forms()  # draw form fields (values, check marks) too
        try:
            for index in parse_pages(pages_spec, len(doc)):
                image = doc[index].render(scale=dpi / 72).to_pil()
                target = outdir / f"{pdf.stem}-p{index + 1}.png"
                image.save(target)
                written.append(target)
        finally:
            doc.close()
        return written
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise FileNotFoundError("no PNG renderer: install pypdfium2 (pip) or poppler's pdftoppm")
    try:
        from pypdf import PdfReader  # only for the page count
        count = len(PdfReader(str(pdf)).pages)
    except ImportError:
        info = subprocess.run([shutil.which("pdfinfo") or "pdfinfo", str(pdf)], capture_output=True, text=True)
        count = next(int(line.split()[-1]) for line in info.stdout.splitlines() if line.startswith("Pages:"))
    for index in parse_pages(pages_spec, count):
        prefix = outdir / f"{pdf.stem}-p{index + 1}"
        subprocess.run([pdftoppm, "-png", "-r", str(dpi), "-f", str(index + 1), "-l", str(index + 1),
                        "-singlefile", str(pdf), str(prefix)], check=True)
        written.append(prefix.with_suffix(".png"))
    return written


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path)
    parser.add_argument("--to", default="pdf", help="target format for LibreOffice (default: pdf)")
    parser.add_argument("--outdir", type=Path, help="output folder (default: next to the input)")
    parser.add_argument("--png", action="store_true", help="also render the PDF pages to PNG")
    parser.add_argument("--dpi", type=int, default=100)
    parser.add_argument("--pages", help="pages to render, e.g. 1-3,5 (default: all)")
    parser.add_argument("--timeout", type=int, default=180, help="seconds to wait for LibreOffice")
    args = parser.parse_args()

    src = args.input.resolve()
    if not src.is_file():
        print(f"error: {src} does not exist", file=sys.stderr)
        return 1
    outdir = (args.outdir or src.parent).resolve()
    try:
        if src.suffix.lower() == ".pdf" and args.to == "pdf":
            result = src
        else:
            result = libreoffice_convert(src, args.to, outdir, args.timeout)
            print(f"wrote {result}")
        if args.png:
            if result.suffix.lower() != ".pdf":
                print("error: --png needs a PDF; convert with --to pdf", file=sys.stderr)
                return 1
            for image in render_png(result, outdir, args.dpi, args.pages):
                print(f"wrote {image}")
    except FileNotFoundError as exc:
        print(f"unavailable: {exc}", file=sys.stderr)
        return 2
    except (RuntimeError, subprocess.SubprocessError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
