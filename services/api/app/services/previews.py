"""Owned diagnostic previews never imply conversion eligibility or serve active HTM."""

from io import BytesIO

from converter.ooxml import sha256
from converter.sec_validation.validator import digest, read_bounded
from PIL import Image
from starlette.responses import Response

from app.core.errors import Problem
from app.services.downloads import private_artifact, read_processing


def preview(storage, record, kind=None, page=1):
    if record["state"] == "expired":
        raise Problem(410, "JOB_EXPIRED", "Job retention has expired")
    if record["state"] not in {"failed", "blocked", "completed"}:
        raise Problem(409, "PREVIEW_NOT_AVAILABLE", "Preview is available after processing stops")
    try:
        report = read_processing(storage, record)
        if not report or not report.get("source_unchanged"):
            raise ValueError("No current report")
        if sha256(storage.source(record["id"])) != record["source_sha256"]:
            raise ValueError("Original changed")
        attempt = storage.attempt(record["id"], record["attempt_id"])
        proof = report.get("pdf_validation") or {}
        pages = proof.get("page_count", 0)
        if type(pages) is not int or not 0 < pages <= 2000:
            raise ValueError("No bounded generated PDF")
        pdf = private_artifact(attempt, report["generated_pdf_artifact"])
        if (
            not pdf.is_file()
            or pdf.stat().st_size > 64 * 1024 * 1024
            or sha256(pdf) != proof["candidate_sha256"]
        ):
            raise ValueError("PDF changed")
        visual = report.get("visual_validation") or {}
        artifacts = set(visual.get("artifacts", []))
        suffixes = {"htm": "screen", "overlay": "overlay", "difference": "print-diff"}
        available = {}
        for option, suffix in suffixes.items():
            available[option] = [
                n
                for n in range(1, pages + 1)
                if f"page{n:04d}.{suffix}.png" in artifacts
                and private_artifact(attempt, f"visual/page{n:04d}.{suffix}.png").is_file()
            ]
        if kind is None:
            return {
                "pages": pages,
                "pdf_available": True,
                "capture_dpi": visual.get("policy", {}).get("dpi", 96),
                "available_pages": available,
                "diagnostic_only": True,
                "conversion_eligible": False,
                "notice": "Internal diagnostic preview. Preview availability does not establish SEC compliance or visual fidelity.",
            }
        if not 1 <= page <= pages:
            raise Problem(422, "PREVIEW_PAGE_INVALID", "Page is outside this document")
        if kind == "pdf":
            data = read_bounded(pdf, 64 * 1024 * 1024)
            if not data.startswith(b"%PDF-") or digest(data) != proof["candidate_sha256"]:
                raise ValueError("Invalid PDF")
            return Response(data, media_type="application/pdf")
        if kind not in suffixes or page not in available[kind]:
            raise Problem(409, "PREVIEW_NOT_AVAILABLE", "This comparison artifact has not been generated")
        data = read_bounded(
            private_artifact(attempt, f"visual/page{page:04d}.{suffixes[kind]}.png"), 64 * 1024 * 1024
        )
        with Image.open(BytesIO(data)) as image:
            if image.format != "PNG" or image.width * image.height > 16_000_000:
                raise ValueError("Invalid preview image")
            image.verify()
        return Response(data, media_type="image/png")
    except Problem:
        raise
    except Exception as exc:
        raise Problem(409, "PREVIEW_NOT_AVAILABLE", "Current diagnostic preview is unavailable") from exc
