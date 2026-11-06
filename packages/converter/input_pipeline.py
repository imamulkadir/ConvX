"""Unified DOCX/PDF preparation and authoritative analysis for the revised workflow."""

import gc
from dataclasses import asdict
from pathlib import Path

from converter.admission import validate_docx
from converter.context import ProcessingContext
from converter.edgar_html import render_edgar
from converter.errors import ConversionFailure, fail
from converter.ooxml import sha256
from converter.pdf_admission import admit_pdf
from converter.pdf_analysis.extract import analyze_authoritative_pdf, write_layout
from converter.pdf_analysis.policy import AnalysisPolicy
from converter.pdf_analysis.resources import extract_resources
from converter.pdf_export.provider import PDFProvider
from converter.pipeline import write_report
from converter.revisions.accept import accept_revisions
from converter.runtime_config import AdmissionError, Limits
from converter.standard_html import render_standard
from converter.standard_visual import verify_standard


def process_input(
    source: Path,
    workspace: Path,
    original_filename: str,
    provider: PDFProvider | None = None,
    limits: Limits | None = None,
    context: ProcessingContext | None = None,
    mode: str = "standard",
) -> dict:
    context, limits = context or ProcessingContext(), limits or Limits()
    workspace.mkdir(mode=0o700, parents=True, exist_ok=False)
    kind = Path(original_filename).suffix.lower()
    report = {
        "schema_version": 2,
        "workflow": "simplification-refactor",
        "mode": mode,
        "stage": 6,
        "original_filename": original_filename,
        "input_type": kind.lstrip("."),
        "source_sha256": None,
        "source_unchanged": False,
        "revision_acceptance": None,
        "provider": None,
        "pdf_input": None,
        "layout_analysis": None,
        "input_preparation_complete": False,
        "diagnostics": [],
        "status": "in_progress",
        "final_conversion_complete": False,
    }
    try:
        context.stage("validating")
        if mode not in {"standard", "edgar"}:
            raise AdmissionError(422, "INVALID_MODE", "Choose Standard or EDGAR mode")
        if kind not in {".docx", ".pdf"}:
            raise AdmissionError(415, "UNSUPPORTED_FILE_TYPE", "Choose a DOCX or PDF document")
        if source.is_symlink() or not source.is_file() or source.stat().st_size > limits.max_upload_bytes:
            raise AdmissionError(413, "INPUT_FILE_INVALID", "Input is unsafe or exceeds the upload limit")
        report["source_sha256"] = sha256(source)
        if kind == ".docx":
            validate_docx(source, limits)
            context.stage("accepting_revisions")
            accepted = workspace / "accepted.docx"
            report["revision_acceptance"] = accept_revisions(source, accepted, context)
            context.stage("generating_pdf")
            if provider is None:
                raise fail(
                    "PDF_RENDERER_UNAVAILABLE",
                    "generating_pdf",
                    "Local DOCX renderer is unavailable",
                    "Install free LibreOffice",
                )
            rendered = provider.render(accepted, workspace / "renderer", context)
            pdf = rendered.path
            report["provider"] = {k: v for k, v in asdict(rendered).items() if k != "path"}
            method = "accepted_docx_local_export"
            report["diagnostics"].append(
                {
                    "code": "DOCX_RENDERER_COMPATIBILITY",
                    "stage": "generating_pdf",
                    "severity": "warning",
                    "description": "Free LibreOffice export is the visual reference; Microsoft Word layout equivalence is not verified",
                }
            )
        else:
            # Private immutable attempt copy; no PDF-to-DOCX conversion or provider call.
            pdf = workspace / "input.pdf"
            with source.open("rb") as incoming, pdf.open("xb") as outgoing:
                while chunk := incoming.read(1024 * 1024):
                    context.check()
                    outgoing.write(chunk)
            method = "direct_uploaded_pdf"
        context.stage("validating_pdf")
        report["pdf_input"] = admit_pdf(pdf, context)
        if kind == ".pdf" and report["pdf_input"]["candidate_sha256"] != report["source_sha256"]:
            raise fail(
                "PDF_SOURCE_CHANGED",
                "validating_pdf",
                "Uploaded PDF changed while copying",
                "Retry with an unchanged input",
            )
        report["generated_pdf_artifact"] = pdf.resolve().relative_to(workspace.resolve()).as_posix()
        provenance = {
            "method": method,
            "source_sha256": report["source_sha256"],
            "pdf_sha256": report["pdf_input"]["candidate_sha256"],
            "visual_authority": True,
            "word_equivalence_verified": False,
        }
        if kind == ".docx":
            provenance.update(accepted_docx_sha256=sha256(accepted), **report["provider"])
        report["visual_reference"] = provenance
        context.stage("analyzing_pdf")
        layout = analyze_authoritative_pdf(pdf, provenance, context=context)
        layout = extract_resources(pdf, layout, workspace / "resources", AnalysisPolicy(), context)
        report["layout_analysis"] = write_layout(workspace / "layout.json", layout)
        report["input_preparation_complete"] = True
        scanned = [page.page_number for page in layout.pages if page.character_count == 0 and page.images]
        if scanned:
            report["diagnostics"].append(
                {
                    "code": "OCR_NOT_AVAILABLE",
                    "stage": "analyzing_pdf",
                    "severity": "warning",
                    "pages": scanned,
                    "description": "Image-only pages detected; OCR text has not been recovered or verified",
                }
            )
        report["status"] = "blocked"
        context.stage("generating_htm")
        if mode == "edgar":
            generation = render_edgar(pdf, layout, workspace / "edgar", original_filename, context)
            report["sec_validation"] = generation["sec_validation"]
        else:
            generation = render_standard(
                pdf, layout, workspace / "resources", workspace / "standard", original_filename, context
            )
        report["html_generation"] = generation
        report["diagnostics"].extend(generation["diagnostics"])
        # The source-bound model is persisted; Chromium does not need its glyph
        # objects. Release them before starting another bounded native process.
        del layout
        gc.collect()
        context.stage("comparing_formatting")
        visual = verify_standard(pdf, workspace / mode, generation, workspace / (mode + "-visual"), context)
        report[mode + "_visual_validation"] = visual
        report["diagnostics"].extend(visual["diagnostics"])
        report["diagnostics"].append(
            {
                "code": "PACKAGING_ENGINE_PENDING",
                "stage": "packaging_zip",
                "severity": "error",
                "description": "HTML and browser checks completed; downloadable ZIP packaging is pending Stage 7",
            }
        )
    except AdmissionError as exc:
        report["status"] = "failed"
        report["diagnostics"].append(
            {"code": exc.code, "stage": "validating", "severity": "error", "description": exc.message}
        )
    except ConversionFailure as exc:
        report["status"] = (
            "blocked"
            if exc.diagnostic.code in {"PDF_RENDERER_UNAVAILABLE", "STANDARD_BROWSER_UNAVAILABLE", "EDGAR_BROWSER_UNAVAILABLE"}
            else "failed"
        )
        report["diagnostics"].append({**exc.diagnostic.to_dict(), "severity": "error"})
    except Exception:
        report["status"] = "failed"
        report["diagnostics"].append(
            {
                "code": "DOCUMENT_PROCESSING_FAILED",
                "stage": "processing",
                "severity": "error",
                "description": "Document could not be safely prepared, analyzed or rendered",
            }
        )
    finally:
        try:
            report["source_unchanged"] = (
                report["source_sha256"] is not None and sha256(source) == report["source_sha256"]
            )
        except OSError:
            report["source_unchanged"] = False
        if not report["source_unchanged"]:
            report["status"] = "failed"
            report["input_preparation_complete"] = False
            report["diagnostics"].append(
                {
                    "code": "SOURCE_INTEGRITY_FAILED",
                    "severity": "error",
                    "stage": "processing",
                    "description": "Original input integrity could not be verified",
                }
            )
        write_report(workspace / "processing.json", report)
    return report
