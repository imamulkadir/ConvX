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
