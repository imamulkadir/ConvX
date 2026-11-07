"""Bounded CSS2 block reconstruction retaining native rectangular clip scopes.

Uses only ordinary HTML4 elements and literal CSS2 boxes/margins. Native SVG is
read solely to associate paint with clips and is never serialized into output.
"""

import hashlib
import json
import re
from collections import Counter
from decimal import Decimal

import pymupdf
from lxml import etree

from converter.edgar_clips import inside, inspect_clips
from converter.edgar_reflow import axis, vertical_plan
from converter.edgar_semantics import Paragraphs, aligned_fields
from converter.edgar_spacing import calibrate
from converter.edgar_symbols import canonical_symbol
from converter.errors import fail
from converter.html_generator.flow import pt
from converter.html_generator.generator import safe_uri
from converter.html_generator.models import AssetRequest, GenerationDiagnostic
from converter.html_generator.typography import font_family, link_characters, render_line


def slots(parent, width, rect, tag="div"):
    """Zero-height block reserves no extra page flow; its child retains clipping."""
    x0, y0, x1, y1 = rect
    outer = etree.SubElement(
        parent,
        tag,
        style=f"width:{pt(width)};height:0;margin:0;padding:0;line-height:0;font-size:0;display:block",
    )
    return etree.SubElement(
        outer,
        tag,
        style=f"display:inline-block;vertical-align:top;margin:{pt(y0)} 0 0 {pt(x0)};padding:0;width:{pt(max(0, x1 - x0))};height:{pt(max(0, y1 - y0))};overflow:hidden;line-height:0;font-size:0",
    )


class LayerBuilder:
    def __init__(self, source, layout, context):
        self.source, self.layout, self.context = source, layout, context
        self.asset_requests, self.diagnostics, self.emitted = [], [], []
        self.reflow_targets = {}
        self.runs = []
        self.clip_proof = []

    def warning(self, code, text, page=None):
        if any(d.code == code and d.page == page for d in self.diagnostics):
            return
        self.diagnostics.append(
            GenerationDiagnostic(
                code=code,
                severity="warning",
                description=text,
                remediation="Review the actual EDGAR preview and measured source comparison",
                page=page,
            )
        )

    def prepare(self):
        if sum(p.character_count for p in self.layout.pages) > 500000:
            raise ValueError("EDGAR character budget exceeded")

    def links(self):
        hrefs, anchors, work = {}, {}, 0
        for page in self.layout.pages:
            lines = [line for block in page.text_blocks for line in block.lines]
            work += page.character_count * len(page.links)
            if work > 2000000:
                raise ValueError("Source link association work limit exceeded")
            for link in page.links:
                self.context.check()
                href = None
                if link.kind == 2:
                    uri = link.uri or ""
                    normalized = "https://" + uri[7:] if uri.startswith("http://") else uri
                    if safe_uri(normalized):
                        href = normalized
                        if uri != normalized:
                            self.warning(
                                "EDGAR_SEC_LINK_HTTPS",
                                "An ordinary SEC Archives reference uses HTTPS; its visible source text is unchanged",
                                page.page_number,
                            )
                elif (
                    link.kind == 1
                    and link.destination_page is not None
                    and 1 <= link.destination_page <= len(self.layout.pages)
                ):
                    destination = self.layout.pages[link.destination_page - 1]
                    candidates = [line for block in destination.text_blocks for line in block.lines]
                    if candidates and link.destination_point is not None:
                        line = min(
                            candidates,
                            key=lambda item: (
                                abs(item.bbox[0] - link.destination_point[0])
                                + abs(item.bbox[1] - link.destination_point[1])
                            ),
                        )
                        name = f"destination{page.page_number}_{link.id}"
                        anchors.setdefault(line.id, []).append(name)
                        href = "#" + name
                    else:
                        href = f"#page{link.destination_page}"
                if href is None:
                    self.warning(
                        "EDGAR_EXTERNAL_LINK_INERT",
                        "A source link destination is not permitted by EFM78; its disclosure text is retained",
                        page.page_number,
                    )
                    continue
                identifiers = link_characters(lines, link)
                if not identifiers:
                    raise fail(
                        "EDGAR_LINK_REGION_UNSUPPORTED",
                        "generating_htm",
                        "A source hyperlink cannot be associated with selectable text",
                        "Resolve the source link region",
                        page=page.page_number,
                    )
                for identifier in identifiers:
                    if identifier in hrefs and hrefs[identifier] != href:
                        raise ValueError("Overlapping source hyperlink targets")
                    hrefs[identifier] = href
        return hrefs, anchors

    def render(self):
        root = etree.Element("html")
        head = etree.SubElement(root, "head")
        etree.SubElement(head, "title").text = "Converted document"
        etree.SubElement(head, "meta", name="convx-edgar-profile", content="edgar_layers_v1")
        body = etree.SubElement(
            root, "body", style="margin:0;padding:0;font-size:0;line-height:0;background-color:#d3d3d3"
        )
        assets = {a.id: a for a in self.layout.assets}
        requests = {}
        hrefs, anchors = self.links()
        with pymupdf.open(self.source) as native:
            for page, source in zip(self.layout.pages, native, strict=True):
                self.context.check()
                if page.geometry.rotation_degrees or page.annotations:
                    raise fail(
                        "EDGAR_GEOMETRY_UNSUPPORTED",
                        "generating_htm",
                        "Rotated pages or annotation appearances need an approved reconstruction",
                        "Use a static unrotated PDF",
                        page=page.page_number,
                    )
                try:
                    clips = inspect_clips(source, page, self.context)
                except ValueError as exc:
                    raise fail(
                        "EDGAR_CLIPPING_UNSUPPORTED",
                        "generating_htm",
                        "Native clipping cannot be associated with supported rectangular paint",
                        "Use Standard Mode for unsupported clipping geometry",
                        page=page.page_number,
                    ) from exc
                self.clip_proof.append(
                    {
                        "page": page.page_number,
                        "associations": len(clips),
                        "sha256": hashlib.sha256(json.dumps(clips, sort_keys=True).encode()).hexdigest(),
                    }
                )
                bounds = page.geometry.unrotated_bounds
                width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
                page_target = etree.SubElement(
                    body,
                    "div",
                    style=f"margin:0 auto;padding:0;width:{pt(width)};height:{pt(height)};page-break-after:{'auto' if page.page_number == len(self.layout.pages) else 'always'};font-size:0;line-height:0;background-color:#ffffff",
                )
                etree.SubElement(page_target, "a", name=f"page{page.page_number}")
                reflow = vertical_plan(source)
                self.reflow_targets[str(page.page_number)] = reflow["words"]
                header = etree.SubElement(
                    page_target, "div", style="height:0;margin:0;padding:0;font-size:0;line-height:0"
                )
                offset_y = reflow.get("content_offset_y", 0)
                target = slots(page_target, width, (0, offset_y, width, height))
                paragraphs = Paragraphs()
                # Actual simple native graphics; never rasterize disclosure text.
                for v in page.vectors:
                    if v.kind in {"clip", "group"}:
                        if v.kind == "group" and (
                            v.properties.get("opacity", 1) != 1
                            or v.properties.get("blendmode", "Normal") != "Normal"
                            or v.properties.get("knockout")
                        ):
                            raise ValueError("Unsupported source compositing")
                        continue
                    clip = clips[v.id]
                    container = slots(target, width, clip)
                    x0, y0, x1, y1 = v.bbox
                    style = ""
                    if (
                        v.kind == "f"
                        and len(v.items) == 1
                        and v.items[0].command == "re"
                        and v.properties.get("fill_opacity", 1) == 1
                    ):
                        color = v.fill_color
                        if color is None or len(color) != 3:
                            raise ValueError("Unsupported fill color")
                        rgb = "".join(f"{round(c * 255):02x}" for c in color)
                        style = f"background-color:#{rgb}"
                    elif (
                        v.kind == "s"
                        and len(v.items) == 1
                        and v.items[0].command == "l"
                        and v.properties.get("stroke_opacity", 1) == 1
                    ):
                        a, b = v.items[0].points
                        if a[0] != b[0] and a[1] != b[1]:
                            raise ValueError("Unsupported diagonal rule")
                        if v.properties.get("dashes", "[] 0").replace(" ", "") != "[]0":
                            raise ValueError("Unsupported dashed rule")
                        stroke = v.stroke_width_pt or 0
                        color = v.stroke_color
                        rgb = "".join(f"{round(c * 255):02x}" for c in color)
                        x0, y0, x1, y1 = x0 - stroke / 2, y0 - stroke / 2, x1 + stroke / 2, y1 + stroke / 2
                        style = f"background-color:#{rgb}"
                    else:
                        raise fail(
                            "EDGAR_VECTOR_UNSUPPORTED",
                            "generating_htm",
                            "Native vector is outside rectangular fill/rule reconstruction",
                            "Preserve the source using a supported graphic strategy",
                            page=page.page_number,
                        )
                    etree.SubElement(
                        container,
                        "div",
                        style=f"display:block;margin:{pt(y0 - clip[1])} 0 0 {pt(x0 - clip[0])};padding:0;width:{pt(x1 - x0)};height:{pt(y1 - y0)};{style}",
                    )
                for image in page.images:
                    a, b, c, d, _, _ = image.transform
                    if a <= 0 or d <= 0 or b or c:
                        raise ValueError("Unsupported image transform")
                    asset = assets[image.asset_id]
                    if asset.xref <= 0:
                        raise ValueError("Unsupported inline image")
                    if asset.id not in requests:
                        name = f"image{len(requests) + 1:03d}.jpg"
                        requests[asset.id] = [name, asset, []]
                    name, _, places = requests[asset.id]
                    places.append(image.id)
                    clip = clips[image.id]
                    container = slots(target, width, clip)
                    etree.SubElement(
                        container,
                        "img",
                        src=name,
                        alt="",
                        style=f"display:block;margin:{pt(image.bbox[1] - clip[1])} 0 0 {pt(image.bbox[0] - clip[0])};width:{pt(image.bbox[2] - image.bbox[0])};height:{pt(image.bbox[3] - image.bbox[1])};border:0",
                    )
                cell_owners = {}
                for table in [*page.tables, *aligned_fields(page, self.context)]:
                    if hasattr(table, "grid_resolved") and (
                        not table.grid_resolved or table.method != "native_lines_strict"
                    ):
                        raise fail(
                            "EDGAR_TABLE_GRID_UNRESOLVED",
                            "generating_htm",
                            "The source table grid is not verified",
                            "Resolve table membership before conversion",
                            page=page.page_number,
                        )
                    parent = slots(target, width, bounds)
                    paragraphs.order[parent.getparent()] = table.bbox
                    x0, y0, x1, y1 = table.bbox
                    element = etree.SubElement(
                        parent,
                        "table",
                        cellpadding="0",
                        cellspacing="0",
                        border="0",
                        style=f"margin:{pt(y0)} 0 0 {pt(x0)};padding:0;width:{pt(x1 - x0)};height:{pt(y1 - y0)};table-layout:fixed;border-collapse:collapse;font-size:0;line-height:0",
                    )
                    edges = sorted({c.bbox[k] for c in table.cells for k in (1, 3)})
                    if len(edges) != table.rows + 1:
                        raise ValueError("Table row geometry is incomplete")
                    by_start = {(c.row, c.column): c for c in table.cells}
                    for row in range(table.rows):
                        tr = etree.SubElement(
                            element, "tr", style=f"height:{pt(edges[row + 1] - edges[row])}"
                        )
                        for col in range(table.columns):
                            cell = by_start.get((row, col))
                            if cell is None:
                                continue
                            attrs = {
                                "style": f"padding:0;border:0;vertical-align:top;width:{pt(cell.bbox[2] - cell.bbox[0])};height:{pt(cell.bbox[3] - cell.bbox[1])};font-size:0;line-height:0"
                            }
                            if cell.row_span > 1:
                                attrs["rowspan"] = str(cell.row_span)
                            if cell.column_span > 1:
                                attrs["colspan"] = str(cell.column_span)
                            td = etree.SubElement(tr, "td", **attrs)
                            for identifier in cell.character_ids:
                                if identifier in cell_owners:
                                    raise ValueError("Duplicate table character ownership")
                                cell_owners[identifier] = (td, cell.bbox[0], cell.bbox[1])
                for block in page.text_blocks:
                    for line in block.lines:
                        if axis(line.direction) != "horizontal":
                            chunks = [
                                c
                                for c in reflow["chunks"]
                                if c["block"] == block.native_number and c["line"] == line.source_index
                            ]
                            if not chunks:
                                raise ValueError("Missing vertical reflow association")
                            for number, chunk in enumerate(chunks):
                                transform = pymupdf.Matrix(
                                    0,
                                    1,
                                    -1,
                                    0,
                                    chunk["left"] + chunk["source_y"],
                                    chunk["baseline"] - chunk["source_x"],
                                )
                                spans = []
                                for span in line.spans:
                                    selected = [
                                        c
                                        for c in span.characters
                                        if (number == 0 or c.origin[1] <= chunk["source_y"] + 0.001)
                                        and (chunk["next_y"] is None or c.origin[1] > chunk["next_y"] + 0.001)
                                    ]
                                    if not selected:
                                        continue
                                    if any(not inside(clips[c.id], c.bbox) for c in selected):
                                        self.warning(
                                            "EDGAR_CLIPPED_TEXT_REFLOWED",
                                            "Clipped vertical source disclosure is retained fully as horizontal selectable text; its visibility differs from the PDF",
                                            page.page_number,
                                        )
                                    chars = tuple(
                                        c.model_copy(
                                            update={
                                                "origin": tuple(pymupdf.Point(c.origin) * transform),
                                                "bbox": tuple(pymupdf.Rect(c.bbox) * transform),
                                                "quad": tuple(
                                                    tuple(pymupdf.Point(point) * transform)
                                                    for point in c.quad
                                                ),
                                            }
                                        )
                                        for c in selected
                                    )
                                    box = pymupdf.Rect(chars[0].bbox)
                                    for char in chars[1:]:
                                        box |= pymupdf.Rect(char.bbox)
                                    spans.append(
                                        span.model_copy(
                                            update={
                                                "characters": chars,
                                                "text": "".join(c.text for c in chars),
                                                "origin": tuple(pymupdf.Point(span.origin) * transform),
                                                "bbox": tuple(box),
                                            }
                                        )
                                    )
                                box = pymupdf.Rect(spans[0].bbox)
                                for span in spans[1:]:
                                    box |= pymupdf.Rect(span.bbox)
                                clone = line.model_copy(
                                    update={
                                        "direction": (1.0, 0.0),
                                        "spans": tuple(spans),
                                        "bbox": tuple(box),
                                    }
                                )
                                container = slots(header, width, bounds)
                                render_line(
                                    clone,
                                    container,
                                    self.emitted,
                                    hrefs,
                                    anchors,
                                    run_records=self.runs,
                                )
                            self.warning(
                                "EDGAR_VERTICAL_TEXT_REFLOWED",
                                "Vertical marginal disclosure is preserved as selectable horizontal text in a source-derived header or vacant band; its orientation and position differ from the source",
                                page.page_number,
                            )
                            continue
                        if line.writing_mode:
                            raise ValueError("Unsupported writing mode")
                        mapped = []
                        for span in line.spans:
                            chars = tuple(
                                c.model_copy(update={"text": canonical_symbol(span.font_name, c.text)})
                                for c in span.characters
                            )
                            changed = any(
                                a.text != b.text for a, b in zip(chars, span.characters, strict=True)
                            )
                            mapped.append(
                                span.model_copy(
                                    update={
                                        "characters": chars,
                                        "text": "".join(c.text for c in chars),
                                        **({"font_name": "Arial"} if changed else {}),
                                    }
                                )
                            )
                            if changed:
                                self.warning(
                                    "EDGAR_SYMBOL_ENCODING_RECOVERED",
                                    "Legacy Symbol/Wingdings source codes use their verified Unicode equivalents; disclosure symbols are retained",
                                    page.page_number,
                                )
                        line = line.model_copy(update={"spans": tuple(mapped)})
                        groups = {}
                        for span in line.spans:
                            if (
                                span.opacity != 255
                                or span.bidi_level
                                or any(m != 0 for m in span.render_modes)
                                or not font_family(span.font_name)
                            ):
                                raise ValueError("Unsupported text paint")
                            for char in span.characters:
                                owner = cell_owners.get(char.id)
                                groups.setdefault((clips[char.id], owner), set()).add(char.id)
                        for (clip, owner), selected in groups.items():
                            container, origin, top, unclipped = paragraphs.container(
                                target, block, line, clip, owner, selected, width, slots
                            )
                            render_line(
                                line,
                                container,
                                self.emitted,
                                hrefs,
                                anchors,
                                selected=selected,
                                offset=origin,
                                run_records=self.runs,
                                tag="font",
                            )
                            paragraph = container[-1]
                            declarations = paragraph.get("style").split(";")
                            for n, item in enumerate(declarations):
                                if item.startswith("padding:"):
                                    declarations[n] = "padding:0"
                                elif item.startswith("margin:"):
                                    declarations[n] = item.replace("margin:0 ", f"margin:{pt(top)} ", 1)
                            paragraph.set(
                                "style", "display:inline-block;vertical-align:top;" + ";".join(declarations)
                            )
                paragraphs.sort(target)
                for table in target.iter("td"):
                    paragraphs.sort(table)
                self.context.check()
        expected = [
            (c.id, canonical_symbol(s.font_name, c.text))
            for p in self.layout.pages
            for b in p.text_blocks
            for line in b.lines
            for s in line.spans
            for c in s.characters
        ]
        if Counter(self.emitted) != Counter(expected):
            raise ValueError("EDGAR character identity mismatch")
        for name, asset, places in requests.values():
            self.asset_requests.append(
                AssetRequest(
                    filename=name,
                    asset_id=asset.id,
                    source_pdf_sha256=self.layout.source_pdf_sha256,
                    source_xref=asset.xref,
                    soft_mask_xref=asset.soft_mask_xref,
                    placement_ids=tuple(places),
                )
            )
        calibrate(self.runs, self.context)
        # CSS2 numbers do not use exponent notation; keep tiny native rounding
        # values exact without changing disclosure or font-family strings.
        for element in root.iter():
            if "style" not in element.attrib:
                continue
            declarations = []
            for item in element.get("style").split(";"):
                name, separator, value = item.partition(":")
                if name.strip() != "font-family":
                    value = re.sub(
                        r"(-?\d+(?:\.\d+)?[eE][+-]?\d+)(?=pt|px)", lambda m: format(Decimal(m[1]), "f"), value
                    )
                    # Sub-micro-point precision has no browser layout meaning.
                    # Keep source text untouched and bound numeric rounding far
                    # below the existing geometry checks; never minify by words.
                    value = re.sub(
                        r"-?\d+\.\d+(?=pt|px)",
                        lambda m: (
                            format(Decimal(m[0]).quantize(Decimal("0.000001")), "f").rstrip("0").rstrip(".")
                            or "0"
                        ),
                        value,
                    )
                declarations.append(name + separator + value)
            element.set("style", ";".join(declarations))
        payload = etree.tostring(root, method="html", encoding="ascii")
        if len(payload) > 25 * 1024 * 1024:
            raise ValueError("EDGAR output budget exceeded")
        return payload
