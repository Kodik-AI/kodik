"""python-pptx helpers for operations the library has no API for.

Import from a script:
    import sys; sys.path.insert(0, "<this folder>")
    from pptx_helpers import set_widescreen, delete_slide, duplicate_slide, ...
"""
from __future__ import annotations

import copy

from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.oxml.ns import qn
from pptx.shapes.group import GroupShape
from pptx.util import Emu, Inches

TITLE_TYPES = (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE, PP_PLACEHOLDER.VERTICAL_TITLE)
BODY_TYPES = (PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT, PP_PLACEHOLDER.VERTICAL_BODY,
              PP_PLACEHOLDER.VERTICAL_OBJECT)
FOOTER_TYPES = (PP_PLACEHOLDER.DATE, PP_PLACEHOLDER.FOOTER, PP_PLACEHOLDER.SLIDE_NUMBER)


def set_widescreen(prs, width=Inches(13.333), height=Inches(7.5)) -> None:
    """Resize the slides (default 16:9) and stretch the master and layout shapes to match.

    Setting prs.slide_width alone leaves the template's placeholders where they
    were, crowded on the left. Use this on a new deck from the default template.
    """
    sx, sy = width / prs.slide_width, height / prs.slide_height
    containers = [prs.slide_master, *prs.slide_layouts, *prs.slides]
    for container in containers:
        for shape in container.shapes:
            # A placeholder without its own xfrm inherits the (already scaled) position.
            own = shape._element.xpath("./p:spPr/a:xfrm | ./p:grpSpPr/a:xfrm | ./p:xfrm")
            if (shape.is_placeholder and not own) or shape.left is None:
                continue
            shape.left, shape.top = Emu(int(shape.left * sx)), Emu(int(shape.top * sy))
            shape.width, shape.height = Emu(int(shape.width * sx)), Emu(int(shape.height * sy))
    prs.slide_width, prs.slide_height = Emu(int(width)), Emu(int(height))


def layout_by_name(prs, name: str):
    """Find a slide layout by name (case-insensitive) across all masters."""
    for master in prs.slide_masters:
        for layout in master.slide_layouts:
            if layout.name.lower() == name.lower():
                return layout
    names = [layout.name for master in prs.slide_masters for layout in master.slide_layouts]
    raise KeyError(f"no layout {name!r}; available: {names}")


def placeholder_of(slide, types):
    """First placeholder on the slide whose type is in `types` (or None)."""
    for shape in slide.placeholders:
        if shape.placeholder_format.type in types:
            return shape
    return None


def remove_shape(shape) -> None:
    element = shape._element
    element.getparent().remove(element)


def remove_empty_placeholders(slide) -> int:
    """Delete placeholders nobody filled, which otherwise show 'Click to add text' in edit view."""
    removed = 0
    for shape in list(slide.placeholders):
        if shape.placeholder_format.type in FOOTER_TYPES:
            continue
        if shape.has_text_frame and shape.text_frame.text.strip():
            continue
        if shape._element.tag.endswith("}pic") or getattr(shape, "has_chart", False) or getattr(shape, "has_table", False):
            continue
        remove_shape(shape)
        removed += 1
    return removed


def delete_slide(prs, index: int) -> None:
    """Remove the slide at `index` and drop its part relationship."""
    slide_ids = prs.slides._sldIdLst
    slide_id = list(slide_ids)[index]
    prs.part.drop_rel(slide_id.get(qn("r:id")))
    slide_ids.remove(slide_id)


def move_slide(prs, old_index: int, new_index: int) -> None:
    slide_ids = prs.slides._sldIdLst
    item = list(slide_ids)[old_index]
    slide_ids.remove(item)
    slide_ids.insert(new_index, item)


def duplicate_slide(prs, index: int):
    """Append a copy of slide `index` (shapes, pictures, notes text) and return it.

    Charts and embedded media are shared with the original slide, not copied:
    editing the chart data of one changes both. Rebuild charts instead.
    """
    source = prs.slides[index]
    target = prs.slides.add_slide(source.slide_layout)
    for shape in list(target.shapes):
        remove_shape(shape)
    rid_map = {}
    for rel in source.part.rels.values():
        if "notesSlide" in rel.reltype or rel.reltype.endswith("/slideLayout"):
            continue
        if rel.is_external:
            new_rid = target.part.relate_to(rel.target_ref, rel.reltype, is_external=True)
        else:
            new_rid = target.part.relate_to(rel.target_part, rel.reltype)
        rid_map[rel.rId] = new_rid
    tree = target.shapes._spTree
    for element in source.shapes._spTree.iterchildren():
        if element.tag in (qn("p:nvGrpSpPr"), qn("p:grpSpPr")):
            continue
        clone = copy.deepcopy(element)
        for node in clone.iter():
            for attr in (qn("r:embed"), qn("r:link"), qn("r:id")):
                if node.get(attr) in rid_map:
                    node.set(attr, rid_map[node.get(attr)])
        tree.append(clone)
    if source.has_notes_slide:
        target.notes_slide.notes_text_frame.text = source.notes_slide.notes_text_frame.text
    return target


def _iter_text_frames(shapes):
    for shape in shapes:
        if isinstance(shape, GroupShape):
            yield from _iter_text_frames(shape.shapes)
            continue
        if shape.has_text_frame:
            yield shape.text_frame
        if getattr(shape, "has_table", False) and shape.has_table:
            for row in shape.table.rows:
                for cell in row.cells:
                    yield cell.text_frame


def _replace_in_paragraph(p, old: str, new: str) -> int:
    nodes = [t for t in p.iter(qn("a:t"))]
    texts = [t.text or "" for t in nodes]
    full = "".join(texts)
    if not old or old not in full:
        return 0
    starts, pos = [], 0
    for text in texts:
        starts.append(pos)
        pos += len(text)

    def locate(offset, is_end):
        for i, text in enumerate(texts):
            low, high = starts[i], starts[i] + len(text)
            if (low < offset <= high) if is_end else (low <= offset < high):
                return i, offset - low
        raise ValueError(offset)

    matches, at = [], 0
    while (found := full.find(old, at)) >= 0:
        matches.append(found)
        at = found + len(old)
    for start in reversed(matches):
        first, first_off = locate(start, False)
        last, last_off = locate(start + len(old), True)
        if first == last:
            texts[first] = texts[first][:first_off] + new + texts[first][last_off:]
        else:
            texts[first] = texts[first][:first_off] + new
            for middle in range(first + 1, last):
                texts[middle] = ""
            texts[last] = texts[last][last_off:]
    for node, text in zip(nodes, texts):
        node.text = text
    return len(matches)


def replace_text(prs, old: str, new: str, include_notes: bool = True) -> int:
    """Replace text on every slide (shapes, groups, tables, optionally notes), keeping run formatting.

    Text split across runs is matched; the replacement takes the formatting of
    the run where the match starts. Returns the number of replacements.
    """
    count = 0
    for slide in prs.slides:
        frames = list(_iter_text_frames(slide.shapes))
        if include_notes and slide.has_notes_slide:
            frames.append(slide.notes_slide.notes_text_frame)
        for frame in frames:
            for paragraph in frame.paragraphs:
                count += _replace_in_paragraph(paragraph._p, old, new)
    return count


def add_picture_fit(slide, image_path: str, left, top, width, height):
    """Add a picture scaled to fit inside the box, keeping its aspect ratio, centered."""
    picture = slide.shapes.add_picture(image_path, left, top)
    ratio = min(width / picture.width, height / picture.height)
    picture.width, picture.height = Emu(int(picture.width * ratio)), Emu(int(picture.height * ratio))
    picture.left = Emu(int(left + (width - picture.width) / 2))
    picture.top = Emu(int(top + (height - picture.height) / 2))
    return picture
