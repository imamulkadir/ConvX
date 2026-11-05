from __future__ import annotations

import os
from importlib.metadata import version
from pathlib import Path

from pydantic import ValidationError

from converter.context import ProcessingContext
from converter.errors import fail
from converter.ooxml import sha256
from converter.packaging.archive import _members, _write_archive, audit_archive_bytes
from converter.packaging.models import PackageResult, PackagingPolicy
from converter.packaging.naming import package_names
from converter.pdf_analysis.extract import _gate
from converter.sec_validation.models import ComplianceResult
from converter.sec_validation.validator import digest, read_bounded, validate_files
from converter.visual_validation.engine import fonts, object_hash
from converter.visual_validation.models import VisualResult


def visual_evidence_consistent(visual):
    """Inspect deep measurements as well as high-level flags; inspection never qualifies."""
    if not (
        visual.mode == "validated_pipeline"
        and visual.strict_passed
        and visual.comparison_passed
        and visual.checks_complete
        and not visual.diagnostics
        and not visual.evidence_truncated
        and visual.source_pages > 0
        and visual.source_pages == visual.rendered_pages == len(visual.pages)
    ):
        return False
    if visual.renderer.get("policy_sha256") != object_hash(visual.policy):
        return False
    if visual.renderer.get("screen_antialias_suppression") is not False:
        return False
    for page in visual.pages:
        geometry = page.get("geometry") or {}
        if page.get("passed") is not True or not all(
            geometry.get(key) is True
            for key in (
                "content_equal",
                "glyph_segmentation_equal",
                "text_alignment_available",
                "geometry_equal",
                "dimensions_equal",
                "image_geometry_pixels_equal",
                "vector_geometry_paint_equal",
                "text_paint_equal",
            )
        ):
            return False
        for name in ("print_pixels", "screen_pixels"):
            metrics = page.get(name) or {}
            values = [
                metrics.get(k)
                for k in (
                    "raw_difference_pixels",
                    "explained_antialias_pixels",
                    "unexplained_difference_pixels",
                )
            ]
            if (
                metrics.get("size_equal") is not True
                or any(type(v) is not int or v < 0 for v in values)
                or values[2] != 0
                or values[0] != values[1] + values[2]
            ):
                return False
            if name == "screen_pixels" and values[0] != 0:
                return False
            if values[1] and not geometry.get("embedded_font_programs_equal"):
                return False
    return True


def verify_package_gates(
    source_pdf, htm, assets, pdf_report, sec_report, visual_report, submission, sec_policy, context
):
    pdf_hash = _gate(source_pdf, pdf_report)
    try:
        sec = ComplianceResult.model_validate(
            sec_report.model_dump() if isinstance(sec_report, ComplianceResult) else sec_report
        )
        visual = VisualResult.model_validate(
            visual_report.model_dump() if isinstance(visual_report, VisualResult) else visual_report
        )
    except (ValidationError, TypeError) as exc:
        raise fail(
            "PACKAGE_GATE_INVALID",
            "packaging_zip",
            "Gate records are incomplete or inconsistent",
            "Supply current complete production evidence",
        ) from exc
    fresh = validate_files(htm, tuple(assets), submission, sec_policy, context)
    sec_hash = object_hash(sec.model_dump(mode="json"))
    if not sec.strict_passed or not fresh.strict_passed or fresh.model_dump() != sec.model_dump():
        raise fail(
            "PACKAGE_SEC_GATE_REQUIRED",
            "packaging_zip",
            "Actual HTM/assets no longer match strict local SEC evidence",
            "Resolve uncertainty and revalidate immutable files",
        )
    hashes = {f.filename: f.sha256 for f in fresh.files}
    if (
        not visual_evidence_consistent(visual)
        or visual.pdf_gate_sha256 != pdf_hash
        or visual.sec_gate_sha256 != sec_hash
        or visual.source_pdf_sha256 != pdf_report["candidate_sha256"]
        or visual.htm_sha256 != hashes[htm.name]
        or visual.asset_sha256 != {p.name: hashes[p.name] for p in assets}
    ):
        raise fail(
            "PACKAGE_VISUAL_GATE_REQUIRED",
            "packaging_zip",
            "Current files do not match complete strict production visual evidence",
            "Do not package diagnostic, failed or stale comparisons",
        )
    for key, library in (
        ("playwright_version", "playwright"),
        ("numpy_version", "numpy"),
        ("pillow_version", "pillow"),
        ("pymupdf_version", "PyMuPDF"),
    ):
        if visual.renderer.get(key) != version(library):
            raise fail(
                "PACKAGE_RENDER_PROFILE_CHANGED",
                "packaging_zip",
                "Rendering dependencies changed after comparison",
                "Repeat visual validation in the current pinned environment",
            )
    if visual.renderer.get("font_environment_sha256") != fonts():
        raise fail(
            "PACKAGE_RENDER_PROFILE_CHANGED",
            "packaging_zip",
            "Font environment changed after comparison",
            "Repeat visual validation with the current installed fonts",
        )
    return fresh, visual, pdf_hash, sec_hash


def create_package(
    original_filename,
    source_pdf,
    htm,
    assets,
    pdf_report,
    sec_report,
    visual_report,
    output_root,
    submission=None,
    sec_policy=None,
    policy=None,
    context=None,
):
    context, policy = context or ProcessingContext(), policy or PackagingPolicy()
    context.check()
    names = package_names(original_filename)
    htm, output_root = Path(htm), Path(output_root)
    assets = tuple(map(Path, assets))
    if htm.name != names.htm_filename:
        raise fail(
            "PACKAGE_NAME_NOT_PREPARED",
            "packaging_zip",
            "HTM name was not finalized before its gates",
            "Prepare the compliant name before SEC/visual validation; never mutate qualified content afterward",
        )
    if output_root.exists() or output_root.is_symlink() or not output_root.parent.is_dir():
        raise fail(
            "PACKAGE_OUTPUT_INVALID",
            "packaging_zip",
            "Package output must be a new owned directory",
            "Use the current attempt package directory",
        )
    fresh, visual, pdf_hash, sec_hash = verify_package_gates(
        Path(source_pdf), htm, assets, pdf_report, sec_report, visual_report, submission, sec_policy, context
    )
    payloads = _members(htm, assets, policy, context)
    if {f.filename: f.sha256 for f in fresh.files} != {n: digest(data) for n, data in payloads.items()}:
        raise fail(
            "PACKAGE_INPUT_CHANGED",
            "packaging_zip",
            "Artifact changed after final validation",
            "Repeat validation and packaging without concurrent modification",
        )
    output_root.mkdir(mode=0o700)
    temporary = output_root / "result.part"
    destination = output_root / "result.zip"
    try:
        _write_archive(temporary, payloads, policy, context)
        audit = audit_archive_bytes(
            read_bounded(temporary, policy.max_archive_bytes),
            fresh.files,
            submission,
            sec_policy,
            policy,
            context,
        )
        context.check()
        if sha256(source_pdf) != visual.source_pdf_sha256 or any(
            sha256(htm if n == htm.name else next(p for p in assets if p.name == n)) != digest(data)
            for n, data in payloads.items()
        ):
            raise fail(
                "PACKAGE_INPUT_CHANGED",
                "packaging_zip",
                "Source changed before package publication",
                "Revalidate the immutable current attempt",
            )
        result = PackageResult(
            original_filename=names.original_filename,
            download_filename=names.download_filename,
            htm_filename=names.htm_filename,
            sha256=audit.sha256,
            bytes=audit.bytes,
            files=audit.files,
            source_pdf_sha256=visual.source_pdf_sha256,
            pdf_gate_sha256=pdf_hash,
            sec_gate_sha256=sec_hash,
            visual_gate_sha256=object_hash(visual.model_dump(mode="json")),
            archive_sec_gate_sha256=audit.sec_gate_sha256,
        )
        os.link(temporary, destination)
        return result
    finally:
        temporary.unlink(missing_ok=True)


def completion_ready(report, record=None):
    """Pure proof-chain consistency; no database transition or filesystem serving here."""
    try:
        if (
            report.get("status") != "packaged"
            or report.get("final_conversion_complete") is not True
            or report.get("source_unchanged") is not True
            or report.get("diagnostics")
        ):
            return False
        package = PackageResult.model_validate(report["packaging"])
        sec = ComplianceResult.model_validate(report["sec_validation"])
        visual = VisualResult.model_validate(report["visual_validation"])
        pdf = report["pdf_validation"]
        revisions = report["revision_acceptance"]
        names = package_names(report["original_filename"])
        if record and (
            report["source_sha256"] != record["source_sha256"]
            or report["original_filename"] != record["original_filename"]
        ):
            return False
        if (
            revisions.get("source_sha256") != report["source_sha256"]
            or revisions.get("source_unchanged") is not True
            or revisions.get("media_preserved") is not True
            or revisions.get("after", {}).get("total") != 0
        ):
            return False
        if (
            not report["layout_analysis"]["reconstruction_eligible"]
            or not report["html_generation"]["content_integrity_passed"]
            or not report["asset_normalization"]["content_integrity_passed"]
        ):
            return False
        expected = report.get("accepted_reference_comparison")
        if expected is not None and expected.get("passed") is not True:
            return False
        if (
            not pdf.get("passed")
            or not pdf.get("reference_compared")
            or not pdf.get("policy", {}).get("require_reference")
            or pdf.get("diagnostics")
            or len(pdf.get("pages", [])) != pdf.get("page_count")
            or not all(p.get("passed") is True and not p.get("codes") for p in pdf["pages"])
        ):
            return False
        if (
            not sec.strict_passed
            or not sec.checks_complete
            or any(d.severity == "error" for d in sec.diagnostics)
            or not visual_evidence_consistent(visual)
        ):
            return False
        if (package.original_filename, package.download_filename, package.htm_filename) != (
            names.original_filename,
            names.download_filename,
            names.htm_filename,
        ):
            return False
        hashes = {f.filename: f.sha256 for f in package.files}
        return (
            package.source_pdf_sha256 == pdf["candidate_sha256"] == visual.source_pdf_sha256
            and package.pdf_gate_sha256 == object_hash(pdf) == visual.pdf_gate_sha256
            and package.sec_gate_sha256 == object_hash(sec.model_dump(mode="json")) == visual.sec_gate_sha256
            and package.visual_gate_sha256 == object_hash(visual.model_dump(mode="json"))
            and visual.htm_sha256 == hashes[names.htm_filename]
            and visual.asset_sha256 == {n: h for n, h in hashes.items() if n != names.htm_filename}
            and hashes == {f.filename: f.sha256 for f in sec.files}
        )
    except (KeyError, TypeError, ValueError, AttributeError):
        return False
