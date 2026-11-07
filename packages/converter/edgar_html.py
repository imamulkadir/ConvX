"""Authoritative-PDF EDGAR normal-flow renderer; no legacy proof promotion."""

import hashlib
import re
from pathlib import Path

from lxml import etree, html

from converter.assets.normalize import normalize_assets, publish
from converter.edgar_layers import LayerBuilder
from converter.errors import fail
from converter.html_generator.generator import Builder
from converter.html_generator.models import GenerationPolicy, GenerationResult
from converter.layout.models import DocumentLayout
from converter.ooxml import sha256
from converter.pdf_analysis.policy import AnalysisPolicy
from converter.pdf_analysis.verification import verify_layout
from converter.sec_validation.flow_profile import PROFILE
from converter.sec_validation.layer_profile import PROFILE as LAYER_PROFILE
from converter.sec_validation.models import ValidationPolicy
from converter.sec_validation.validator import validate_files


def document_name(original_filename):
    stem = Path(original_filename).stem
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", stem).lstrip("._-") or "document"
    if len(safe) > 28 or safe != stem:
        suffix = hashlib.sha256(stem.encode()).hexdigest()[:8]
        safe = safe[:19] + "-" + suffix
    return safe + ".htm"


def render_edgar(source, layout, directory, original_filename, context):
    context.check()
    layout = DocumentLayout.model_validate(layout.model_dump())
    if (
        layout.mode != "authoritative_pdf"
        or not layout.extraction_complete
        or not layout.verification
        or layout.source_pdf_sha256 != sha256(source)
    ):
        raise fail(
            "EDGAR_AUTHORITY_REQUIRED",
            "generating_htm",
            "EDGAR requires current verified authoritative PDF layout",
            "Re-analyze the unchanged source",
        )
    if directory.exists() or directory.is_symlink():
        raise ValueError("EDGAR output must be new")
    builder = Builder(layout, GenerationPolicy(), context, allow_ligature_backstep=True)
    # Do not silently discard appearances or unresolved native extraction failures.
    if any(page.annotations for page in layout.pages):
        raise fail(
            "EDGAR_ANNOTATION_UNSUPPORTED",
            "generating_htm",
            "Annotation appearances cannot be reproduced by the permitted flow renderer",
            "Flatten authorized annotations into a static source PDF",
        )
    needs_layers = any(
        v.kind == "clip"
        and not (
            len(v.items) == 1
            and v.items[0].command == "re"
            and v.items[0].rect is not None
            and all(
                abs(a - b) <= 0.05
                for a, b in zip(v.items[0].rect, page.geometry.unrotated_bounds, strict=True)
            )
        )
        for page in layout.pages
        for v in page.vectors
    )
    if needs_layers:
        builder = LayerBuilder(source, layout, context)
    if any(
        d.severity == "error" and not (needs_layers and d.code == "CLIP_ASSOCIATION_UNRESOLVED")
        for d in layout.diagnostics
    ) or any(
        d.severity == "error" and not (needs_layers and d.code == "CLIP_ASSOCIATION_UNRESOLVED")
        for p in layout.pages
        for d in p.diagnostics
    ):
        raise fail(
            "EDGAR_LAYOUT_UNRESOLVED",
            "generating_htm",
            "Source layout contains unresolved extraction errors",
            "Review layout diagnostics",
        )
    layout = verify_layout(source, layout, AnalysisPolicy.model_validate(layout.policy), context)
    builder.layout = layout
    builder.prepare()
    errors = [d for d in builder.diagnostics if d.severity == "error"]
    if errors:
        first = errors[0]
        raise fail(first.code, "generating_htm", first.description, first.remediation, page=first.page)
    payload = builder.render()
    if payload is None:
        raise fail(
            "EDGAR_READING_ORDER_UNRESOLVED",
            "generating_htm",
            "Permitted flow cannot preserve disclosure order",
            "Use Standard mode or resolve source structure",
        )
    # The revised profile deliberately excludes the legacy CSS3 box-sizing property.
    # Edit attributes only: a disclosure can itself contain a CSS-looking string.
    # A byte replacement could silently delete that legitimate source text.
    parsed = html.document_fromstring(payload)
    disclosure = "".join(parsed.find("body").itertext())
    for element in parsed.xpath("//*[@style]"):
        declarations = [
            item for item in element.get("style").split(";") if item.split(":", 1)[0].strip() != "box-sizing"
        ]
        element.set("style", ";".join(declarations))
    payload = etree.tostring(parsed, method="html", encoding="ascii", pretty_print=False)
    if "".join(html.document_fromstring(payload).find("body").itertext()) != disclosure:
        raise fail(
            "EDGAR_CONTENT_CHANGED",
            "generating_htm",
            "Formatting serialization changed disclosure",
            "Rebuild from verified source",
        )
    filename = document_name(original_filename)
    scratch = directory.parent / (directory.name + "-candidate")
    scratch.mkdir(mode=0o700, exist_ok=False)
    candidate = scratch / filename
    publish(candidate, payload)
    generation = GenerationResult(
        generated=True,
        candidate_filename=filename,
        candidate_sha256=sha256(candidate),
        candidate_bytes=len(payload),
        source_pdf_sha256=layout.source_pdf_sha256,
        layout_sha256=hashlib.sha256(layout.model_dump_json().encode()).hexdigest(),
        pages=len(layout.pages),
        character_count=sum(p.character_count for p in layout.pages),
        content_integrity_passed=True,
        asset_requests=tuple(builder.asset_requests),
        diagnostics=tuple(builder.diagnostics),
    )
    context.stage("preparing_assets")
    normalized = normalize_assets(source, candidate, generation, directory, context)
    assets = {item["filename"]: item for item in normalized["images"]}
    context.stage("validating_output")
    validation = validate_files(
        directory / filename,
        tuple(directory / n for n in assets),
        policy=ValidationPolicy(html_profile="edgar_layers_v1" if needs_layers else "edgar_flow_v1"),
        context=context,
    )
    if not validation.passed:
        first = next(d for d in validation.diagnostics if d.severity == "error")
        raise fail(
            first.code,
            "validating_output",
            first.description,
            first.remediation,
            file=first.file,
            element=first.element,
        )
    tree = html.document_fromstring((directory / filename).read_bytes())
    elements = tree.xpath("/html/body/div")
    if len(elements) != len(layout.pages):
        raise ValueError("EDGAR page count mismatch")
    pages = []
    for p, element in zip(layout.pages, elements, strict=True):
        text = "".join(element.itertext())
        bounds = p.geometry.display_bounds
        pages.append(
            {
                "page": p.page_number,
                "width_pt": bounds[2] - bounds[0],
                "height_pt": bounds[3] - bounds[1],
                "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "characters": len(text),
            }
        )
    if sha256(source) != layout.source_pdf_sha256:
        raise fail(
            "EDGAR_SOURCE_CHANGED",
            "validating_output",
            "Source changed during rendering",
            "Re-analyze source",
        )
    diagnostics = [d.model_dump() for d in builder.diagnostics]
    diagnostics.append(
        {
            "code": "EDGAR_LOCAL_PROFILE",
            "severity": "warning",
            "stage": "validating_output",
            "description": "Local EFM78 flow profile passed; browser/font differences and full submission checks remain separate. SEC acceptance is not confirmed.",
        }
    )
    return {
        "method": LAYER_PROFILE if needs_layers else PROFILE,
        **(
            {"reflow_targets": builder.reflow_targets, "clip_association": builder.clip_proof}
            if needs_layers
            else {}
        ),
        "generated": True,
        "filename": filename,
        "sha256": sha256(directory / filename),
        "bytes": (directory / filename).stat().st_size,
        "source_pdf_sha256": layout.source_pdf_sha256,
        "assets": assets,
        "pages": pages,
        "characters": sum(p["characters"] for p in pages),
        "font_embedding": False,
        "pixel_equivalence_verified": False,
        "sec_validation": validation.model_dump(mode="json"),
        "asset_normalization": normalized,
        "diagnostics": diagnostics,
    }
