"""Stage 6 normalizes graphics and validates actual files; visual/ZIP gates pending."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

from converter.assets.normalize import normalize_assets
from converter.context import ProcessingContext
from converter.errors import ConversionFailure, fail
from converter.html_generator.generator import generate_htm
from converter.html_generator.models import GenerationPolicy
from converter.ooxml import sha256
from converter.pdf_analysis.extract import analyze_pdf, write_layout
from converter.pdf_analysis.policy import AnalysisPolicy
from converter.pdf_export.provider import PDFProvider
from converter.pdf_export.validation import PDFValidationPolicy, validate_pdf
from converter.revisions.accept import accept_revisions, compare_accepted_content
from converter.sec_validation.models import SubmissionContext, ValidationPolicy
from converter.sec_validation.validator import validate_files


def write_report(path: Path, report: dict) -> None:
    temporary = path.with_suffix(".part")
    with temporary.open("wb") as output:
        os.chmod(temporary, 0o600)
        output.write((json.dumps(report, indent=2, ensure_ascii=True) + "\n").encode())
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(path)


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
) -> dict:
    context = context or ProcessingContext()
    workspace = workspace.resolve()
    workspace.mkdir(mode=0o700, parents=True, exist_ok=False)
    report = {
        "schema_version": 1,
        "stage": 6,
        "source_sha256": sha256(source),
        "status": "in_progress",
        "revision_acceptance": None,
        "accepted_reference_comparison": None,
        "pdf_validation": None,
        "layout_analysis": None,
        "html_generation": None,
        "asset_normalization": None,
        "sec_validation": None,
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
        compliance = validate_files(
            filing / "candidate.htm",
            tuple(filing / image["filename"] for image in report["asset_normalization"]["images"]),
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
        report["status"] = "sec_validated"
    except ConversionFailure as exc:
        report["status"] = (
            "blocked"
            if exc.diagnostic.code in {"PDF_RENDERER_UNAVAILABLE", "PDF_REFERENCE_REQUIRED"}
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
        write_report(workspace / "processing.json", report)
    return report
