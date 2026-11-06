"""Independent native-page checks for the shared authoritative layout."""

import hashlib

import pymupdf

from converter.errors import fail
from converter.layout.models import DocumentLayout, LayoutVerification, PageVerification
from converter.ooxml import sha256
from converter.pdf_analysis.text import extraction_flags
from converter.pdf_export.validation import PDFValidationPolicy, _open


def verify_layout(path, layout, policy, context):
    # Revalidate references/ledgers even if the caller used model_copy(update=...).
    layout = DocumentLayout.model_validate(layout.model_dump())
    context.check()
    if sha256(path) != layout.source_pdf_sha256:
        raise fail(
            "PDF_LAYOUT_SOURCE_CHANGED",
            "analyzing_pdf",
            "PDF differs from the extracted source",
            "Analyze the unchanged PDF again",
        )
    checks = []
    font_keys = {(font.xref, font.base_font, name) for font in layout.fonts for name in font.resource_names}
    assets = {asset.id: asset for asset in layout.assets}
    with _open(
        path,
        PDFValidationPolicy(
            require_reference=False, max_pages=policy.max_pages, max_pdf_bytes=policy.max_pdf_bytes
        ),
    ) as document:
        if len(layout.pages) != document.page_count:
            raise fail(
                "PDF_LAYOUT_CONTENT_MISMATCH",
                "analyzing_pdf",
                "Extracted page count differs from PDF",
                "Do not render a partial layout",
            )
        for native, page in zip(document, layout.pages, strict=True):
            context.check()
            bounds, rotation = tuple(native.rect), native.rotation
            native.set_rotation(0)
            if any((font[0], font[3], font[4]) not in font_keys for font in native.get_fonts(full=True)):
                raise fail(
                    "PDF_LAYOUT_FONT_MISMATCH",
                    "analyzing_pdf",
                    "Native font resources are missing or changed",
                    "Retain all source font metadata",
                )
            raw = native.get_text(
                "rawdict",
                flags=extraction_flags(policy),
                clip=pymupdf.INFINITE_RECT(),
                sort=False,
            )
            text = "".join(
                char["c"]
                for block in raw["blocks"]
                if block["type"] == 0
                for line in block["lines"]
                for span in line["spans"]
                for char in span["chars"]
            )
            native_chars = [
                char
                for block in raw["blocks"]
                if block["type"] == 0
                for line in block["lines"]
                for span in line["spans"]
                for char in span["chars"]
            ]
            extracted_chars = [
                char
                for block in page.text_blocks
                for line in block.lines
                for span in line.spans
                for char in span.characters
            ]
            native_spans = [
                span
                for block in raw["blocks"]
                if block["type"] == 0
                for line in block["lines"]
                for span in line["spans"]
            ]
            extracted_spans = [
                span for block in page.text_blocks for line in block.lines for span in line.spans
            ]
            if len(native_spans) != len(extracted_spans) or any(
                actual["font"] != stored.font_name
                or actual["flags"] != stored.font_flags
                or actual["color"] != stored.color_rgb
                or abs(actual["size"] - stored.font_size_pt) > 0.01
                for actual, stored in zip(native_spans, extracted_spans, strict=True)
            ):
                raise fail(
                    "PDF_LAYOUT_FONT_MISMATCH",
                    "analyzing_pdf",
                    "Extracted typography differs from PDF",
                    "Preserve native font, size, weight and color",
                )
            if len(native_chars) != len(extracted_chars) or any(
                any(
                    abs(a - b) > 0.01
                    for a, b in zip(
                        (*actual["origin"], *actual["bbox"]), (*stored.origin, *stored.bbox), strict=True
                    )
                )
                for actual, stored in zip(native_chars, extracted_chars, strict=True)
            ):
                raise fail(
                    "PDF_LAYOUT_POSITION_MISMATCH",
                    "analyzing_pdf",
                    "Extracted glyph positions differ from native PDF",
                    "Re-extract before rendering",
                )
            image_infos = native.get_image_info(hashes=True, xrefs=True)
            if len(image_infos) != len(page.images) or any(
                int(actual.get("xref", 0)) != assets[stored.asset_id].xref
                or (actual["width"], actual["height"])
                != (assets[stored.asset_id].width_px, assets[stored.asset_id].height_px)
                or any(abs(a - b) > 0.01 for a, b in zip(actual["transform"], stored.transform, strict=True))
                for actual, stored in zip(image_infos, page.images, strict=True)
            ):
                raise fail(
                    "PDF_LAYOUT_IMAGE_MISMATCH",
                    "analyzing_pdf",
                    "Image resource or placement differs from PDF",
                    "Preserve native image transforms and source associations",
                )
            checked = PageVerification(
                page=page.page_number,
                character_sha256=hashlib.sha256(text.encode()).hexdigest(),
                characters=len(text),
                images=len(image_infos),
                vectors=len(native.get_drawings(extended=True)),
                width_pt=bounds[2] - bounds[0],
                height_pt=bounds[3] - bounds[1],
                rotation=rotation,
            )
            native.set_rotation(rotation)
            checks.append(checked)
    context.check()
    if sha256(path) != layout.source_pdf_sha256:
        raise fail(
            "PDF_LAYOUT_SOURCE_CHANGED",
            "analyzing_pdf",
            "PDF changed during verification",
            "Retry with an unchanged PDF",
        )
    verification = LayoutVerification(source_pdf_sha256=layout.source_pdf_sha256, pages=tuple(checks))
    try:
        return DocumentLayout.model_validate(
            layout.model_copy(update={"verification": verification}).model_dump()
        )
    except ValueError as exc:
        raise fail(
            "PDF_LAYOUT_CONTENT_MISMATCH",
            "analyzing_pdf",
            "Native PDF text, geometry or resource counts differ from layout",
            "Do not render incomplete extraction",
        ) from exc
