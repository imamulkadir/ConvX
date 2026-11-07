"""Source-derived paragraphs and reading order for rectangular EDGAR pages.

Physical line positions stay verified; paragraph containers express text groups
instead of exposing every PDF line as a separate paragraph. Only HTML4 inline
FONT elements appear inside P; no DIV/P nesting or duplicated hidden disclosure.
"""

import re
from types import SimpleNamespace

from lxml import etree

from converter.edgar_clips import inside
from converter.edgar_reflow import axis
from converter.pdf_analysis.geometry import overlaps, union
from converter.pdf_analysis.ordering import reading_order
from converter.pdf_analysis.policy import AnalysisPolicy


def aligned_fields(page, context):
    """Conservative borderless label/value rows, never nested around a grid.

    Require at least three aligned colon-ended labels, paired source values,
    a clear column gap and complete character ownership. Ambiguity leaves the
    source as ordinary paragraphs; it does not invent a financial table.
    """
    lines = sorted(
        (line for b in page.text_blocks for line in b.lines if axis(line.direction) == "horizontal"),
        key=lambda line: (line.bbox[1], line.bbox[0]),
    )
    native = [t.bbox for t in page.tables]
    if len(lines) > 2000 or len(native) > 1000:
        return []
    usable = [line for line in lines if not any(overlaps(line.bbox, box) for box in native)]
    labels = []
    work = 0
    for line in usable:
        context.check()
        text = "".join(s.text for s in line.spans).strip()
        if not re.fullmatch(r"[^:]{1,70}:\*?", text):
            continue
        size = max(s.font_size_pt for s in line.spans)
        parts = [line]
        # Recover a wrapped label from its preceding aligned source line.
        previous = [
            p
            for p in usable
            if abs(p.bbox[0] - line.bbox[0]) < 1
            and 0 < line.bbox[1] - p.bbox[1] < size * 1.6
            and p.bbox[2] < line.bbox[0] + 110
            and not "".join(s.text for s in p.spans).strip().endswith((":", ":*"))
        ]
        if previous:
            parts.insert(0, max(previous, key=lambda p: p.bbox[1]))
        box = union([p.bbox for p in parts])
        work += len(usable) * 2
        if work > 2_000_000:
            return []
        values = [
            p for p in usable if abs(p.bbox[1] - box[1]) < 1 and p.bbox[0] > max(box[2] + 4, box[0] + 50)
        ]
        if len(values) != 1:
            continue
        labels.append((parts, values[0]))
    groups = []
    for item in labels:
        left, value = item
        if groups:
            prev_left, prev_value = groups[-1][-1]
            between = (
                left[0].bbox[0],
                prev_value.bbox[3],
                page.geometry.unrotated_bounds[2],
                left[0].bbox[1],
            )
            join = (
                abs(left[0].bbox[0] - prev_left[0].bbox[0]) < 1
                and abs(value.bbox[0] - prev_value.bbox[0]) < 1
                and not any(overlaps(between, box) for box in native)
            )
        else:
            join = False
        if not join:
            groups.append([])
        groups[-1].append(item)
    result = []
    for group in groups:
        if len(group) < 3:
            continue
        rows = []
        used = set()
        for index, (label, first) in enumerate(group):
            stop = (
                group[index + 1][0][0].bbox[1]
                if index + 1 < len(group)
                else page.geometry.unrotated_bounds[3]
            )
            values = [first]
            for candidate in usable:
                if candidate.bbox[1] <= first.bbox[1] or candidate.bbox[1] >= stop - 1:
                    continue
                if (
                    abs(candidate.bbox[0] - first.bbox[0]) < 1
                    and 0
                    < candidate.bbox[1] - values[-1].bbox[1]
                    < max(s.font_size_pt for s in candidate.spans) * 1.65
                ):
                    if any(overlaps(union([first.bbox, candidate.bbox]), box) for box in native):
                        break
                    values.append(candidate)
            ids = [c.id for part in label + values for s in part.spans for c in s.characters]
            if used.intersection(ids):
                rows = []
                break
            used.update(ids)
            rows.append((label, values))
        if not rows:
            continue
        box = union([part.bbox for row in rows for cell in row for part in cell])
        # Unassigned source text inside the inferred table is ambiguous.
        enclosed = {
            c.id for line in usable if overlaps(line.bbox, box) for s in line.spans for c in s.characters
        }
        if enclosed != used or any(overlaps(box, b) for b in native):
            continue
        edges = [row[0][0].bbox[1] for row in rows] + [box[3]]
        split = min(row[1][0].bbox[0] for row in rows)
        cells = []
        for index, row in enumerate(rows):
            for column, parts in enumerate(row):
                cells.append(
                    SimpleNamespace(
                        row=index,
                        column=column,
                        row_span=1,
                        column_span=1,
                        bbox=(
                            box[0] if column == 0 else split,
                            edges[index],
                            split if column == 0 else box[2],
                            edges[index + 1],
                        ),
                        character_ids=tuple(c.id for part in parts for s in part.spans for c in s.characters),
                    )
                )
        result.append(SimpleNamespace(bbox=box, rows=len(rows), columns=2, cells=cells))
    return result


class Paragraphs:
    def __init__(self):
        self.last = {}
        self.order = {}

    def container(self, target, block, line, clip, owner, selected, width, slots):
        chars = [c for s in line.spans for c in s.characters if c.id in selected]
        left = min(c.bbox[0] for c in chars)
        top = min(c.bbox[1] for c in chars)
        right = max(c.bbox[2] for c in chars)
        bottom = max(c.bbox[3] for c in chars)
        size = max(s.font_size_pt for s in line.spans)
        parent, dx, dy = owner if owner else (target, 0, 0)
        key = (parent, block.id)
        previous = self.last.get(key)
        adjacent = previous is not None and (
            (0.25 < top - previous[1] <= size * 1.65 and abs(left - previous[2]) < 2)
            or (abs(top - previous[1]) <= 0.25 and 0 <= left - previous[3] <= size * 3)
        )
        if adjacent:
            paragraph = previous[0]
            self.order[paragraph] = union([self.order[paragraph], (left, top, right, bottom)])
        else:
            paragraph = etree.SubElement(
                parent, "p", style="margin:0;padding:0;height:0;font-size:0;line-height:0"
            )
            self.order[paragraph] = (left, top, right, bottom)
        self.last[key] = (paragraph, top, left, right)
        if inside(clip, (left, top, right, bottom)):
            outer = etree.SubElement(
                paragraph, "font", style="display:block;height:0;font-size:0;line-height:0"
            )
            return outer, (dx, dy), (top - dy), True
        shifted = (clip[0] - dx, clip[1] - dy, clip[2] - dx, clip[3] - dy)
        return slots(paragraph, width, shifted, tag="font"), clip[:2], top - clip[1], False

    def sort(self, parent):
        # Decorative paint remains before content. Source tables and paragraphs
        # then share one spatial ordering rather than table-first emission.
        children = list(parent)
        content = [e for e in children if e in self.order]
        if len(content) <= 2000:
            items = [SimpleNamespace(id=str(i), bbox=self.order[e], lines=()) for i, e in enumerate(content)]
            order = reading_order(items, AnalysisPolicy()).candidate_block_ids
            ordered = [content[int(i)] for i in order]
        else:
            ordered = sorted(content, key=lambda e: (self.order[e][1], self.order[e][0]))
        for element in ordered:
            parent.remove(element)
            parent.append(element)
