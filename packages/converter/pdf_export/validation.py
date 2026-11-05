from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path

import pymupdf
from PIL import Image, ImageChops

from converter.context import ProcessingContext
from converter.errors import fail
from converter.ooxml import sha256


@dataclass(frozen=True)
class PDFValidationPolicy:
    dpi: int = 96
    max_pages: int = 500
    max_page_dimension_pt: float = 2000
    max_render_pixels: int = 16_000_000
    geometry_tolerance_pt: float = 0.01
    require_reference: bool = True
    max_pdf_bytes: int = 64 * 1024 * 1024
    max_objects: int = 100000
    max_evidence_bytes: int = 128 * 1024 * 1024

    def __post_init__(self):
        if (
            not 36 <= self.dpi <= 300
            or self.max_pages < 1
            or self.max_page_dimension_pt <= 0
            or self.max_render_pixels < 1
            or self.geometry_tolerance_pt < 0
            or self.max_pdf_bytes < 1
            or self.max_objects < 1
            or self.max_evidence_bytes < 0
        ):
            raise ValueError("Invalid PDF validation policy")


def _open(path: Path, policy: PDFValidationPolicy):
    try:
        if not path.is_file() or path.stat().st_size > policy.max_pdf_bytes:
            raise ValueError("file limit")
        document = pymupdf.open(path)
        if (
            not document.is_pdf
            or document.needs_pass
            or document.is_encrypted
            or not 1 <= document.page_count <= policy.max_pages
            or document.xref_length() > policy.max_objects
        ):
            document.close()
            raise ValueError("encrypted/invalid page count")
        if document.embfile_count():
            document.close()
            raise ValueError("embedded files")
        for number in range(1, document.xref_length()):
            keys = set(document.xref_get_keys(number))
            if keys & {"JS", "JavaScript", "OpenAction", "AA", "Launch", "RichMediaContent"}:
                document.close()
                raise ValueError("active content")
        return document
    except (ValueError, RuntimeError, pymupdf.FileDataError) as exc:
        raise fail(
            "PDF_INVALID",
            "validating_pdf",
            "PDF is invalid, encrypted, empty or unsafe",
            "Provide a valid bounded PDF without active content",
        ) from exc


def _font_counts(page) -> Counter:
    result = Counter()
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                font = re.sub(r"^[A-Z]{6}\+", "", span["font"]).lower()
                key = (font, round(span["size"], 3), span["flags"], span["color"])
                result[key] += len(span["text"])
    return result


def _render(page, dpi):
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(dpi / 72, dpi / 72), colorspace=pymupdf.csRGB, alpha=False)
    return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)


def validate_pdf(
    candidate: Path,
    reference: Path | None = None,
    policy: PDFValidationPolicy | None = None,
    evidence_directory: Path | None = None,
    context: ProcessingContext | None = None,
) -> dict:
    policy, context = policy or PDFValidationPolicy(), context or ProcessingContext()
    context.check()
    report = {
        "method": "pdf-content-geometry-font-exact-raster-v2",
        "policy": asdict(policy),
        "candidate_sha256": sha256(candidate),
        "reference_sha256": sha256(reference) if reference else None,
        "passed": False,
        "pages": [],
        "diagnostics": [],
        "reference_compared": reference is not None,
        "pymupdf_version": pymupdf.VersionBind,
        "evidence_bytes": 0,
        "evidence_truncated": False,
    }
    with _open(candidate, policy) as actual:
        baseline = _open(reference, policy) if reference else None
        try:
            report["page_count"] = actual.page_count
            report["reference_page_count"] = baseline.page_count if baseline else None
            if baseline and actual.page_count != baseline.page_count:
                report["diagnostics"].append({"code": "PDF_PAGE_COUNT_MISMATCH"})
            if not baseline and policy.require_reference:
                report["diagnostics"].append({"code": "PDF_REFERENCE_REQUIRED"})
            for index in range(max(actual.page_count, baseline.page_count if baseline else 0)):
                context.check()
                if index >= actual.page_count:
                    report["pages"].append(
                        {"page": index + 1, "passed": False, "codes": ["PDF_MISSING_PAGE"]}
                    )
                    continue
                page = actual[index]
                rect = page.rect
                if (
                    min(rect.width, rect.height) <= 0
                    or max(rect.width, rect.height) > policy.max_page_dimension_pt
                    or rect.width * rect.height * (policy.dpi / 72) ** 2 > policy.max_render_pixels
                ):
                    raise fail(
                        "PDF_PAGE_LIMIT",
                        "validating_pdf",
                        "PDF page geometry exceeds configured limits",
                        "Review page dimensions and raster limits",
                        page=index + 1,
                    )
                words = page.get_text("words", sort=True)
                record = {
                    "page": index + 1,
                    "dimensions_pt": [rect.width, rect.height],
                    "rotation": page.rotation,
                    "word_count": len(words),
                    "codes": [],
                    "passed": True,
                }
                if baseline and index < baseline.page_count:
                    expected = baseline[index]
                    expected_rect = expected.rect
                    record["geometry_match"] = (
                        all(
                            abs(a - b) <= policy.geometry_tolerance_pt
                            for a, b in zip(
                                tuple(page.mediabox) + tuple(page.cropbox),
                                tuple(expected.mediabox) + tuple(expected.cropbox),
                                strict=True,
                            )
                        )
                        and page.rotation == expected.rotation
                    )
                    expected_words = expected.get_text("words", sort=True)
                    record["text_match"] = [w[4] for w in words] == [w[4] for w in expected_words]
                    record["word_content_match"] = Counter(w[4] for w in words) == Counter(
                        w[4] for w in expected_words
                    )
                    record["word_geometry_discrepancies"] = (
                        sum(
                            any(
                                abs(a - b) > policy.geometry_tolerance_pt
                                for a, b in zip(w[:4], e[:4], strict=True)
                            )
                            for w, e in zip(words, expected_words, strict=True)
                        )
                        if record["text_match"]
                        else None
                    )
                    actual_fonts, expected_fonts = _font_counts(page), _font_counts(expected)
                    record["fonts_match"] = actual_fonts == expected_fonts
                    record["font_signatures"] = {
                        "actual": [list(key) + [count] for key, count in sorted(actual_fonts.items())],
                        "reference": [list(key) + [count] for key, count in sorted(expected_fonts.items())],
                    }
                    for field, code in (
                        ("geometry_match", "PDF_PAGE_GEOMETRY_MISMATCH"),
                        ("fonts_match", "PDF_FONT_MISMATCH"),
                    ):
                        if not record[field]:
                            record["codes"].append(code)
                    if not record["text_match"]:
                        record["codes"].append(
                            "PDF_READING_ORDER_MISMATCH"
                            if record["word_content_match"]
                            else "PDF_CONTENT_MISMATCH"
                        )
                    if record["word_geometry_discrepancies"]:
                        record["codes"].append("PDF_TEXT_POSITION_MISMATCH")
                    # Reference pages are bounded too before native rasterization.
                    if (
                        max(expected_rect.width, expected_rect.height) > policy.max_page_dimension_pt
                        or expected_rect.width * expected_rect.height * (policy.dpi / 72) ** 2
                        > policy.max_render_pixels
                    ):
                        raise fail(
                            "PDF_PAGE_LIMIT",
                            "validating_pdf",
                            "Reference page exceeds raster limits",
                            "Review the reference page",
                            page=index + 1,
                        )
                    image_a, image_b = _render(page, policy.dpi), _render(expected, policy.dpi)
                    if image_a.size == image_b.size:
                        difference = ImageChops.difference(image_a, image_b)
                        r, g, b = difference.split()
                        mask = ImageChops.lighter(ImageChops.lighter(r, g), b)
                        differing = image_a.width * image_a.height - mask.histogram()[0]
                        record["different_pixels"] = differing
                        record["pixel_difference_fraction"] = differing / (image_a.width * image_a.height)
                        record["raster_match"] = differing == 0
                    else:
                        difference = None
                        record.update(
                            raster_match=False, different_pixels=None, pixel_difference_fraction=None
                        )
                    if not record["raster_match"]:
                        record["codes"].append("PDF_VISUAL_MISMATCH")
                        if evidence_directory:
                            evidence_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
                            for label, image in (
                                ("actual", image_a),
                                ("reference", image_b),
                                ("difference", difference),
                            ):
                                if image is None or report["evidence_truncated"]:
                                    continue
                                with BytesIO() as buffer:
                                    image.save(buffer, format="PNG")
                                    if report["evidence_bytes"] + buffer.tell() > policy.max_evidence_bytes:
                                        report["evidence_truncated"] = True
                                        continue
                                    (evidence_directory / f"page{index + 1:03d}-{label}.png").write_bytes(
                                        buffer.getvalue()
                                    )
                                    report["evidence_bytes"] += buffer.tell()
                elif baseline:
                    record["codes"].append("PDF_EXTRA_PAGE")
                record["passed"] = not record["codes"]
                report["pages"].append(record)
            if not any(page.get("word_count", 0) for page in report["pages"]):
                report["diagnostics"].append({"code": "PDF_NO_SELECTABLE_TEXT"})
            report["passed"] = not report["diagnostics"] and all(p["passed"] for p in report["pages"])
            return report
        finally:
            if baseline:
                baseline.close()
