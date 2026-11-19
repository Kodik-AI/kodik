"""Small python-docx helpers for things the library has no API for.

Import from a script:
    import sys; sys.path.insert(0, "<this folder>")
    from docx_helpers import open_document, add_page_number_field, ...

Every helper edits the WordprocessingML directly and keeps the rest of the
document untouched.
"""
from __future__ import annotations

import copy
import io
import zipfile
from pathlib import Path

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.table import _Row
from docx.text.paragraph import Paragraph

_TEMPLATE_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml"
_MACRO_TEMPLATE_TYPE = "application/vnd.ms-word.template.macroEnabledTemplate.main+xml"
_DOCUMENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"


def open_document(path: str | Path):
    """Open a .docx, or a .dotx/.dotm template as a new document (python-docx rejects templates)."""
    path = Path(path)
    with zipfile.ZipFile(path) as archive:
        types = archive.read("[Content_Types].xml").decode("utf-8")
        if _TEMPLATE_TYPE not in types and _MACRO_TEMPLATE_TYPE not in types:
            return Document(str(path))
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as out:
            for item in archive.infolist():
                data = archive.read(item.filename)
                if item.filename == "[Content_Types].xml":
                    text = types.replace(_TEMPLATE_TYPE, _DOCUMENT_TYPE).replace(_MACRO_TEMPLATE_TYPE, _DOCUMENT_TYPE)
                    data = text.encode("utf-8")
                out.writestr(item, data)
    buffer.seek(0)
    return Document(buffer)


def _field_runs(paragraph: Paragraph, instruction: str, placeholder: str) -> None:
    """Append a complex field (begin / instrText / separate / result / end) to a paragraph."""
    def run_with(child):
        run = OxmlElement("w:r")
        run.append(child)
        paragraph._p.append(run)

    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    begin.set(qn("w:dirty"), "true")  # ask Word to refresh the result on open
    run_with(begin)
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {instruction} "
    run_with(instr)
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    run_with(separate)
    result = OxmlElement("w:t")
    result.text = placeholder
    run_with(result)
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run_with(end)


def add_page_number_field(paragraph: Paragraph, with_total: bool = False) -> None:
    """Append 'PAGE' (or 'PAGE of NUMPAGES') fields, typically to a footer paragraph."""
    _field_runs(paragraph, "PAGE", "1")
    if with_total:
        paragraph.add_run(" / ")
        _field_runs(paragraph, "NUMPAGES", "1")


def add_table_of_contents(paragraph: Paragraph, levels: str = "1-3") -> None:
    """Insert a TOC field. Word fills it on open (it may ask to update fields); LibreOffice on update."""
    _field_runs(paragraph, f'TOC \\o "{levels}" \\h \\z \\u', "Right-click and choose Update Field to build the table of contents.")


def add_hyperlink(paragraph: Paragraph, url: str, text: str, underline: bool = True, color: str = "0563C1"):
    """Append a clickable external hyperlink run to a paragraph and return the w:hyperlink element."""
    r_id = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), r_id)
    run = OxmlElement("w:r")
    props = OxmlElement("w:rPr")
    if color:
        color_el = OxmlElement("w:color")
        color_el.set(qn("w:val"), color)
        props.append(color_el)
    if underline:
        u = OxmlElement("w:u")
        u.set(qn("w:val"), "single")
        props.append(u)
    run.append(props)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    run.append(t)
    link.append(run)
    paragraph._p.append(link)
    return link


def set_cell_background(cell, hex_color: str) -> None:
    """Fill a table cell, e.g. set_cell_background(cell, 'D9E2F3')."""
    tc_pr = cell._tc.get_or_add_tcPr()
    for old in tc_pr.findall(qn("w:shd")):
        tc_pr.remove(old)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    # The schema fixes the order of tcPr children; Word rejects a w:shd placed after these.
    later = {qn(f"w:{name}") for name in ("noWrap", "tcMar", "textDirection", "tcFitText", "vAlign",
                                          "hideMark", "headers", "cellIns", "cellDel", "cellMerge", "tcPrChange")}
    for index, child in enumerate(tc_pr):
        if child.tag in later:
            tc_pr.insert(index, shd)
            return
    tc_pr.append(shd)


def repeat_as_header_row(row: _Row) -> None:
    """Repeat this table row at the top of every page the table spans."""
    tr_pr = row._tr.get_or_add_trPr()
    if tr_pr.find(qn("w:tblHeader")) is None:
        header = OxmlElement("w:tblHeader")
        header.set(qn("w:val"), "true")
        tr_pr.append(header)


def insert_paragraph_after(paragraph: Paragraph, text: str = "", style: str | None = None) -> Paragraph:
    """Insert a new paragraph directly after `paragraph` (python-docx only has insert-before)."""
    new_p = OxmlElement("w:p")
    paragraph._p.addnext(new_p)
    new_paragraph = Paragraph(new_p, paragraph._parent)
    if text:
        new_paragraph.add_run(text)
    if style is not None:
        new_paragraph.style = style
    return new_paragraph


def clone_paragraph_after(paragraph: Paragraph, text: str | None = None) -> Paragraph:
    """Copy a paragraph (style, numbering, run formatting) after itself; optionally set new text
    while keeping the first run's formatting."""
    new_p = copy.deepcopy(paragraph._p)
    paragraph._p.addnext(new_p)
    clone = Paragraph(new_p, paragraph._parent)
    if text is not None:
        runs = clone.runs
        if runs:
            runs[0].text = text
            for extra in runs[1:]:
                extra._r.getparent().remove(extra._r)
        else:
            clone.add_run(text)
    return clone


def delete_paragraph(paragraph: Paragraph) -> None:
    """Remove a paragraph from the document."""
    element = paragraph._element
    element.getparent().remove(element)
