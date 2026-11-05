from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import psutil
import pymupdf

from converter.context import ProcessingContext
from converter.errors import ConversionFailure, fail
from converter.layout.models import (
    AnnotationRecord,
    DocumentLayout,
    LayoutDiagnostic,
    LinkRecord,
    PageGeometry,
    PageLayout,
    PaintOperation,
)
from converter.ooxml import sha256
from converter.pdf_analysis.geometry import box, contains, point, union
from converter.pdf_analysis.graphics import images, json_value, vectors
from converter.pdf_analysis.ordering import margin_regions, reading_order
from converter.pdf_analysis.policy import AnalysisPolicy
from converter.pdf_analysis.tables import extract_tables
from converter.pdf_analysis.text import extract_text
from converter.pdf_export.validation import PDFValidationPolicy, _open


class _Guard:
    def __init__(self, policy, context):
        self.policy, self.context, self.total = policy, context, 0
        self.process, self.next_memory = psutil.Process(), 0.0

    def check(self):
        self.context.check()
        now = time.monotonic()
        if now >= self.next_memory:
            self.next_memory = now + 0.1
            if self.process.memory_info().rss > self.policy.max_memory_bytes:
                raise fail(
                    "PDF_ANALYSIS_MEMORY_LIMIT",
                    "analyzing_pdf",
                    "Analysis memory budget exceeded",
                    "Review the document and bounded worker memory profile",
                )

    def characters(self, count):
        self.total += count
        if count > self.policy.max_characters_per_page or self.total > self.policy.max_total_characters:
            raise fail(
                "PDF_ANALYSIS_LIMIT",
                "analyzing_pdf",
                "Character budget exceeded",
                "Increase limits only after reviewing document complexity",
            )


def _gate(path, report):
    expected = report.get("page_count", 0)
    pages = report.get("pages", [])
    valid = (
        report.get("passed") is True
        and report.get("reference_compared") is True
        and report.get("policy", {}).get("require_reference") is True
        and report.get("reference_sha256")
        and not report.get("diagnostics")
        and expected > 0
        and len(pages) == expected
        and [p.get("page") for p in pages] == list(range(1, expected + 1))
        and all(p.get("passed") is True and not p.get("codes") for p in pages)
        and report.get("method") == "pdf-content-geometry-font-exact-raster-v2"
    )
    if not valid:
        raise fail(
            "PDF_LAYOUT_GATE_REQUIRED",
            "analyzing_pdf",
            "Layout reconstruction requires a complete passing strict PDF reference gate",
            "Resolve prior PDF validation; do not bypass failed or missing evidence",
        )
    if report.get("candidate_sha256") != sha256(path):
        raise fail(
            "PDF_LAYOUT_SOURCE_CHANGED",
            "analyzing_pdf",
            "PDF no longer matches its validated hash",
            "Revalidate the actual generated PDF before analysis",
        )
    return hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _extract(path, mode, gate_hash, policy, context, expected_pages=None, provenance=None):
    source_digest = sha256(path)
    guard = _Guard(policy, context)
    guard.check()
    font_registry, assets, pages = {}, {}, []
    safety = PDFValidationPolicy(
        max_pages=policy.max_pages, max_pdf_bytes=policy.max_pdf_bytes, require_reference=False
    )
    with _open(path, safety) as document:
        if expected_pages is not None and document.page_count != expected_pages:
            raise fail(
                "PDF_LAYOUT_SOURCE_CHANGED",
                "analyzing_pdf",
                "Validated PDF page count changed",
                "Revalidate the source PDF",
            )
        metadata = {k: v for k, v in sorted(document.metadata.items())}
        for number in range(document.page_count):
            guard.check()
            page, prefix = document[number], f"p{number + 1:04d}"
            diagnostics, seen = [], {}

            def diagnostic(
                code,
                severity,
                object_id,
                description,
                remediation,
                _seen=seen,
                _diagnostics=diagnostics,
                _page=number + 1,
            ):
                # Keep one representative object per page/code; no disclosure excerpts in diagnostics.
                if code not in _seen:
                    _seen[code] = len(_diagnostics)
                    _diagnostics.append(
                        LayoutDiagnostic(
                            code=code,
                            severity=severity,
                            page=_page,
                            object_id=object_id,
                            description=description,
                            remediation=remediation,
                        )
                    )
                else:
                    index = _seen[code]
                    previous = _diagnostics[index]
                    _diagnostics[index] = previous.model_copy(
                        update={"occurrences": previous.occurrences + 1}
                    )

            rotation = page.rotation
            displayed, to_display, from_display = (
                box(page.rect),
                tuple(page.rotation_matrix),
                tuple(page.derotation_matrix),
            )
            try:
                # Native coordinate APIs have rotation-dependent special cases. Extract uniformly at zero rotation,
                # record the original transform and restore it in memory. The source file is never saved.
                page.set_rotation(0)
                bounds = box(page.rect)
                geometry = PageGeometry(
                    media_box=box(page.mediabox),
                    crop_box=box(page.cropbox),
                    crop_offset=point(page.cropbox_position),
                    unrotated_bounds=bounds,
                    display_bounds=displayed,
                    rotation_degrees=rotation,
                    pdf_to_page_matrix=tuple(page.transformation_matrix),
                    page_to_display_matrix=to_display,
                    display_to_page_matrix=from_display,
                )
                raw_paths = page.get_drawings(extended=True)
                paths = vectors(raw_paths, prefix, policy, guard)
                paint_order = tuple(
                    PaintOperation(sequence=i, kind=item[0], bbox=box(item[1]), layer=item[2])
                    for i, item in enumerate(page.get_bboxlog(layers=True))
                )
                blocks, text_paints, character_count, character_digest = extract_text(
                    page, prefix, policy, guard, font_registry, paths, bounds, diagnostic
                )
                placements = images(page, document, prefix, policy, guard, assets, paint_order, False)
                content_boxes = [
                    span.bbox for block in blocks for line in block.lines for span in line.spans
                ] + [image.bbox for image in placements]
                nontrivial_clip = any(
                    path.kind == "clip"
                    and (path.scissor or path.bbox) is not None
                    and any(
                        not (
                            contains(path.scissor or path.bbox, (bbox[0], bbox[1]))
                            and contains(path.scissor or path.bbox, (bbox[2], bbox[3]))
                        )
                        for bbox in content_boxes
                    )
                    for path in paths
                )
                if nontrivial_clip:
                    placements = tuple(
                        image.model_copy(update={"clipping": "association_unresolved"})
                        for image in placements
                    )
                    diagnostic(
                        "CLIP_ASSOCIATION_UNRESOLVED",
                        "error",
                        prefix,
                        "Clip scopes may intersect text/images and cannot be fully associated by the current API",
                        "Resolve clipping before reconstruction; exact clip/group operations are preserved",
                    )
                tables = extract_tables(page, prefix, blocks, paths, raw_paths, policy, guard, diagnostic)
                links = tuple(
                    LinkRecord(
                        id=f"{prefix}-link{i:04d}",
                        bbox=box(link["from"]),
                        kind=int(link["kind"]),
                        uri=link.get("uri"),
                        destination_page=link["page"] + 1 if link.get("page", -1) >= 0 else None,
                        destination_point=point(link["to"]) if hasattr(link.get("to"), "x") else None,
                        named_destination=link.get("nameddest"),
                        file_target=link.get("file"),
                        xref=link.get("xref"),
                    )
                    for i, link in enumerate(page.get_links())
                )
                annotations = []
                for i, annot in enumerate(page.annots() or []):
                    annotations.append(
                        AnnotationRecord(
                            id=f"{prefix}-annotation{i:04d}",
                            xref=annot.xref,
                            kind=annot.type[1],
                            bbox=box(annot.rect),
                            properties={
                                "info": annot.info,
                                "flags": annot.flags,
                                "opacity": annot.opacity,
                                "colors": json_value(annot.colors)
                                if not isinstance(annot.colors, dict)
                                else {k: json_value(v) for k, v in annot.colors.items()},
                            },
                        )
                    )
                for i, widget in enumerate(page.widgets() or []):
                    annotations.append(
                        AnnotationRecord(
                            id=f"{prefix}-widget{i:04d}",
                            xref=widget.xref,
                            kind="widget",
                            bbox=box(widget.rect),
                            properties={
                                "field_type": widget.field_type_string,
                                "field_value": str(widget.field_value),
                            },
                        )
                    )
                if annotations:
                    diagnostic(
                        "ANNOTATION_APPEARANCE_UNRESOLVED",
                        "error",
                        prefix,
                        "Annotations or widgets need appearance/content reconstruction beyond page text extraction",
                        "Resolve or flatten authorized appearances without losing disclosure text",
                    )
                order = reading_order(blocks, policy)
                if order.ambiguous:
                    diagnostic(
                        "READING_ORDER_AMBIGUOUS",
                        "warning",
                        prefix,
                        "Overlapping native text-block boxes make semantic order uncertain",
                        "Use the preserved native/spatial orders and accepted OOXML semantics before final text generation",
                    )
                pages.append(
                    PageLayout(
                        id=prefix,
                        page_number=number + 1,
                        geometry=geometry,
                        text_blocks=blocks,
                        images=placements,
                        vectors=paths,
                        paint_order=paint_order,
                        text_paints=text_paints,
                        tables=tables,
                        links=links,
                        annotations=tuple(annotations),
                        reading_order=order,
                        observed_text_bounds=union([b.bbox for b in blocks]),
                        character_count=character_count,
                        character_sha256=character_digest,
                        diagnostics=tuple(diagnostics),
                    )
                )
            except ConversionFailure:
                raise
            except Exception as exc:
                raise fail(
                    "PDF_LAYOUT_EXTRACTION_FAILED",
                    "analyzing_pdf",
                    "PDF page could not be represented without extraction loss",
                    "Inspect private diagnostics and add support before reconstruction",
                    page=number + 1,
                ) from exc
            finally:
                page.set_rotation(rotation)
            guard.check()
    if sha256(path) != source_digest:
        raise fail(
            "PDF_LAYOUT_SOURCE_CHANGED",
            "analyzing_pdf",
            "PDF changed during extraction",
            "Revalidate an immutable generated PDF",
        )
    regions = margin_regions(pages)
    pages = [page.model_copy(update={"regions": tuple(regions[page.page_number])}) for page in pages]
    blocking = any(d.severity == "error" for page in pages for d in page.diagnostics)
    result = DocumentLayout(
        pymupdf_version=pymupdf.VersionBind,
        source_pdf_sha256=source_digest,
        mode=mode,
        validation_report_sha256=gate_hash,
        source_metadata=metadata,
        rendering_provenance=provenance
        or {"method": "pdf_input_inspection" if mode == "inspection_only" else "validated_pdf_input"},
        policy=policy.model_dump(mode="json"),
        pages=tuple(pages),
        fonts=tuple(font_registry[k] for k in sorted(font_registry)),
        assets=tuple(assets[k] for k in sorted(assets)),
        extraction_complete=True,
        reconstruction_eligible=mode == "validated_generated_pdf" and not blocking,
        diagnostics=(),
    )
    guard.check()
    return result


def analyze_pdf(
    path: Path,
    validation_report: dict,
    policy: AnalysisPolicy | None = None,
    context: ProcessingContext | None = None,
    rendering_provenance: dict | None = None,
) -> DocumentLayout:
    path, policy, context = path.resolve(), policy or AnalysisPolicy(), context or ProcessingContext()
    context.check()
    gate_hash = _gate(path, validation_report)
    return _extract(
        path,
        "validated_generated_pdf",
        gate_hash,
        policy,
        context,
        validation_report["page_count"],
        rendering_provenance,
    )


def inspect_pdf(
    path: Path, policy: AnalysisPolicy | None = None, context: ProcessingContext | None = None
) -> DocumentLayout:
    """Explicit read-only diagnostic mode; its output can never authorize HTM reconstruction."""
    return _extract(
        path.resolve(), "inspection_only", None, policy or AnalysisPolicy(), context or ProcessingContext()
    )


def write_layout(path: Path, layout: DocumentLayout, max_bytes: int | None = None) -> dict:
    limit = max_bytes if max_bytes is not None else int(layout.policy["max_layout_bytes"])
    if path.exists() or path.is_symlink():
        raise fail(
            "LAYOUT_OUTPUT_EXISTS",
            "analyzing_pdf",
            "Layout output must be a new private file",
            "Use a new attempt path",
        )
    payload = layout.model_dump_json().encode("utf-8")
    if len(payload) > limit:
        raise fail(
            "PDF_LAYOUT_OUTPUT_LIMIT",
            "analyzing_pdf",
            "Layout serialization exceeds the configured byte limit",
            "Review the analysis budget; partial output is not eligible",
        )
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    try:
        with temporary.open("xb") as output:
            os.chmod(temporary, 0o600)
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "schema_version": 1,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "source_pdf_sha256": layout.source_pdf_sha256,
        "pages": len(layout.pages),
        "characters": sum(p.character_count for p in layout.pages),
        "mode": layout.mode,
        "reconstruction_eligible": layout.reconstruction_eligible,
        "diagnostics": [d.model_dump(mode="json") for p in layout.pages for d in p.diagnostics],
    }
