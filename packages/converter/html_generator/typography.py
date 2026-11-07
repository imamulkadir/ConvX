from __future__ import annotations

import re
from itertools import groupby

from lxml import etree

from converter.html_generator.flow import pt
from converter.pdf_analysis.geometry import center, contains


def font_family(name):
    name = re.sub(r"^[A-Z]{6}\+", "", name)
    aliases = (
        (r"^(Times(?:NewRomanPS)?|TimesNewRoman)", "Times New Roman"),
        (r"^(Helvetica|Arial)", "Arial"),
        (r"^(Courier|CourierNew)", "Courier New"),
    )
    for pattern, replacement in aliases:
        if re.match(pattern, name):
            return replacement
    name = re.sub(r"[-,](?:Bold|Italic|Oblique|Regular|Roman).*$", "", name)
    # Font names become CSS tokens only after a narrow grammar check.
    return name if re.fullmatch(r"[A-Za-z][A-Za-z0-9 -]{0,95}", name) else None


def render_line(line, parent, emitted, hrefs, anchors, selected=None, offset=(0, 0), run_records=None):
    spans = [s for s in line.spans if selected is None or any(c.id in selected for c in s.characters)]
    if not spans:
        return
    characters = [(s, c) for s in spans for c in s.characters if selected is None or c.id in selected]
    left = min(c.origin[0] for _, c in characters)
    top = min(c.bbox[1] for _, c in characters)
    height = max(c.bbox[3] for _, c in characters) - top
    p = etree.SubElement(
        parent,
        "p",
        style=f"margin:0 0 0 {pt(left - offset[0])};padding:{pt(top - offset[1])} 0 0 0;white-space:pre;line-height:{pt(height)};font-size:{pt(max(s.font_size_pt for s in spans))}",
    )
    for anchor in anchors.pop(line.id, ()):
        etree.SubElement(p, "a", name=anchor)
    baseline = max(s.origin[1] for s in spans)
    previous_end = left

    def key(pair):
        span, char = pair
        return (
            font_family(span.font_name),
            span.font_size_pt,
            span.color_rgb,
            span.origin[1],
            span.bold_hint,
            span.italic_hint,
            span.underline_hint,
            span.script_hint,
            hrefs.get(char.id),
        )

    runs = [list(group) for _, group in groupby(characters, key=key)]
    for index, run in enumerate(runs):
        span, char = run[0]
        target = p
        if char.id in hrefs:
            target = etree.SubElement(
                target, "a", href=hrefs[char.id], style="color:inherit;text-decoration:none"
            )
        style = f"font-family:'{font_family(span.font_name)}';font-size:{pt(span.font_size_pt)};line-height:1;color:#{span.color_rgb:06x};vertical-align:{pt(baseline - span.origin[1])}"
        # Shared formatting runs avoid the SEC-prohibited per-word formatting pattern.
        # Browser glyph shaping inside each run must be measured in Stage 7.
        following = runs[index + 1][0][1].origin[0] if index + 1 < len(runs) else run[-1][1].bbox[2]
        advance = following - char.origin[0]
        style += f";display:inline-block;width:{pt(max(0, advance))};margin-left:{pt(char.origin[0] - previous_end)}"
        target = etree.SubElement(target, "font", style=style)
        if run_records is not None:
            run_records.append((target, span, tuple(c for _, c in run)))
        if span.bold_hint:
            target = etree.SubElement(target, "b")
        if span.italic_hint:
            target = etree.SubElement(target, "i")
        if span.underline_hint:
            target = etree.SubElement(target, "u")
        if span.script_hint != "normal":
            # Source size and baseline already applied. Disable browser default rescaling/shift.
            tag = "sup" if span.script_hint == "superscript" else "sub"
            target = etree.SubElement(target, tag, style="font-size:inherit;vertical-align:baseline")
        target.text = "".join(c.text for _, c in run)
        emitted.extend((c.id, c.text) for _, c in run)
        previous_end = char.origin[0] + max(0, advance)


def link_characters(lines, link):
    return [
        c.id
        for line in lines
        for s in line.spans
        for c in s.characters
        if contains(link.bbox, center(c.bbox))
    ]
