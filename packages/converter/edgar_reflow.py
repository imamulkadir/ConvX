"""Deterministic, independently reproducible reflow of vertical marginal text.

The source words are preserved at their original font size in a vacant footer
band. Both renderer and browser/audit verifier derive this plan from source PDF
bytes. No arbitrary displacement exemption or screenshot text is used.
"""

import hashlib
import re

import pymupdf

from converter.edgar_symbols import source_words
from converter.errors import fail


def axis(direction):
    # Native PDF rotation matrices can contain cos(90deg) rounding residue.
    if abs(direction[0] - 1) < 1e-7 and abs(direction[1]) < 1e-7:
        return "horizontal"
    if abs(direction[0]) < 1e-7 and abs(direction[1] + 1) < 1e-7:
        return "vertical"
    return None


def source_word_ledger(page):
    """Use native horizontal words and complete raw vertical glyph sequences.

    Native get_text(words) can return individual fragments for clipped vertical
    text. The raw character ledger retains its complete, independently verified
    Unicode content and whitespace, which is the reflow authority.
    """
    flags = pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_IMAGES & ~pymupdf.TEXT_MEDIABOX_CLIP
    raw = page.get_text("rawdict", flags=flags, clip=pymupdf.INFINITE_RECT(), sort=False)
    lines = [
        (b["number"], n, line)
        for b in raw["blocks"]
        if b["type"] == 0
        for n, line in enumerate(b["lines"])
        if axis(line["dir"]) == "vertical"
    ]
    vertical_blocks = {b for b, _, _ in lines}
    if any(
        any(axis(line["dir"]) != "vertical" for line in b["lines"])
        for b in raw["blocks"]
        if b["type"] == 0 and b["number"] in vertical_blocks
    ):
        raise ValueError("Mixed-orientation native block requires explicit association")
    words = [w for w in source_words(page) if w[5] not in vertical_blocks]
    for block, index, line in lines:
        chars = [c for s in line["spans"] for c in s["chars"]]
        text = "".join(c["c"] for c in chars)
        if any(len(c["c"]) != 1 for c in chars):
            raise ValueError("Ambiguous vertical glyph sequence")
        for ordinal, match in enumerate(re.finditer(r"\S+", text)):
            box = pymupdf.Rect(chars[match.start()]["bbox"])
            for c in chars[match.start() + 1 : match.end()]:
                box |= pymupdf.Rect(c["bbox"])
            words.append((*tuple(box), match[0], block, index, ordinal))
    return words


def vertical_plan(page):
    flags = pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_IMAGES & ~pymupdf.TEXT_MEDIABOX_CLIP
    raw = page.get_text("rawdict", flags=flags, clip=pymupdf.INFINITE_RECT(), sort=False)
    vertical, horizontal = [], []
    for block in raw["blocks"]:
        if block["type"] != 0:
            continue
        for index, line in enumerate(block["lines"]):
            if axis(line["dir"]) == "horizontal":
                horizontal.append(line)
            elif axis(line["dir"]) == "vertical":
                vertical.append((block["number"], index, line))
            else:
                raise fail(
                    "EDGAR_TEXT_ROTATION_UNSUPPORTED",
                    "generating_htm",
                    "This text angle has no supported reflow plan",
                    "Use an unrotated source",
                    page=page.number + 1,
                )
    if not vertical:
        return {"chunks": [], "words": []}
    words = source_word_ledger(page)
    left = min(line["bbox"][0] for line in horizontal)
    right = max(line["bbox"][2] for line in horizontal)
    occupied = [(line["bbox"][1], line["bbox"][3]) for line in horizontal]
    occupied += [(i["bbox"][1], i["bbox"][3]) for i in page.get_image_info()]
    occupied += [
        (v["rect"].y0, v["rect"].y1)
        for v in page.get_drawings()
        if v["rect"].x1 >= left and v["rect"].x0 <= right and v.get("fill") != (1.0, 1.0, 1.0)
    ]
    required = 0
    for block, index, line in vertical:
        selected = [w for w in words if w[5] == block and w[6] == index]
        size = max(s["bbox"][2] - s["bbox"][0] for s in line["spans"])
        start = None
        for word in selected:
            if start is None or start - word[1] > right - left:
                required += size + 1
                start = word[3]
    # Promote marginal notes to a header when the complete page can be shifted
    # without cropping any source paint. This is geometry-derived, not wording-
    # or issuer-specific. The verifier derives the same horizontal word targets.
    first_top = min(start for start, _ in occupied)
    spare = page.rect.height - 2 - max(end for _, end in occupied)
    header_top = min(first_top, first_top + spare - required - 4)
    header_top = max(2, header_top)
    shift = max(0, header_top + required + 4 - first_top)
    header = max(end for _, end in occupied) + shift <= page.rect.height - 2
    footer = (max(end for _, end in occupied) + 4, page.rect.height - 2)
    if header:
        bands = [(header_top, header_top + required)]
    elif footer[1] - footer[0] >= required:
        bands = [footer]
    else:
        bands = []
        end = 0
        for top, bottom in sorted(occupied):
            if top - end > 2:
                bands.append((end + 1, top - 1))
            end = max(end, bottom)
        if page.rect.height - end > 2:
            bands.append((end + 1, page.rect.height - 1))
    band = 0
    cursor = bands[0][0] if bands else page.rect.height
    chunks, targets = [], []
    for block, index, line in vertical:
        selected = [(i, w) for i, w in enumerate(words) if w[5] == block and w[6] == index]
        if not selected:
            raise ValueError("Vertical disclosure lacks independently extracted words")
        size = max(s["bbox"][2] - s["bbox"][0] for s in line["spans"])
        origin_x = line["spans"][0]["origin"][0]
        position = 0
        while position < len(selected):
            first = position
            start = selected[first][1][3]
            while position + 1 < len(selected) and start - selected[position + 1][1][1] <= right - left:
                position += 1
            last = position
            while band < len(bands) and cursor + size > bands[band][1]:
                band += 1
                if band < len(bands):
                    cursor = bands[band][0]
            if band >= len(bands):
                raise fail(
                    "EDGAR_REFLOW_SPACE_UNAVAILABLE",
                    "generating_htm",
                    "Vertical text cannot fit in vacant source-derived page bands",
                    "Use a source with room for selectable reflow",
                    page=page.number + 1,
                )
            baseline = cursor + origin_x - line["bbox"][0]
            chunk = {
                "block": block,
                "line": index,
                "source_y": start,
                "source_x": origin_x,
                "left": left,
                "baseline": baseline,
                "top": cursor,
                "height": size,
                "next_y": selected[last + 1][1][3] if last + 1 < len(selected) else None,
            }
            chunks.append(chunk)
            for ordinal, word in selected[first : last + 1]:
                targets.append(
                    {
                        "index": ordinal,
                        "text_sha256": hashlib.sha256(word[4].encode()).hexdigest(),
                        "source_bbox": list(word[:4]),
                        "target_origin": [left + start - word[3], baseline + word[0] - origin_x],
                    }
                )
            cursor += size + 1
            position += 1
    if header and shift:
        vertical_blocks = {block for block, _, _ in vertical}
        for ordinal, word in enumerate(words):
            if word[5] not in vertical_blocks:
                targets.append(
                    {
                        "index": ordinal,
                        "text_sha256": hashlib.sha256(word[4].encode()).hexdigest(),
                        "source_bbox": list(word[:4]),
                        "target_origin": [word[0], word[1] + shift],
                    }
                )
    return {
        "chunks": chunks,
        "words": targets,
        "content_offset_y": shift if header else 0,
        "placement": "header" if header else "vacant_band",
    }
