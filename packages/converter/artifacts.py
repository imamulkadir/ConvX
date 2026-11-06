"""Revalidate existing qualified legacy artifacts without importing a web service."""

from pathlib import Path, PurePosixPath

from converter.context import ProcessingContext
from converter.ooxml import sha256
from converter.packaging.archive import audit_archive_bytes
from converter.packaging.engine import completion_ready, verify_package_gates
from converter.packaging.models import PackageResult, PackagingPolicy
from converter.sec_validation.models import SubmissionContext, ValidationPolicy
from converter.sec_validation.validator import digest, read_bounded


def private_path(root, relative):
    parts = PurePosixPath(relative).parts
    if (
        not parts
        or PurePosixPath(relative).is_absolute()
        or any(p in {".", ".."} or ":" in p or "\\" in p for p in parts)
    ):
        raise ValueError("Unsafe artifact path")
    candidate = Path(root)
    for part in parts:
        candidate /= part
        if candidate.is_symlink():
            raise ValueError("Linked artifact path")
    if not candidate.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError("Artifact outside workspace")
    return candidate


def audit_download(root, report):
    if report.get("packaging", {}).get("method") == "source-verified-mode-zip-v1":
        return audit_current_download(root, report)
    if not completion_ready(report) or sha256(root / "source.docx") != report["source_sha256"]:
        raise ValueError("Incomplete or changed conversion")
    package = PackageResult.model_validate(report["packaging"])
    policy = PackagingPolicy.model_validate(report["packaging_policy"])
    sec_policy = ValidationPolicy.model_validate(report["sec_policy"])
    submission = SubmissionContext.model_validate(report["submission_context"])
    workspace = private_path(root, report["workspace"])
    pdf = private_path(workspace, report["generated_pdf_artifact"])
    htm = private_path(workspace, "filing/" + package.htm_filename)
    assets = tuple(
        private_path(workspace, "filing/" + f.filename)
        for f in package.files
        if f.filename != package.htm_filename
    )
    context = ProcessingContext(timeout_seconds=60)
    verify_package_gates(
        pdf,
        htm,
        assets,
        report["pdf_validation"],
        report["sec_validation"],
        report["visual_validation"],
        submission,
        sec_policy,
        context,
    )
    data = read_bounded(private_path(workspace, "package/result.zip"), policy.max_archive_bytes)
    if len(data) != package.bytes or digest(data) != package.sha256:
        raise ValueError("Changed archive")
    audit = audit_archive_bytes(data, package.files, submission, sec_policy, policy, context)
    if audit.sec_gate_sha256 != package.archive_sec_gate_sha256:
        raise ValueError("Changed archived validation")
    return {"sha256": digest(data), "bytes": len(data), "filename": package.download_filename}


def audit_current_download(root, report):
    import json

    from converter.packaging.current import CurrentPackage, audit_bytes, names, object_hash, verified_payloads

    context = ProcessingContext(timeout_seconds=60)
    root = Path(root)
    request = json.loads(read_bounded(root / "request.json", 32768))
    mode, original = request.get("mode", "standard"), request["original_filename"]
    package = CurrentPackage.model_validate(report["packaging"])
    attempt = request.get("attempt", 1)
    if type(attempt) is not int or not 1 <= attempt <= 3:
        raise ValueError("Invalid attempt")
    filename, download = names(original, mode)
    source = private_path(root, "source.pdf" if original.lower().endswith(".pdf") else "source.docx")
    if (
        report.get("workflow") != "simplification-refactor"
        or report.get("stage") != 7
        or report.get("status") != "packaged"
        or report.get("final_conversion_complete") is not True
        or report.get("source_unchanged") is not True
        or report.get("input_preparation_complete") is not True
        or report.get("mode") != mode
        or report.get("original_filename") != original
        or report.get("workspace") != f"attempt{attempt:03d}"
        or (root / "cancelled").exists()
        or package.mode != mode
        or package.original_filename != original
        or package.document_filename != filename
        or package.download_filename != download
        or sha256(source) != report["source_sha256"]
    ):
        raise ValueError("Incomplete, changed or inconsistent current conversion")
    workspace = private_path(root, report["workspace"])
    pdf = private_path(workspace, report["generated_pdf_artifact"])
    generation, visual = report["html_generation"], report[mode + "_visual_validation"]
    if (
        package.generation_sha256 != object_hash(generation)
        or package.visual_sha256 != object_hash(visual)
        or package.source_pdf_sha256 != report["pdf_input"]["candidate_sha256"]
        or package.source_pdf_sha256 != sha256(pdf)
    ):
        raise ValueError("Changed packaging proof")
    sidecar = json.loads(
        read_bounded(private_path(workspace, mode + "-visual/comparison.json"), 8 * 1024 * 1024)
    )
    if object_hash(sidecar) != object_hash(visual):
        raise ValueError("Changed browser report")
    for name, expected in visual["artifact_sha256"].items():
        context.check()
        if (
            digest(read_bounded(private_path(workspace, mode + "-visual/" + name), 64 * 1024 * 1024))
            != expected
        ):
            raise ValueError("Changed browser evidence")
    directory = private_path(workspace, mode)
    payloads = verified_payloads(pdf, directory, mode, generation, visual, context)
    payloads = {filename: payloads.pop(generation["filename"]), **payloads}
    expected = {f.filename: {"sha256": f.sha256, "bytes": f.bytes} for f in package.files}
    if len(expected) != len(package.files) or expected != {
        n: {"sha256": digest(d), "bytes": len(d)} for n, d in payloads.items()
    }:
        raise ValueError("Changed output manifest")
    data = read_bounded(private_path(workspace, "package/result.zip"), 128 * 1024 * 1024)
    if len(data) != package.bytes or digest(data) != package.sha256:
        raise ValueError("Changed current archive")
    audit_bytes(data, mode, filename, expected, context)
    if sha256(source) != report["source_sha256"] or sha256(pdf) != package.source_pdf_sha256:
        raise ValueError("Source changed during download audit")
    return {"sha256": digest(data), "bytes": len(data), "filename": download}
