from __future__ import annotations

import hashlib
import re
from collections import defaultdict

import pymupdf

from converter.errors import fail
from converter.layout.models import (
    Character,
    FontDefinition,
    ParagraphCandidate,
    TextBlock,
    TextLine,
    TextPaint,
    TextSpan,
)
from converter.pdf_analysis.geometry import box, point, quad_points, visibility


def normalized_font(name):
    return re.sub(r"^[A-Z]{6}\+", "", name).replace(" ", "").casefold()


def register_fonts(page, registry):
    lookup = defaultdict(list)
    for xref, ext, font_type, base, resource, encoding, referrer in page.get_fonts(full=True):
        identifier = (
            f"font-x{xref:08d}"
            if xref
            else "font-native-"
            + hashlib.sha256(f"{base}|{ext}|{font_type}|{encoding}".encode()).hexdigest()[:16]
        )
        if identifier in registry:
            previous = registry[identifier]
            registry[identifier] = previous.model_copy(
                update={
                    "resource_names": tuple(sorted(set(previous.resource_names) | {resource})),
                    "referring_xrefs": tuple(sorted(set(previous.referring_xrefs) | {referrer})),
                }
            )
        else:
            registry[identifier] = FontDefinition(
                id=identifier,
                xref=xref,
                base_font=base,
                resource_names=(resource,),
                font_type=font_type,
                file_extension=ext,
                encoding=encoding,
                referring_xrefs=(referrer,),
            )
        lookup[normalized_font(base)].append(identifier)
    return lookup


def _key(font, origin, text):
    return normalized_font(font), round(origin[0], 3), round(origin[1], 3), text


def _underline(span, direction, paths):
    native_flags = span.get("char_flags")
    if native_flags is not None and native_flags & pymupdf.mupdf.FZ_STEXT_UNDERLINE:
        return True, ()
    if abs(direction[0] - 1) > 0.001 or abs(direction[1]) > 0.001:
        return None, ()
    x0, _, x1, _ = span["bbox"]
    baseline, size = span["origin"][1], span["size"]
    evidence = []
    for path in paths:
        if (
            path.kind not in {"s", "fs"}
            or path.stroke_width_pt is None
            or path.stroke_width_pt > max(1.5, size * 0.12)
        ):
            continue
        for item in path.items:
            if item.command != "l":
                continue
            a, b = item.points
            if abs(a[1] - b[1]) <= 0.1 and 0.25 <= a[1] - baseline <= size * 0.25:
                left, right = sorted((a[0], b[0]))
                if left <= x0 + 1 and right >= x1 - 1 and (right - left) <= (x1 - x0) * 1.5 + 2:
                    evidence.append(path.id)
    return (True, tuple(sorted(set(evidence)))) if evidence else (None, ())


def extract_text(page, prefix, policy, guard, font_registry, vector_paths, bounds, diagnostic):
    flags = pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_IMAGES
    raw = page.get_text("rawdict", sort=False, flags=flags, clip=pymupdf.INFINITE_RECT())
    raw_blocks = [b for b in raw["blocks"] if b["type"] == 0]
    if len(raw_blocks) > policy.max_blocks_per_page:
        raise fail(
            "PDF_ANALYSIS_LIMIT",
            "analyzing_pdf",
            "Text block count limit exceeded",
            "Review extraction policy",
        )
    raw_text = "".join(
        c["c"] for b in raw_blocks for line in b["lines"] for span in line["spans"] for c in span["chars"]
    )
    guard.characters(
        sum(1 for b in raw_blocks for line in b["lines"] for span in line["spans"] for _c in span["chars"])
    )
    lookup = register_fonts(page, font_registry)
    traces = page.get_texttrace()
    trace_index = defaultdict(list)
    for trace in traces:
        for char in trace["chars"]:
            if 0 <= char[0] <= 0x10FFFF:
                trace_index[_key(trace["font"], char[2], chr(char[0]))].append(
                    (trace["seqno"], trace["type"], char[1])
                )
    character_map = defaultdict(list)
    blocks = []
    count = 0
    for bi, raw_block in enumerate(raw_blocks):
        guard.check()
        block_id, lines = f"{prefix}-b{bi:05d}", []
        for li, raw_line in enumerate(raw_block["lines"]):
            line_id, spans = f"{block_id}-l{li:04d}", []
            direction = point(raw_line["dir"])
            dominant = max(raw_line["spans"], key=lambda s: (s["size"], len(s["chars"])), default=None)
            normal = (-direction[1], direction[0])
            dominant_baseline = (
                sum(a * b for a, b in zip(dominant["origin"], normal, strict=True)) if dominant else 0
            )
            for si, raw_span in enumerate(raw_line["spans"]):
                span_id, chars, sequences, modes = f"{line_id}-s{si:04d}", [], set(), set()
                font_ids = tuple(sorted(set(lookup.get(normalized_font(raw_span["font"]), []))))
                if len(font_ids) != 1:
                    diagnostic(
                        "FONT_RESOURCE_AMBIGUOUS",
                        "warning",
                        span_id,
                        "Span font could not be uniquely associated with a PDF resource",
                        "Use preserved font name/metrics and resolve resource mapping",
                    )
                for ci, char in enumerate(raw_span["chars"]):
                    count += 1
                    if count % 256 == 0:
                        guard.check()
                    identifier = f"{span_id}-c{ci:05d}"
                    key = _key(raw_span["font"], char["origin"], char["c"])
                    matches = trace_index.get(key, [])
                    sequences.update(m[0] for m in matches)
                    modes.update(m[1] for m in matches)
                    character_map[key].append(identifier)
                    if "\ufffd" in char["c"] or any(
                        0xD800 <= ord(c) <= 0xDFFF or ord(c) == 0 for c in char["c"]
                    ):
                        diagnostic(
                            "UNICODE_MAPPING_UNRESOLVED",
                            "error",
                            identifier,
                            "A disclosure glyph lacks a reliable Unicode mapping",
                            "Resolve source glyph mapping before reconstruction",
                        )
                    chars.append(
                        Character(
                            id=identifier,
                            text=char["c"],
                            origin=point(char["origin"]),
                            bbox=box(char["bbox"]),
                            quad=quad_points(pymupdf.recover_char_quad(direction, raw_span, char)),
                            synthetic=bool(char.get("synthetic", False)),
                            glyph_ids=tuple(sorted({m[2] for m in matches})),
                        )
                    )
                underline, underline_paths = _underline(raw_span, direction, vector_paths)
                script, script_source = "normal", "none"
                if raw_span["flags"] & 1:
                    script, script_source = "superscript", "native_flag"
                elif dominant and raw_span["size"] < dominant["size"] * 0.85:
                    delta = (
                        sum(a * b for a, b in zip(raw_span["origin"], normal, strict=True))
                        - dominant_baseline
                    )
                    if abs(delta) > dominant["size"] * 0.15:
                        script, script_source = (
                            ("superscript" if delta < 0 else "subscript"),
                            "relative_baseline",
                        )
                crop_visibility = visibility(raw_span["bbox"], bounds)
                if crop_visibility != "inside":
                    diagnostic(
                        "TEXT_CROP_VISIBILITY",
                        "warning",
                        span_id,
                        "Text extends beyond the visible crop area",
                        "Preserve clipping intent; do not silently add or remove disclosure",
                    )
                bidi = int(raw_span.get("bidi", 0))
                if bidi:
                    diagnostic(
                        "BIDI_READING_ORDER_UNRESOLVED",
                        "error",
                        span_id,
                        "Bidirectional text requires logical-order verification",
                        "Resolve with accepted OOXML semantics before reconstruction",
                    )
                spans.append(
                    TextSpan(
                        id=span_id,
                        source_index=si,
                        bbox=box(raw_span["bbox"]),
                        origin=point(raw_span["origin"]),
                        text="".join(c.text for c in chars),
                        font_name=raw_span["font"],
                        font_ids=font_ids,
                        font_size_pt=raw_span["size"],
                        font_flags=raw_span["flags"],
                        character_flags=raw_span.get("char_flags"),
                        bold_hint=bool(raw_span["flags"] & 16),
                        italic_hint=bool(raw_span["flags"] & 2),
                        underline_hint=underline,
                        underline_evidence=underline_paths,
                        script_hint=script,
                        script_evidence=script_source,
                        color_rgb=raw_span["color"],
                        opacity=raw_span.get("alpha", 255),
                        ascender=raw_span["ascender"],
                        descender=raw_span["descender"],
                        bidi_level=bidi,
                        render_modes=tuple(sorted(modes)),
                        paint_sequences=tuple(sorted(sequences)),
                        characters=tuple(chars),
                        crop_visibility=crop_visibility,
                    )
                )
            advance = None
            if li + 1 < len(raw_block["lines"]) and raw_line["spans"] and raw_block["lines"][li + 1]["spans"]:
                next_line = raw_block["lines"][li + 1]
                if all(abs(a - b) < 0.001 for a, b in zip(direction, next_line["dir"], strict=True)):
                    a, b = raw_line["spans"][0]["origin"], next_line["spans"][0]["origin"]
                    advance = (b[0] - a[0]) * normal[0] + (b[1] - a[1]) * normal[1]
            lines.append(
                TextLine(
                    id=line_id,
                    source_index=li,
                    bbox=box(raw_line["bbox"]),
                    direction=direction,
                    writing_mode=raw_line["wmode"],
                    spans=tuple(spans),
                    observed_bbox_height_pt=raw_line["bbox"][3] - raw_line["bbox"][1],
                    baseline_origins=tuple(s.origin for s in spans),
                    advance_to_next_line_pt=advance,
                )
            )
        blocks.append(
            TextBlock(
                id=block_id,
                native_number=raw_block["number"],
                bbox=box(raw_block["bbox"]),
                lines=tuple(lines),
                paragraphs=(
                    ParagraphCandidate(
                        id=block_id + "-paragraph",
                        bbox=box(raw_block["bbox"]),
                        line_ids=tuple(line.id for line in lines),
                    ),
                ),
            )
        )
    paints = []
    for trace in traces:
        ids = []
        for char in trace["chars"]:
            if 0 <= char[0] <= 0x10FFFF:
                ids.extend(character_map.get(_key(trace["font"], char[2], chr(char[0])), []))
        paints.append(
            TextPaint(
                sequence=trace["seqno"],
                render_mode=trace["type"],
                font_name=trace["font"],
                font_size_pt=trace["size"],
                bbox=box(trace["bbox"]),
                direction=point(trace["dir"]),
                opacity=trace["opacity"],
                color_space_components=trace["colorspace"],
                color=tuple(trace["color"])
                if isinstance(trace["color"], (tuple, list))
                else (trace["color"],),
                stroke_width_pt=trace["linewidth"],
                layer=trace.get("layer", ""),
                character_ids=tuple(dict.fromkeys(ids)),
            )
        )
    return tuple(blocks), tuple(paints), count, hashlib.sha256(raw_text.encode()).hexdigest()
