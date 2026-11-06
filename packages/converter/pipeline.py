"""Stage 8 packages exact qualified files; unresolved earlier gates never publish output."""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from pathlib import Path

from converter.assets.normalize import normalize_assets
from converter.context import ProcessingContext
from converter.errors import ConversionFailure, fail
from converter.html_generator.generator import generate_htm
from converter.html_generator.models import GenerationPolicy
from converter.ooxml import sha256
from converter.packaging.engine import create_package
from converter.packaging.models import PackagingPolicy
from converter.packaging.naming import prepare_filing_name
from converter.pdf_analysis.extract import analyze_pdf, write_layout
from converter.pdf_analysis.policy import AnalysisPolicy
from converter.pdf_export.provider import PDFProvider
from converter.pdf_export.validation import PDFValidationPolicy, validate_pdf
from converter.revisions.accept import accept_revisions, compare_accepted_content
from converter.sec_validation.models import SubmissionContext, ValidationPolicy
from converter.sec_validation.validator import validate_files
from converter.visual_validation.engine import compare_visuals
from converter.visual_validation.models import VisualPolicy


def write_report(path: Path, report: dict) -> None:
    temporary = path.with_suffix(".part")
    with temporary.open("wb") as output:
        os.chmod(temporary, 0o600)
        output.write((json.dumps(report, indent=2, ensure_ascii=True) + "\n").encode())
        output.flush()
        os.fsync(output.fileno())
    deadline = time.monotonic() + 1.0
    while True:
        try:
            temporary.replace(path)
            break
        except PermissionError as exc:
            # Windows readers/virus scanners can briefly deny delete-sharing.
            # Keep the old complete JSON until atomic replacement succeeds.
            if (
                os.name != "nt"
                or getattr(exc, "winerror", None) not in {5, 32, 33}
                or time.monotonic() >= deadline
            ):
                raise
            time.sleep(0.02)


def process_docx(
    source: Path,
    workspace: Path,
    provider: PDFProvider,
    reference_pdf: Path | None = None,
    expected_accepted_docx: Path | None = None,
    policy: PDFValidationPolicy | None = None,
    context: ProcessingContext | None = None,
    analysis_policy: AnalysisPolicy | None = None,
    generation_policy: GenerationPolicy | None = None,
    sec_policy: ValidationPolicy | None = None,
    submission: SubmissionContext | None = None,
    visual_policy: VisualPolicy | None = None,
    original_filename: str | None = None,
    packaging_policy: PackagingPolicy | None = None,
) -> dict:
    context = context or ProcessingContext()
    workspace = workspace.resolve()
    workspace.mkdir(mode=0o700, parents=True, exist_ok=False)
    report = {
        "schema_version": 1,
        "stage": 8,
        "original_filename": original_filename if original_filename is not None else source.name,
        "submission_context": submission.model_dump(mode="json") if submission else None,
        "sec_policy": (sec_policy or ValidationPolicy()).model_dump(mode="json"),
        "packaging_policy": (packaging_policy or PackagingPolicy()).model_dump(mode="json"),
        "source_sha256": sha256(source),
        "status": "in_progress",
        "revision_acceptance": None,
        "accepted_reference_comparison": None,
        "pdf_validation": None,
        "layout_analysis": None,
        "html_generation": None,
        "asset_normalization": None,
        "sec_validation": None,
        "visual_validation": None,
        "packaging": None,
        "provider": None,
        "diagnostics": [],
        "final_conversion_complete": False,
    }
    try:
        context.stage("accepting_revisions")
        accepted = workspace / "accepted.docx"
        report["revision_acceptance"] = accept_revisions(source, accepted, context)
        if expected_accepted_docx:
            comparison = compare_accepted_content(accepted, expected_accepted_docx)
            report["accepted_reference_comparison"] = comparison
            if not comparison["passed"]:
                raise fail(
                    "ACCEPTED_REFERENCE_MISMATCH",
                    "accepting_revisions",
                    "Accepted DOCX content differs from the expected baseline",
                    "Resolve story/content/structure differences before PDF export",
                )
        context.stage("generating_pdf")
        result = provider.render(accepted, workspace / "renderer", context)
        report["generated_pdf_artifact"] = result.path.resolve().relative_to(workspace).as_posix()
        report["provider"] = {k: v for k, v in asdict(result).items() if k != "path"}
        context.stage("validating_pdf")
        report["pdf_validation"] = validate_pdf(
            result.path, reference_pdf, policy, workspace / "pdf-evidence", context
        )
        context.check()
        if not report["pdf_validation"]["passed"]:
            codes = [d["code"] for d in report["pdf_validation"]["diagnostics"]]
            codes.extend(code for page in report["pdf_validation"]["pages"] for code in page["codes"])
            raise fail(
                "PDF_REFERENCE_REQUIRED"
                if codes == ["PDF_REFERENCE_REQUIRED"]
                else "PDF_STRICT_VALIDATION_FAILED",
                "validating_pdf",
                "PDF did not pass configured strict validation",
                "Review all-page content, geometry, typography and visual evidence",
            )
        context.stage("analyzing_pdf")
        layout = analyze_pdf(
            result.path,
            report["pdf_validation"],
            policy=analysis_policy,
            context=context,
            rendering_provenance={
                "method": "accepted_docx_open_export",
                "original_docx_sha256": report["source_sha256"],
                "accepted_docx_sha256": sha256(accepted),
                **report["provider"],
            },
        )
        context.check()
        report["layout_analysis"] = write_layout(workspace / "layout.json", layout)
        if not layout.reconstruction_eligible:
            raise fail(
                "PDF_LAYOUT_UNRESOLVED",
                "analyzing_pdf",
                "Layout extraction has unresolved reconstruction blockers",
                "Review private layout diagnostics; do not generate HTML from this model",
            )
        context.stage("generating_htm")
        generation = generate_htm(
            layout,
            result.path,
            report["pdf_validation"],
            workspace / "candidate.htm",
            generation_policy,
            context,
        )
        report["html_generation"] = generation.model_dump(mode="json")
        if not generation.generated:
            raise fail(
                "HTM_RECONSTRUCTION_UNSUPPORTED",
                "generating_htm",
                "Source layout has unresolved HTM reconstruction incompatibilities",
                "Review generation diagnostics; do not label this output filing-ready",
            )
        context.stage("preparing_assets")
        filing = workspace / "filing"
        asset_policy = sec_policy or ValidationPolicy()
        report["asset_normalization"] = normalize_assets(
            result.path,
            workspace / "candidate.htm",
            generation,
            filing,
            context,
            max_pixels=asset_policy.max_image_pixels,
            max_bytes=asset_policy.max_asset_bytes,
            max_html_bytes=asset_policy.max_html_bytes,
            max_total_bytes=asset_policy.max_total_bytes,
            max_total_pixels=asset_policy.max_total_image_pixels,
            max_assets=asset_policy.max_assets,
        )
        context.stage("validating_sec")
        filing_htm, names = prepare_filing_name(
            filing / "candidate.htm", report["original_filename"], context, asset_policy.max_html_bytes
        )
        report["prepared_htm_filename"] = names.htm_filename
        filing_assets = tuple(filing / image["filename"] for image in report["asset_normalization"]["images"])
        compliance = validate_files(
            filing_htm,
            filing_assets,
            submission,
            sec_policy,
            context,
        )
        report["sec_validation"] = compliance.model_dump(mode="json")
        if not compliance.passed:
            raise fail(
                "SEC_VALIDATION_FAILED",
                "validating_sec",
                "Actual HTM/assets failed local rule or unresolved-permission checks",
                "Resolve report diagnostics before any visual/packaging eligibility claim",
            )
        context.stage("comparing_formatting")
        visual = compare_visuals(
            result.path,
            filing_htm,
            filing_assets,
            report["pdf_validation"],
            compliance,
            workspace / "visual",
            visual_policy,
            context,
            submission,
            sec_policy,
        )
        report["visual_validation"] = visual.model_dump(mode="json")
        if not visual.strict_passed:
            raise fail(
                "VISUAL_STRICT_VALIDATION_FAILED",
                "comparing_formatting",
                "Unexplained content, geometry or pixel discrepancies remain",
                "Inspect private visual evidence; do not package unsuccessful output",
            )
        context.stage("packaging_zip")
        package = create_package(
            report["original_filename"],
            result.path,
            filing_htm,
            filing_assets,
            report["pdf_validation"],
            compliance,
            visual,
            workspace / "package",
            submission,
            sec_policy,
            packaging_policy,
            context,
        )
        report["packaging"] = package.model_dump(mode="json")
        report["status"] = "packaged"
        report["final_conversion_complete"] = True
    except ConversionFailure as exc:
        report["status"] = (
            "blocked"
            if exc.diagnostic.code
            in {"PDF_RENDERER_UNAVAILABLE", "PDF_REFERENCE_REQUIRED", "VISUAL_BROWSER_UNAVAILABLE"}
            else "failed"
        )
        report["diagnostics"].append(exc.diagnostic.to_dict())
    except Exception:
        report["status"] = "failed"
        report["diagnostics"].append(
            {
                "code": "DOCUMENT_PROCESSING_FAILED",
                "stage": "processing",
                "description": "Document processing failed without producing validated output",
                "remediation": "Inspect the private worker environment without logging disclosure text",
            }
        )
    finally:
        try:
            report["source_unchanged"] = sha256(source) == report["source_sha256"]
        except OSError:
            report["source_unchanged"] = False
        if not report["source_unchanged"]:
            report["status"] = "failed"
            report["diagnostics"].append({"code": "SOURCE_INTEGRITY_FAILED", "stage": "processing"})
        if report["status"] != "packaged":
            report["final_conversion_complete"] = False
        write_report(workspace / "processing.json", report)
    return report
