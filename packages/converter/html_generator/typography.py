from __future__ import annotations

import re

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


def render_line(line, parent, emitted, hrefs, anchors, selected=None, offset=(0, 0)):
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
    for index, (span, char) in enumerate(characters):
        target = p
        if char.id in hrefs:
            target = etree.SubElement(
                target, "a", href=hrefs[char.id], style="color:inherit;text-decoration:none"
            )
        style = f"font-family:'{font_family(span.font_name)}';font-size:{pt(span.font_size_pt)};line-height:1;color:#{span.color_rgb:06x};vertical-align:{pt(baseline - span.origin[1])}"
        # Origin-to-origin advances preserve source kerning and word spacing without invented text.
        following = characters[index + 1][1].origin[0] if index + 1 < len(characters) else char.bbox[2]
        advance = following - char.origin[0]
        style += f";display:inline-block;width:{pt(max(0, advance))};margin-left:{pt(char.origin[0] - previous_end)}"
        target = etree.SubElement(target, "font", style=style)
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
        target.text = char.text
        emitted.append((char.id, char.text))
        previous_end = char.origin[0] + max(0, advance)


def link_characters(lines, link):
    return [
        c.id
        for line in lines
        for s in line.spans
        for c in s.characters
        if contains(link.bbox, center(c.bbox))
    ]
