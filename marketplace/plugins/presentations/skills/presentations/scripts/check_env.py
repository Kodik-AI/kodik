#!/usr/bin/env python3
"""Report whether the tools for office-document work are available.

Usage:
    python check_env.py docx|xlsx|pptx|pdf [--json]

Checks the running Python, the Python packages the chosen format needs
(required and optional), and LibreOffice (optional, used for conversion and
rendering). Installs nothing. Exit code 0 means every required package is
importable, 1 means something required is missing.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import platform
import shutil
import sys
from pathlib import Path

# (pip name, import name, required, what it is for)
PROFILES = {
    "docx": [
        ("python-docx", "docx", True, "read, create and edit .docx"),
        ("pypdfium2", "pypdfium2", False, "render PDF pages to PNG for visual checks"),
    ],
    "xlsx": [
        ("openpyxl", "openpyxl", True, "read, create and edit .xlsx with formulas and styles"),
        ("pandas", "pandas", False, "tabular analysis, CSV and quick reads"),
        ("pypdfium2", "pypdfium2", False, "render PDF pages to PNG for visual checks"),
    ],
    "pptx": [
        ("python-pptx", "pptx", True, "read, create and edit .pptx"),
        ("pypdfium2", "pypdfium2", False, "render PDF pages to PNG for visual checks"),
    ],
    "pdf": [
        ("pypdf", "pypdf", True, "merge, split, rotate, forms, basic text"),
        ("pdfplumber", "pdfplumber", False, "layout-aware text and table extraction"),
        ("reportlab", "reportlab", False, "create new PDFs from scratch"),
        ("pypdfium2", "pypdfium2", False, "render PDF pages to PNG for visual checks"),
    ],
}

MIN_PYTHON = (3, 9)


def find_soffice() -> str | None:
    """Return the path of the LibreOffice binary, or None when it is not installed."""
    override = os.environ.get("SOFFICE_PATH")
    if override and Path(override).is_file():
        return override
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    candidates = []
    if sys.platform == "darwin":
        candidates.append("/Applications/LibreOffice.app/Contents/MacOS/soffice")
    elif os.name == "nt":
        for env in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
            base = os.environ.get(env)
            if base:
                candidates.append(os.path.join(base, "LibreOffice", "program", "soffice.exe"))
    else:
        candidates += ["/usr/bin/soffice", "/usr/lib/libreoffice/program/soffice",
                       "/opt/libreoffice/program/soffice", "/snap/bin/libreoffice"]
    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate
    return None


def check_package(import_name: str) -> tuple[bool, str]:
    try:
        module = importlib.import_module(import_name)
    except Exception as exc:  # ImportError or a broken install
        return False, type(exc).__name__
    version = getattr(module, "__version__", None)
    if version is None:
        try:
            from importlib.metadata import version as dist_version
            version = dist_version({"docx": "python-docx", "pptx": "python-pptx"}.get(import_name, import_name))
        except Exception:
            version = "unknown"
    return True, str(version)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("format", choices=sorted(PROFILES))
    parser.add_argument("--json", action="store_true", help="print a JSON report")
    args = parser.parse_args()

    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    report = {
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
            "in_virtualenv": in_venv,
            "ok": sys.version_info >= MIN_PYTHON,
        },
        "packages": [],
        "libreoffice": find_soffice(),
        "platform": platform.system(),
    }
    missing_required, missing_optional = [], []
    for pip_name, import_name, required, purpose in PROFILES[args.format]:
        ok, detail = check_package(import_name)
        report["packages"].append({"pip": pip_name, "import": import_name, "required": required,
                                   "ok": ok, "version": detail if ok else None, "purpose": purpose})
        if not ok:
            (missing_required if required else missing_optional).append(pip_name)
    report["missing_required"] = missing_required
    report["missing_optional"] = missing_optional

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        py = report["python"]
        print(f"Python {py['version']} at {py['executable']}"
              f"{' (virtualenv)' if in_venv else ''}{'' if py['ok'] else '  TOO OLD, need 3.9+'}")
        for pkg in report["packages"]:
            tag = "required" if pkg["required"] else "optional"
            state = f"ok {pkg['version']}" if pkg["ok"] else "MISSING"
            print(f"  {pkg['pip']:<12} {tag:<8} {state:<16} {pkg['purpose']}")
        if report["libreoffice"]:
            print(f"LibreOffice: {report['libreoffice']}")
        else:
            print("LibreOffice: not found (optional; conversion and rendering to PDF/PNG are unavailable)")
        wanted = missing_required + missing_optional
        if wanted:
            print("\nTo install (ask the user first), inside a project-local virtual environment:")
            if os.name == "nt":
                print("  python -m venv .venv && .venv\\Scripts\\python -m pip install " + " ".join(wanted))
            else:
                print("  python3 -m venv .venv && .venv/bin/python -m pip install " + " ".join(wanted))
            print("  or with uv:  uv venv .venv && uv pip install --python .venv " + " ".join(wanted))
    return 0 if not missing_required and report["python"]["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
