#!/usr/bin/env python3
"""List and fill the interactive form fields (AcroForm) of a PDF.

Usage:
    python pdf_form.py list FORM.pdf [--json]            # names, types, current values, allowed values
    python pdf_form.py template FORM.pdf > values.json   # a JSON skeleton to fill in
    python pdf_form.py fill FORM.pdf OUT.pdf values.json [--flatten]

values.json maps field names to values: text as strings, check boxes as
true/false (or the exact state name such as "/Yes"), radio groups and choice
lists as one of the allowed values that `list` prints. --flatten bakes the
values into the page so they can no longer be edited (Latin text only).
A PDF without fields is not a fillable form: write text onto it instead (see
the overlay recipe in SKILL.md).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, IndirectObject, NameObject, StreamObject

TYPES = {"/Tx": "text", "/Btn": "button", "/Ch": "choice", "/Sig": "signature"}


def field_pages(reader: PdfReader) -> dict[str, int]:
    pages: dict[str, int] = {}
    for number, page in enumerate(reader.pages, start=1):
        for annot in page.get("/Annots") or []:
            annot = annot.get_object()
            if annot.get("/Subtype") != "/Widget":
                continue
            node, parts = annot, []
            while node is not None:
                if "/T" in node:
                    parts.append(str(node["/T"]))
                node = node.get("/Parent")
                node = node.get_object() if node is not None else None
            if parts:
                pages.setdefault(".".join(reversed(parts)), number)
    return pages


def describe(reader: PdfReader) -> list[dict]:
    fields = reader.get_fields() or {}
    pages = field_pages(reader)
    out = []
    for name, field in fields.items():
        kind = TYPES.get(field.get("/FT"), "unknown")
        if kind == "unknown" and "/Kids" in field:
            continue  # a pure container of other fields
        entry = {"name": name, "type": kind, "value": _plain(field.get("/V")), "page": pages.get(name)}
        flags = int(field.get("/Ff", 0))
        if kind == "button":
            states = [s for s in field.get("/_States_", []) if s != "/Off"]
            entry["type"] = "radio" if flags & (1 << 15) else ("pushbutton" if flags & (1 << 16) else "checkbox")
            entry["options"] = states
        elif kind == "choice":
            entry["options"] = [_plain(o) for o in field.get("/Opt", [])]
            entry["type"] = "combo" if flags & (1 << 17) else "list"
        if field.get("/TU"):
            entry["tooltip"] = str(field["/TU"])
        if flags & 1:
            entry["read_only"] = True
        if flags & 2:
            entry["required"] = True
        out.append(entry)
    return out


def _plain(value):
    if value is None:
        return None
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return str(value)


def _latin1(text: str) -> bool:
    try:
        str(text).encode("latin-1")
        return True
    except UnicodeEncodeError:
        return False


def _num(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")


def flatten_widgets(writer: PdfWriter) -> None:
    """Paint every visible widget's current appearance into its page, then drop the form."""
    for page in writer.pages:
        annots = page.get("/Annots")
        if not annots:
            continue
        resources = page.get("/Resources")
        resources = resources.get_object() if resources is not None else DictionaryObject()
        xobjects = resources.get("/XObject")
        xobjects = xobjects.get_object() if xobjects is not None else DictionaryObject()
        kept, ops = ArrayObject(), []
        for ref in annots.get_object():
            annot = ref.get_object()
            if annot.get("/Subtype") != "/Widget":
                kept.append(ref)
                continue
            if int(annot.get("/F", 0)) & (2 | 32):  # hidden / no-view
                continue
            normal = annot.get("/AP", {}).get("/N") if annot.get("/AP") else None
            if normal is None:
                continue
            normal_ref = annot["/AP"].raw_get("/N")
            normal = normal.get_object()
            if not isinstance(normal, StreamObject):  # check box / radio: one stream per state
                state = annot.get("/AS")
                if state is None or state not in normal:
                    continue
                normal_ref, normal = normal.raw_get(state), normal[state].get_object()
            if not isinstance(normal_ref, IndirectObject):
                normal_ref = writer._add_object(normal)
            x1, y1, x2, y2 = (float(v) for v in annot["/Rect"])
            x1, x2, y1, y2 = min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)
            bx1, by1, bx2, by2 = (float(v) for v in normal.get("/BBox", [0, 0, x2 - x1, y2 - y1]))
            a, b, c, d, e, f = (float(v) for v in normal.get("/Matrix", [1, 0, 0, 1, 0, 0]))
            corners = [(a * x + c * y + e, b * x + d * y + f) for x in (bx1, bx2) for y in (by1, by2)]
            min_x, max_x = min(p[0] for p in corners), max(p[0] for p in corners)
            min_y, max_y = min(p[1] for p in corners), max(p[1] for p in corners)
            sx = (x2 - x1) / (max_x - min_x) if max_x > min_x else 1.0
            sy = (y2 - y1) / (max_y - min_y) if max_y > min_y else 1.0
            name = f"/KFlat{len(xobjects)}"
            xobjects[NameObject(name)] = normal_ref
            ops.append(f"q {_num(sx)} 0 0 {_num(sy)} {_num(x1 - min_x * sx)} {_num(y1 - min_y * sy)} cm {name} Do Q")
        if ops:
            resources[NameObject("/XObject")] = xobjects
            page[NameObject("/Resources")] = resources
            content = page.get_contents()
            original = content.get_data() if content is not None else b""
            stream = DecodedStreamObject()
            stream.set_data(b"q\n" + original + b"\nQ\n" + "\n".join(ops).encode("ascii") + b"\n")
            page.replace_contents(stream)
        page[NameObject("/Annots")] = kept
    if "/AcroForm" in writer._root_object:
        del writer._root_object[NameObject("/AcroForm")]


def fill(src: Path, dst: Path, values: dict, flatten: bool) -> list[str]:
    reader = PdfReader(str(src))
    if "/AcroForm" in reader.trailer["/Root"] and "/XFA" in reader.trailer["/Root"]["/AcroForm"]:
        print("warning: this form also has XFA data; viewers that prefer XFA may ignore the filled values",
              file=sys.stderr)
    known = {f["name"]: f for f in describe(reader)}
    unknown = [name for name in values if name not in known]
    if unknown:
        raise KeyError(f"unknown fields: {unknown}; run 'list' for the exact names")
    resolved = {}
    for name, value in values.items():
        field = known[name]
        if field["type"] in ("checkbox", "radio"):
            on_states = field.get("options") or ["/Yes"]
            if value is True:
                value = on_states[0]
            elif value in (False, None, ""):
                value = "/Off"
            else:
                value = value if str(value).startswith("/") else "/" + str(value)
                if value not in on_states + ["/Off"]:
                    raise ValueError(f"{name}: {value} is not one of {on_states + ['/Off']}")
        elif field["type"] in ("combo", "list") and field.get("options"):
            allowed = [o[-1] if isinstance(o, list) else o for o in field["options"]]
            if str(value) not in allowed and field["type"] == "list":
                raise ValueError(f"{name}: {value!r} is not one of {allowed}")
        else:
            value = "" if value is None else str(value)
        resolved[name] = value
    if flatten:
        non_latin = [n for n, v in resolved.items() if known[n]["type"] == "text" and not _latin1(v)]
        if non_latin:
            raise ValueError(f"cannot flatten non-Latin text in {non_latin}: the form's font has no such "
                             "glyphs. Fill without --flatten, or write the text with the overlay recipe.")
    writer = PdfWriter(clone_from=reader)
    for page in writer.pages:
        if page.get("/Annots"):
            writer.update_page_form_field_values(page, resolved, auto_regenerate=False)
    if flatten:
        flatten_widgets(writer)
    else:
        writer.set_need_appearances_writer(True)  # let viewers redraw fields with the new values
    with open(dst, "wb") as handle:
        writer.write(handle)
    return sorted(resolved)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("list"); p.add_argument("file", type=Path); p.add_argument("--json", action="store_true")
    p = sub.add_parser("template"); p.add_argument("file", type=Path)
    p = sub.add_parser("fill"); p.add_argument("file", type=Path); p.add_argument("output", type=Path)
    p.add_argument("values", type=Path); p.add_argument("--flatten", action="store_true")
    args = parser.parse_args()

    if args.command in ("list", "template"):
        fields = describe(PdfReader(str(args.file)))
        if args.command == "template":
            skeleton = {f["name"]: (False if f["type"] == "checkbox" else (f["options"][0] if f.get("options") else ""))
                        for f in fields if f["type"] not in ("pushbutton", "signature") and not f.get("read_only")}
            print(json.dumps(skeleton, indent=2, ensure_ascii=False))
        elif args.json:
            print(json.dumps(fields, indent=2, ensure_ascii=False))
        elif not fields:
            print("no form fields: this PDF is not a fillable form")
        else:
            for f in fields:
                extra = f" options={f['options']}" if f.get("options") else ""
                flags = "".join(f" {k}" for k in ("required", "read_only") if f.get(k))
                print(f"p{f['page']} {f['type']:<10} {f['name']!r} = {f['value']!r}{extra}{flags}"
                      + (f"  ({f['tooltip']})" if f.get("tooltip") else ""))
        return 0
    if args.output.resolve() == args.file.resolve():
        parser.error("write to a new file, not over the input")
    values = json.loads(args.values.read_text(encoding="utf-8"))
    try:
        names = fill(args.file, args.output, values, args.flatten)
    except (KeyError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"filled {len(names)} field(s), wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
