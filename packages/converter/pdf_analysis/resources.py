"""Retain source image payloads and soft masks in private analysis storage."""

import hashlib
import os

from converter.errors import fail
from converter.layout.models import DocumentLayout, ImageResource, LayoutDiagnostic
from converter.ooxml import sha256
from converter.pdf_export.validation import PDFValidationPolicy, _open


def extract_resources(path, layout, directory, policy, context):
    layout = DocumentLayout.model_validate(layout.model_dump())
    if sha256(path) != layout.source_pdf_sha256:
        raise fail(
            "PDF_LAYOUT_SOURCE_CHANGED",
            "analyzing_pdf",
            "Image source no longer matches layout",
            "Use the unchanged source",
        )
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    total, assets, diagnostics = 0, [], list(layout.diagnostics)
    with _open(
        path,
        PDFValidationPolicy(
            require_reference=False, max_pages=policy.max_pages, max_pdf_bytes=policy.max_pdf_bytes
        ),
    ) as document:

        def capture(xref, prefix, index, dimensions):
            nonlocal total
            context.check()
            payload = document.extract_image(xref)
            if not payload or (payload["width"], payload["height"]) != dimensions:
                raise fail(
                    "PDF_IMAGE_EXTRACTION_FAILED",
                    "analyzing_pdf",
                    "Image resource dimensions or payload are unavailable",
                    "Review the unsupported source resource",
                )
            data, extension = payload["image"], payload["ext"].lower()
            if not extension.isascii() or not extension.isalnum() or not 2 <= len(extension) <= 5:
                raise fail(
                    "PDF_IMAGE_FORMAT_UNSUPPORTED",
                    "analyzing_pdf",
                    "Image resource format is unsupported",
                    "Review the native image encoding",
                )
            total += len(data)
            if not data or len(data) > policy.max_resource_bytes or total > policy.max_total_resource_bytes:
                raise fail(
                    "PDF_IMAGE_RESOURCE_LIMIT",
                    "analyzing_pdf",
                    "Extracted image bytes exceed configured limits",
                    "Review image complexity before changing budgets",
                )
            filename = f"{prefix}{index:04d}.{extension}"
            with (directory / filename).open("xb") as output:
                os.chmod(directory / filename, 0o600)
                output.write(data)
            return ImageResource(
                filename=filename,
                sha256=hashlib.sha256(data).hexdigest(),
                bytes=len(data),
                format=extension,
                width_px=payload["width"],
                height_px=payload["height"],
            )

        for index, asset in enumerate(layout.assets, 1):
            context.check()
            if asset.inline:
                diagnostics.append(
                    LayoutDiagnostic(
                        code="INLINE_IMAGE_RESOURCE_UNRESOLVED",
                        severity="error",
                        object_id=asset.id,
                        description="Inline image payload cannot yet be associated reliably with its placement",
                        remediation="Add verified inline extraction before rendering",
                    )
                )
                assets.append(asset)
                continue
            original = capture(asset.xref, "image", index, (asset.width_px, asset.height_px))
            mask = (
                capture(asset.soft_mask_xref, "mask", index, (asset.width_px, asset.height_px))
                if asset.soft_mask_xref
                else None
            )
            assets.append(asset.model_copy(update={"original": original, "mask": mask}))
    context.check()
    if sha256(path) != layout.source_pdf_sha256:
        raise fail(
            "PDF_LAYOUT_SOURCE_CHANGED",
            "analyzing_pdf",
            "PDF changed during image extraction",
            "Retry with an unchanged source",
        )
    return DocumentLayout.model_validate(
        layout.model_copy(update={"assets": tuple(assets), "diagnostics": tuple(diagnostics)}).model_dump()
    )
