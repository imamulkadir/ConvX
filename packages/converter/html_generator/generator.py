"""PDF-first, manual-constrained normal-flow candidate HTM reconstruction."""

from __future__ import annotations

import hashlib
import os
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

import psutil
from lxml import etree, html

from converter.context import ProcessingContext
from converter.errors import fail
from converter.html_generator.flow import Partitioner, emit_flow, pt
from converter.html_generator.models import (
    AssetRequest,
    GenerationDiagnostic,
    GenerationPolicy,
    GenerationResult,
    Item,
)
from converter.html_generator.tables import path_edges, render_table, rgb
from converter.html_generator.typography import font_family, link_characters, render_line
from converter.layout.models import DocumentLayout
from converter.ooxml import sha256
from converter.pdf_analysis.extract import _gate
from converter.pdf_analysis.geometry import contains, union


def safe_uri(value):
    """Conservative generator output contract; Stage 6 validates actual file links."""
    if not value or any(ord(c) < 33 or ord(c) > 126 for c in value) or "\\" in value or "%" in value:
        return False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and parsed.netloc == "www.sec.gov"
        and parsed.path.startswith("/Archives/edgar/data/")
        and not any(part in {".", ".."} for part in parsed.path.split("/"))
        and not parsed.query
    )


def simple_stroke(path):
    return (
        path.kind == "s"
        and path.stroke_width_pt is not None
        and path.stroke_width_pt > 0
        and rgb(path.stroke_color) is not None
        and path.properties.get("stroke_opacity", 1) == 1
        and path.properties.get("dashes", "[] 0").replace(" ", "") == "[]0"
        and all(item.command in {"l", "re"} for item in path.items)
    )


class Builder:
    def __init__(self, layout, policy, context):
        self.layout, self.policy, self.context = layout, policy, context
        self.diagnostics = []
        self.emitted = []
        self.asset_requests = []
        self.plans = []
        self.partitioner = Partitioner(policy, context)
        self.hrefs, self.anchors = {}, {}
        self.process, self.next_memory = psutil.Process(), 0.0

    def check(self):
        self.context.check()
        now = time.monotonic()
        if now >= self.next_memory:
            self.next_memory = now + 0.1
            if self.process.memory_info().rss > self.policy.max_memory_bytes:
                raise fail(
                    "HTM_MEMORY_LIMIT",
                    "generating_htm",
                    "Reconstruction memory budget exceeded",
                    "Review the bounded worker profile",
                )

    def diagnostic(
        self, code, description, remediation, page=None, element=None, severity="error", section=None
    ):
        # Aggregate at page/code; no disclosure excerpts enter reports or logs.
        if not any(d.code == code and d.page == page for d in self.diagnostics):
            self.diagnostics.append(
                GenerationDiagnostic(
                    code=code,
                    severity=severity,
                    description=description,
                    remediation=remediation,
                    page=page,
                    element=element,
                    section=section,
                )
            )

    def links(self):
        for page in self.layout.pages:
            self.partitioner.work += page.character_count * len(page.links)
            if self.partitioner.work > self.policy.max_partition_work:
                raise fail(
                    "HTM_LINK_WORK_LIMIT",
                    "generating_htm",
                    "Hyperlink association budget exceeded",
                    "Review bounded generation limits",
                )
            lines = [line for b in page.text_blocks for line in b.lines]
            for link in page.links:
                self.check()
                href = None
                if link.kind == 2 and safe_uri(link.uri):
                    href = link.uri
                elif (
                    link.kind == 1
                    and link.destination_page is not None
                    and 1 <= link.destination_page <= len(self.layout.pages)
                ):
                    destination = self.layout.pages[link.destination_page - 1]
                    dest_lines = [line for b in destination.text_blocks for line in b.lines]
                    if dest_lines and link.destination_point is not None:
                        line = min(
                            dest_lines,
                            key=lambda line: (
                                abs(line.bbox[1] - link.destination_point[1])
                                + abs(line.bbox[0] - link.destination_point[0])
                            ),
                        )
                        anchor = f"destination{page.page_number}_{link.xref or link.id}"
                        self.anchors.setdefault(line.id, []).append(anchor)
                        href = "#" + anchor
                        self.diagnostic(
                            "HTM_LINK_DESTINATION_APPROXIMATE",
                            "PDF destination mapped to its nearest disclosure line",
                            "Verify destination geometry in visual validation",
                            page.page_number,
                            link.id,
                            "warning",
                            "5.2.2.3",
                        )
                    else:
                        href = f"#page{link.destination_page}"
                if href is None:
                    self.diagnostic(
                        "HTM_LINK_UNSUPPORTED",
                        "Hyperlink cannot be represented by the conservative filing candidate profile",
                        "Resolve the original target without silently removing the link",
                        page.page_number,
                        link.id,
                        section="5.2.2.3",
                    )
                    continue
                ids = link_characters(lines, link)
                if not ids:
                    self.diagnostic(
                        "HTM_LINK_REGION_UNSUPPORTED",
                        "Link has no uniquely associated disclosure text",
                        "Resolve image/empty-region hyperlinks before reconstruction",
                        page.page_number,
                        link.id,
                    )
                for identifier in ids:
                    if identifier in self.hrefs and self.hrefs[identifier] != href:
                        self.diagnostic(
                            "HTM_LINK_OVERLAP",
                            "Overlapping link targets affect the same character",
                            "Resolve hyperlink semantics",
                            page.page_number,
                            link.id,
                        )
                    self.hrefs[identifier] = href

    def prepare(self):
        self.check()
        self.links()
        assets = {a.id: a for a in self.layout.assets}
        requests = {}
        for page in self.layout.pages:
            self.context.check()
            number = page.page_number
            if page.geometry.rotation_degrees:
                self.diagnostic(
                    "HTM_PAGE_ROTATION_UNSUPPORTED",
                    "Rotated page geometry cannot be reconstructed with this normal-flow profile",
                    "Add a permitted geometry strategy and validate its appearance",
                    number,
                )
            lines = [line for b in page.text_blocks for line in b.lines]
            allchars = {c.id: c for line in lines for s in line.spans for c in s.characters}
            self.partitioner.work += len(allchars) * sum(len(t.cells) for t in page.tables) * 3
            if self.partitioner.work > self.policy.max_partition_work:
                raise fail(
                    "HTM_TABLE_WORK_LIMIT",
                    "generating_htm",
                    "Table membership/render budget exceeded",
                    "Review cell complexity and bounded generation limits",
                )
            if (
                len(allchars) > self.policy.max_characters
                or sum(p.character_count for p in self.layout.pages) > self.policy.max_characters
            ):
                raise fail(
                    "HTM_CHARACTER_LIMIT",
                    "generating_htm",
                    "Generation character budget exceeded",
                    "Review bounded generation limits",
                )
            items, payloads, owned, consumed = [], {}, set(), set()
            for line in lines:
                if line.direction != (1.0, 0.0) or line.writing_mode:
                    self.diagnostic(
                        "HTM_TEXT_ROTATION_UNSUPPORTED",
                        "Rotated or vertical disclosure requires an approved markup strategy",
                        "Preserve text and fail strict reconstruction; do not rasterize disclosure",
                        number,
                        line.id,
                    )
                chars = [c for s in line.spans for c in s.characters]
                if any(b.origin[0] < a.origin[0] for a, b in zip(chars, chars[1:], strict=False)):
                    self.diagnostic(
                        "HTM_TEXT_ADVANCE_UNSUPPORTED",
                        "Nonmonotonic horizontal glyph origins require overlapping or bidirectional layout",
                        "Resolve logical order and glyph placement",
                        number,
                        line.id,
                    )
                for span in line.spans:
                    if font_family(span.font_name) is None:
                        self.diagnostic(
                            "HTM_FONT_NAME_UNSUPPORTED",
                            "Font name cannot be safely represented in the candidate profile",
                            "Resolve a verified local font family",
                            number,
                            span.id,
                        )
                    if (
                        span.crop_visibility != "inside"
                        or span.opacity != 255
                        or span.bidi_level
                        or any(mode != 0 for mode in span.render_modes)
                    ):
                        self.diagnostic(
                            "HTM_TEXT_PAINT_UNSUPPORTED",
                            "Clipped, translucent, stroked or nonstandard text requires unsupported painting",
                            "Implement permitted text painting without losing searchable disclosure",
                            number,
                            span.id,
                        )
                    if not 0 < span.font_size_pt <= 1000 or not 0 <= span.color_rgb <= 0xFFFFFF:
                        self.diagnostic(
                            "HTM_TYPOGRAPHY_RANGE",
                            "Invalid font size or color",
                            "Resolve extraction typography",
                            number,
                            span.id,
                        )
                    if any(
                        any(
                            ord(ch) < 32
                            and ch not in "\t\n\r"
                            or 0x7F <= ord(ch) <= 0x9F
                            or 0xD800 <= ord(ch) <= 0xDFFF
                            for ch in c.text
                        )
                        for c in span.characters
                    ):
                        self.diagnostic(
                            "HTM_CHARACTER_UNREPRESENTABLE",
                            "Control or surrogate characters cannot be safely serialized",
                            "Resolve Unicode without silent replacement",
                            number,
                            span.id,
                            section="5.2.2.6",
                        )
                    consumed.update(span.underline_evidence)
            for table in page.tables:
                if table.method != "native_lines_strict" or not table.grid_resolved:
                    self.diagnostic(
                        "HTM_TABLE_SEMANTICS_UNRESOLVED",
                        "Inferred or unresolved table grid is insufficient for strict reconstruction",
                        "Verify cell relationships with accepted OOXML",
                        number,
                        table.id,
                    )
                    continue
                edges = {v for cell in table.cells for v in (cell.bbox[1], cell.bbox[3])}
                if len(edges) != table.rows + 1:
                    self.diagnostic(
                        "HTM_TABLE_ROW_GEOMETRY",
                        "Table row boundaries are incomplete",
                        "Resolve merged-cell geometry",
                        number,
                        table.id,
                    )
                for cell in table.cells:
                    self.check()
                    expected = {
                        (r, c)
                        for r in range(cell.row, cell.row + (cell.row_span or 0))
                        for c in range(cell.column, cell.column + (cell.column_span or 0))
                    }
                    actual = {
                        (r, c)
                        for r, row in enumerate(table.grid)
                        for c, value in enumerate(row)
                        if value == cell.id
                    }
                    if expected != actual or owned.intersection(cell.character_ids):
                        self.diagnostic(
                            "HTM_TABLE_MEMBERSHIP",
                            "Overlapping cells or inconsistent merged-cell membership",
                            "Resolve cell structure without duplicating text",
                            number,
                            cell.id,
                        )
                    owned.update(cell.character_ids)
                    consumed.update(cell.border_path_ids)
                    selected = set(cell.character_ids)
                    cursor = cell.bbox[1]
                    selected_lines = [
                        [c for s in line.spans for c in s.characters if c.id in selected] for line in lines
                    ]
                    for chars in sorted(
                        (cs for cs in selected_lines if cs),
                        key=lambda cs: (min(c.bbox[1] for c in cs), min(c.origin[0] for c in cs)),
                    ):
                        if min(c.bbox[1] for c in chars) < cursor or not all(
                            contains(cell.bbox, point)
                            for c in chars
                            for point in ((c.bbox[0], c.bbox[1]), (c.bbox[2], c.bbox[3]))
                        ):
                            self.diagnostic(
                                "HTM_TABLE_TEXT_OVERLAP",
                                "Cell disclosure overlaps adjacent lines or extends outside the physical cell",
                                "Resolve exact cell layout without clipping text",
                                number,
                                cell.id,
                            )
                        cursor = max(c.bbox[3] for c in chars)
                items.append(Item(id=table.id, kind="table", bbox=table.bbox))
                payloads[table.id] = table
            for line in lines:
                selected = {c.id for s in line.spans for c in s.characters if c.id not in owned}
                if selected:
                    bbox = union([allchars[i].bbox for i in selected])
                    items.append(Item(id=line.id, kind="line", bbox=bbox))
                    payloads[line.id] = (line, selected)
            for image in page.images:
                a, b, c, d, _, _ = image.transform
                if a <= 0 or d <= 0 or b != 0 or c != 0 or image.clipping != "page_bounds_only":
                    self.diagnostic(
                        "HTM_IMAGE_TRANSFORM_UNSUPPORTED",
                        "Image rotation, reflection, skew or clipping needs normalized pixels",
                        "Normalize only the graphic while preserving its source transform",
                        number,
                        image.id,
                    )
                if not all(
                    contains(page.geometry.unrotated_bounds, point)
                    for point in ((image.bbox[0], image.bbox[1]), (image.bbox[2], image.bbox[3]))
                ):
                    self.diagnostic(
                        "HTM_IMAGE_CROP_UNSUPPORTED",
                        "Image extends outside the page crop",
                        "Resolve exact graphic clipping",
                        number,
                        image.id,
                    )
                asset = assets[image.asset_id]
                if asset.xref <= 0:
                    self.diagnostic(
                        "HTM_INLINE_IMAGE_UNSUPPORTED",
                        "Inline image needs a verified extraction locator",
                        "Resolve source stream before generating asset requests",
                        number,
                        image.id,
                    )
                if asset.id not in requests:
                    requests[asset.id] = [f"image{len(requests) + 1:03d}.jpg", asset, []]
                requests[asset.id][2].append(image.id)
                items.append(Item(id=image.id, kind="image", bbox=image.bbox))
                payloads[image.id] = (image, requests[asset.id][0])
            vectors = {v.id: v for v in page.vectors}
            for path in page.vectors:
                if path.id in consumed:
                    if not simple_stroke(path):
                        self.diagnostic(
                            "HTM_BORDER_PAINT_UNSUPPORTED",
                            "Table/underline border uses unsupported native painting",
                            "Preserve stroke pattern, color and opacity before reconstruction",
                            number,
                            path.id,
                        )
                    continue
                if path.kind in {"clip", "group"}:
                    if path.kind == "group" and (
                        path.properties.get("isolated")
                        or path.properties.get("knockout")
                        or path.properties.get("opacity", 1) != 1
                        or path.properties.get("blendmode", "Normal") != "Normal"
                    ):
                        self.diagnostic(
                            "HTM_COMPOSITING_UNSUPPORTED",
                            "Nontrivial compositing group cannot be represented",
                            "Resolve native compositing without rasterizing disclosure",
                            number,
                            path.id,
                        )
                    continue
                edges = path_edges(path)
                if simple_stroke(path) and len(edges) == 1:
                    a, b = edges[0]
                    if a[0] == b[0] or a[1] == b[1]:
                        half = path.stroke_width_pt / 2
                        bbox = (
                            min(a[0], b[0]) - half,
                            min(a[1], b[1]) - half,
                            max(a[0], b[0]) + half,
                            max(a[1], b[1]) + half,
                        )
                        items.append(Item(id=path.id, kind="rule", bbox=bbox))
                        payloads[path.id] = path
                        continue
                if (
                    len(path.items) == 1
                    and path.items[0].command == "re"
                    and path.kind in {"f", "s", "fs"}
                    and path.properties.get("fill_opacity", 1) == 1
                    and (path.fill_color is None or rgb(path.fill_color))
                    and (path.kind == "f" or simple_stroke(path))
                ):
                    items.append(Item(id=path.id, kind="rectangle", bbox=path.items[0].rect))
                    payloads[path.id] = path
                    continue
                self.diagnostic(
                    "HTM_VECTOR_UNSUPPORTED",
                    "Vector path requires an unsupported drawing or compositing operation",
                    "Add a permitted shape strategy or graphic-only asset extraction",
                    number,
                    path.id,
                )
            # Ensure consumed evidence did not accidentally hide drawing outside its owner.
            for identifier in consumed:
                path = vectors[identifier]
                if (
                    path.bbox
                    and not any(
                        all(
                            contains(t.bbox, p, tolerance=0.01)
                            for p in ((path.bbox[0], path.bbox[1]), (path.bbox[2], path.bbox[3]))
                        )
                        for t in page.tables
                    )
                    and not any(identifier in s.underline_evidence for line in lines for s in line.spans)
                ):
                    self.diagnostic(
                        "HTM_BORDER_EXTENT_UNSUPPORTED",
                        "Consumed border has painting outside its table",
                        "Split native drawing evidence without dropping graphics",
                        number,
                        identifier,
                    )
            if len(items) > self.policy.max_items_per_page:
                raise fail(
                    "HTM_ITEM_LIMIT",
                    "generating_htm",
                    "Page reconstruction item budget exceeded",
                    "Review bounded generation limits",
                )
            tree = self.partitioner.build(items)
            if items and tree is None:
                self.diagnostic(
                    "HTM_FLOW_OVERLAP_UNSUPPORTED",
                    "Overlapping or interlocking content cannot be represented by this normal-flow profile",
                    "Resolve an allowed layout strategy; preserve disclosure and fail strict reconstruction",
                    number,
                )
            self.plans.append((page, tree, payloads))
        self.asset_requests = [
            AssetRequest(
                filename=name,
                asset_id=asset.id,
                source_pdf_sha256=self.layout.source_pdf_sha256,
                source_xref=asset.xref,
                soft_mask_xref=asset.soft_mask_xref,
                placement_ids=tuple(ids),
            )
            for name, asset, ids in requests.values()
        ]

    def render(self):
        root = etree.Element("html")
        head = etree.SubElement(root, "head")
        etree.SubElement(head, "title").text = "Document"
        body = etree.SubElement(root, "body", style="margin:0;padding:0;background-color:#ffffff")
        for page, tree, payloads in self.plans:
            self.context.check()
            bounds = page.geometry.unrotated_bounds
            element = etree.SubElement(
                body,
                "div",
                style=f"width:{pt(bounds[2] - bounds[0])};height:{pt(bounds[3] - bounds[1])};margin:0;padding:0;font-size:0;page-break-after:always",
            )
            etree.SubElement(element, "a", name=f"page{page.page_number}")
            if tree is None:
                continue
            container = etree.SubElement(
                element,
                "div",
                style=f"margin:0;padding:{pt(tree.bbox[1] - bounds[1])} 0 0 {pt(tree.bbox[0] - bounds[0])};width:{pt(tree.bbox[2] - tree.bbox[0])};height:{pt(tree.bbox[3] - tree.bbox[1])}",
            )

            def leaf(item, parent, payloads=payloads, page=page):
                self.check()
                value = payloads[item.id]
                if item.kind == "line":
                    line, selected = value
                    render_line(
                        line,
                        parent,
                        self.emitted,
                        self.hrefs,
                        self.anchors,
                        selected,
                        offset=(item.bbox[0], item.bbox[1]),
                    )
                elif item.kind == "table":
                    render_table(value, page, parent, self.emitted, self.hrefs, self.anchors)
                elif item.kind == "image":
                    image, name = value
                    etree.SubElement(
                        parent,
                        "img",
                        src=name,
                        alt="",
                        style=f"display:block;width:{pt(image.bbox[2] - image.bbox[0])};height:{pt(image.bbox[3] - image.bbox[1])};border:0",
                    )
                elif item.kind == "rule":
                    a, b = path_edges(value)[0]
                    side = "left" if a[0] == b[0] else "top"
                    etree.SubElement(
                        parent,
                        "div",
                        style=f"width:{pt(abs(b[0] - a[0]))};height:{pt(abs(b[1] - a[1]))};border-{side}:{pt(value.stroke_width_pt)} solid {rgb(value.stroke_color)};margin:0;padding:0",
                    )
                else:
                    style = f"width:{pt(item.bbox[2] - item.bbox[0])};height:{pt(item.bbox[3] - item.bbox[1])};box-sizing:border-box;margin:0;padding:0"
                    if value.fill_color is not None:
                        style += f";background-color:{rgb(value.fill_color)}"
                    if value.stroke_color is not None:
                        style += f";border:{pt(value.stroke_width_pt)} solid {rgb(value.stroke_color)}"
                    etree.SubElement(parent, "div", style=style)

            emit_flow(tree, container, leaf)
            self.check()
        if sum(1 for _ in root.iter()) > self.policy.max_nodes:
            raise fail(
                "HTM_NODE_LIMIT",
                "generating_htm",
                "Candidate HTML node budget exceeded",
                "Review bounded generation limits",
            )
        payload = etree.tostring(root, method="html", encoding="ascii", pretty_print=False)
        if len(payload) > self.policy.max_html_bytes:
            raise fail(
                "HTM_BYTE_LIMIT",
                "generating_htm",
                "Candidate HTML byte budget exceeded",
                "Review bounded generation limits",
            )
        expected = [
            (c.id, c.text)
            for page in self.layout.pages
            for b in page.text_blocks
            for line in b.lines
            for s in line.spans
            for c in s.characters
        ]
        parsed = html.document_fromstring(payload)
        if Counter(self.emitted) != Counter(expected) or "".join(parsed.find("body").itertext()) != "".join(
            text for _, text in self.emitted
        ):
            raise fail(
                "HTM_CONTENT_INTEGRITY_FAILED",
                "generating_htm",
                "Serialized candidate changed, duplicated or omitted disclosure characters",
                "Resolve reconstruction without normalizing source content",
            )
        table_chars = {
            identifier
            for page in self.layout.pages
            for table in page.tables
            for cell in table.cells
            for identifier in cell.character_ids
        }
        expected_order = []
        for page in self.layout.pages:
            lines = {line.id: line for block in page.text_blocks for line in block.lines}
            for identifier in page.reading_order.candidate_line_ids:
                expected_order.extend(
                    c.id
                    for span in lines[identifier].spans
                    for c in span.characters
                    if c.id not in table_chars
                )
        if [identifier for identifier, _ in self.emitted if identifier not in table_chars] != expected_order:
            self.diagnostic(
                "HTM_READING_ORDER_UNRESOLVED",
                "Flow layout changed the proposed disclosure reading order",
                "Resolve source semantics with accepted OOXML; do not reorder disclosure silently",
            )
            return None
        return payload


def generate_htm(
    layout: DocumentLayout,
    source_pdf: Path,
    validation_report: dict,
    output: Path,
    policy: GenerationPolicy | None = None,
    context: ProcessingContext | None = None,
) -> GenerationResult:
    policy, context = policy or GenerationPolicy(), context or ProcessingContext()
    context.check()
    # Revalidate even frozen records: model_copy and nested dictionaries can bypass construction.
    layout = DocumentLayout.model_validate(layout.model_dump())
    proof = _gate(source_pdf, validation_report)
    if (
        not layout.reconstruction_eligible
        or layout.validation_report_sha256 != proof
        or layout.source_pdf_sha256 != sha256(source_pdf)
    ):
        raise fail(
            "HTM_LAYOUT_GATE_REQUIRED",
            "generating_htm",
            "HTM requires an eligible layout bound to this passing PDF proof",
            "Do not reconstruct inspection models or stale/failed generated PDFs",
        )
    if (
        output.name != "candidate.htm"
        or output.exists()
        or output.is_symlink()
        or not output.parent.is_dir()
        or output.parent.is_symlink()
    ):
        raise fail(
            "HTM_OUTPUT_INVALID",
            "generating_htm",
            "Candidate output must be a new private candidate.htm file",
            "Use the current owned attempt workspace",
        )
    builder = Builder(layout, policy, context)
    builder.prepare()
    builder.diagnostic(
        "HTM_STYLE_PROFILE_PENDING",
        "Inline style scope/property approval remains pending",
        "Stage 6 must approve a versioned manual-derived profile and validate actual bytes",
        severity="warning",
        section="5.2.2.5",
    )
    builder.diagnostic(
        "HTM_FONT_METRICS_UNVERIFIED",
        "Browser font availability and baseline metrics have not been measured",
        "Stage 7 must compare actual rendered typography and all page geometry",
        severity="warning",
    )
    if any(
        ord(c) > 127
        for p in layout.pages
        for b in p.text_blocks
        for line in b.lines
        for s in line.spans
        for c in s.text
    ):
        builder.diagnostic(
            "HTM_CHARACTER_MAPPING_PENDING",
            "Unicode is preserved as numeric references but manual mapping needs validation",
            "Stage 6 must verify references without transliterating disclosure",
            severity="warning",
            section="5.2.2.6",
        )
    if builder.asset_requests:
        builder.diagnostic(
            "HTM_ASSETS_PENDING",
            "Candidate references requested graphics that have not been normalized",
            "Materialize and validate all referenced JPG/GIF graphics before preview or packaging",
            severity="warning",
            section="5.2.2.3",
        )
    payload = None
    if not any(d.severity == "error" for d in builder.diagnostics):
        payload = builder.render()
    context.check()
    if sha256(source_pdf) != layout.source_pdf_sha256:
        raise fail(
            "HTM_SOURCE_CHANGED",
            "generating_htm",
            "PDF changed during reconstruction",
            "Repeat validation on immutable source artifacts",
        )
    if payload is not None:
        temporary = output.with_suffix(".htm.part")
        try:
            with temporary.open("xb") as stream:
                os.chmod(temporary, 0o600)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            context.check()
            # Atomic exclusive publication: a concurrent creator must never be overwritten.
            os.link(temporary, output)
        finally:
            temporary.unlink(missing_ok=True)
    return GenerationResult(
        generated=payload is not None,
        candidate_filename=output.name if payload is not None else None,
        candidate_sha256=hashlib.sha256(payload).hexdigest() if payload is not None else None,
        candidate_bytes=len(payload or b""),
        source_pdf_sha256=layout.source_pdf_sha256,
        layout_sha256=hashlib.sha256(layout.model_dump_json().encode()).hexdigest(),
        pages=len(layout.pages),
        character_count=sum(p.character_count for p in layout.pages),
        content_integrity_passed=payload is not None,
        asset_requests=tuple(builder.asset_requests),
        diagnostics=tuple(builder.diagnostics),
    )
