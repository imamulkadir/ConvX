"""Bounded structural admission for authoritative generated or uploaded PDFs."""

from pathlib import Path

from converter.context import ProcessingContext
from converter.errors import fail
from converter.ooxml import sha256
from converter.pdf_export.validation import PDFValidationPolicy, _open


def admit_pdf(path: Path, context: ProcessingContext, max_bytes=64 * 1024 * 1024) -> dict:
    context.check()
    if path.is_symlink() or not path.is_file() or path.stat().st_size > max_bytes:
        raise fail(
            "PDF_INVALID",
            "validating_pdf",
            "PDF file is unsafe or exceeds its size limit",
            "Upload a bounded regular PDF",
        )
    with path.open("rb") as stream:
        if not stream.read(8).startswith(b"%PDF-"):
            raise fail(
                "PDF_SIGNATURE_INVALID",
                "validating_pdf",
                "File does not have a PDF signature",
                "Choose a real PDF document",
            )
    digest = sha256(path)
    pages = []
    policy = PDFValidationPolicy(require_reference=False, max_pdf_bytes=max_bytes)
    with _open(path, policy) as document:
        if document.is_repaired:
            raise fail(
                "PDF_REPAIR_REQUIRED",
                "validating_pdf",
                "PDF requires structural repair",
                "Re-save the PDF in a trusted document application",
            )
        for xref in range(1, document.xref_length()):
            context.check()
            keys = set(document.xref_get_keys(xref))
            actions = {document.xref_get_key(xref, key) for key in ("S", "A/S")}
            chained = (
                document.xref_get_key(xref, "S")[0] == "name"
                and document.xref_get_key(xref, "Next")[0] != "null"
            ) or any(
                document.xref_get_key(xref, key)[0] != "null"
                for key in ("A/Next", "AcroForm/XFA", "Names/JavaScript")
            )
            if (
                keys & {"XFA", "RichMedia", "RichMediaSettings"}
                or chained
                or actions
                & {
                    ("name", "/Launch"),
                    ("name", "/JavaScript"),
                    ("name", "/SubmitForm"),
                    ("name", "/ImportData"),
                    ("name", "/GoToR"),
                    ("name", "/GoToE"),
                    ("name", "/Rendition"),
                    ("name", "/Movie"),
                    ("name", "/Sound"),
                }
            ):
                raise fail(
                    "PDF_ACTIVE_CONTENT",
                    "validating_pdf",
                    "PDF contains unsupported active content",
                    "Export a static PDF without actions or interactive embedded content",
                )
        for index, page in enumerate(document):
            context.check()
            rect = page.rect
            if (
                min(rect.width, rect.height) <= 0
                or max(rect.width, rect.height) > policy.max_page_dimension_pt
                or rect.width * rect.height * (policy.dpi / 72) ** 2 > policy.max_render_pixels
            ):
                raise fail(
                    "PDF_PAGE_LIMIT",
                    "validating_pdf",
                    "PDF page geometry exceeds safe limits",
                    "Use supported bounded page dimensions",
                    page=index + 1,
                )
            pages.append(
                {
                    "page": index + 1,
                    "width_pt": rect.width,
                    "height_pt": rect.height,
                    "rotation": page.rotation,
                }
            )
    if sha256(path) != digest:
        raise fail(
            "PDF_SOURCE_CHANGED",
            "validating_pdf",
            "PDF changed during admission",
            "Retry with an unchanged source",
        )
    return {
        "method": "authoritative-pdf-structural-admission-v1",
        "candidate_sha256": digest,
        "page_count": len(pages),
        "pages": pages,
        "structurally_valid": True,
        "reference_compared": False,
        "word_equivalence_verified": False,
    }
