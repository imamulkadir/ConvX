"""Stage 4 stops after gated PDF layout analysis; no HTML or ZIP implementation."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

from converter.context import ProcessingContext
from converter.errors import ConversionFailure, fail
from converter.ooxml import sha256
from converter.pdf_analysis.extract import analyze_pdf, write_layout
from converter.pdf_analysis.policy import AnalysisPolicy
from converter.pdf_export.provider import PDFProvider
from converter.pdf_export.validation import PDFValidationPolicy, validate_pdf
from converter.revisions.accept import accept_revisions, compare_accepted_content


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
) -> dict:
    context = context or ProcessingContext()
    workspace = workspace.resolve()
    workspace.mkdir(mode=0o700, parents=True, exist_ok=False)
    report = {
        "schema_version": 1,
        "stage": 4,
        "source_sha256": sha256(source),
        "status": "in_progress",
        "revision_acceptance": None,
        "accepted_reference_comparison": None,
        "pdf_validation": None,
        "layout_analysis": None,
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
        report["status"] = "layout_analyzed"
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
