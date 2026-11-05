from __future__ import annotations

import re
from collections import Counter

from converter.layout.models import ReadingOrder, RegionCandidate
from converter.pdf_analysis.geometry import overlaps


def reading_order(blocks, policy):
    def gap(items, axis, minimum):
        intervals = sorted((b.bbox[axis], b.bbox[axis + 2]) for b in items)
        candidates = []
        if not intervals:
            return None
        end = intervals[0][1]
        for lo, hi in intervals[1:]:
            if lo - end >= minimum:
                candidates.append((lo - end, (lo + end) / 2))
            end = max(end, hi)
        return max(candidates, key=lambda item: (item[0], -item[1]))[1] if candidates else None

    def arrange(items, depth=0):
        if len(items) < 2:
            return items
        if depth > 64:
            return sorted(items, key=lambda b: (b.bbox[1], b.bbox[0], b.id))
        for axis, minimum in ((0, policy.column_gap_pt), (1, policy.horizontal_gap_pt)):
            cut = gap(items, axis, minimum)
            if cut is not None:
                before = [b for b in items if b.bbox[axis + 2] <= cut]
                after = [b for b in items if b.bbox[axis] >= cut]
                if before and after and len(before) + len(after) == len(items):
                    return arrange(before, depth + 1) + arrange(after, depth + 1)
        return sorted(items, key=lambda b: (b.bbox[1], b.bbox[0], b.id))

    candidate = tuple(b.id for b in arrange(list(blocks)))
    lines = [line for block in blocks for line in block.lines]
    candidate_lines = tuple(line.id for line in arrange(lines))
    # Block boxes can overlap even when individual glyphs do not. This is uncertainty, not deletion.
    ordered_by_x = sorted(blocks, key=lambda b: b.bbox[0])
    ambiguous = False
    for i, a in enumerate(ordered_by_x):
        for b in ordered_by_x[i + 1 :]:
            if b.bbox[0] >= a.bbox[2]:
                break
            if overlaps(a.bbox, b.bbox):
                ambiguous = True
                break
        if ambiguous:
            break
    return ReadingOrder(
        native_block_ids=tuple(b.id for b in blocks),
        candidate_block_ids=candidate,
        edges=tuple(zip(candidate, candidate[1:], strict=False)),
        native_line_ids=tuple(line.id for line in lines),
        candidate_line_ids=candidate_lines,
        line_edges=tuple(zip(candidate_lines, candidate_lines[1:], strict=False)),
        confidence=0.35 if ambiguous else 0.7,
        ambiguous=ambiguous,
    )


def margin_regions(pages):
    candidates, occurrences = [], Counter()
    number_pattern = re.compile(r"^(?:(?:page\s*)?\d+(?:\s+of\s+\d+)?|[a-z]{1,4}[-–]\d+)$", re.I)
    for page in pages:
        height = page.geometry.unrotated_bounds[3]
        per_page = set()
        for block in page.text_blocks:
            area = (
                "header"
                if block.bbox[3] <= height * 0.12
                else "footer"
                if block.bbox[1] >= height * 0.88
                else None
            )
            if not area:
                continue
            text = " ".join("".join(s.text for s in line.spans) for line in block.lines).strip()
            normalized = re.sub(r"\d+", "#", re.sub(r"\s+", " ", text.casefold()))
            candidates.append(
                (page.page_number, block, area, normalized, bool(number_pattern.fullmatch(text)))
            )
            per_page.add((area, normalized))
        occurrences.update(per_page)
    result = {p.page_number: [] for p in pages}
    for number, block, area, normalized, is_number in candidates:
        if is_number:
            result[number].append(
                RegionCandidate(
                    kind="page_number",
                    block_id=block.id,
                    bbox=block.bbox,
                    method="margin_page_number_pattern",
                    confidence=0.75,
                )
            )
        elif normalized and occurrences[(area, normalized)] >= max(2, (len(pages) + 1) // 2):
            result[number].append(
                RegionCandidate(
                    kind=area,
                    block_id=block.id,
                    bbox=block.bbox,
                    method="repeated_margin_text",
                    confidence=0.7,
                )
            )
    return result
