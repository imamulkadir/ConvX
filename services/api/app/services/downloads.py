from __future__ import annotations

import json
from pathlib import PurePosixPath
from urllib.parse import quote

from converter.context import ProcessingContext
from converter.ooxml import sha256
from converter.packaging.archive import audit_archive_bytes
from converter.packaging.engine import completion_ready, verify_package_gates
from converter.packaging.models import PackageResult, PackagingPolicy
from converter.sec_validation.models import SubmissionContext, ValidationPolicy
from converter.sec_validation.validator import digest, read_bounded

from app.core.errors import Problem


def read_processing(storage, record):
    if not record.get("attempt_id"):
        return None
    try:
        path = storage.attempt(record["id"], record["attempt_id"]) / "processing.json"
        report = json.loads(read_bounded(path, 8 * 1024 * 1024))
        return (
            report
            if isinstance(report, dict) and report.get("source_sha256") == record["source_sha256"]
            else None
        )
    except (OSError, ValueError, TypeError):
        return None


def availability(storage, record):
    if record["state"] != "completed":
        return False
    report = read_processing(storage, record)
    if not report or not completion_ready(report, record):
        return False
    try:
        path = storage.attempt(record["id"], record["attempt_id"]) / "package/result.zip"
        return (
            path.is_file() and not path.is_symlink() and path.stat().st_size == report["packaging"]["bytes"]
        )
    except (OSError, ValueError):
        return False


def private_artifact(attempt, relative):
    path = PurePosixPath(relative)
    if (
        path.is_absolute()
        or not path.parts
        or any(p in {".", ".."} or "\\" in p or ":" in p for p in path.parts)
    ):
        raise ValueError("Unsafe artifact path")
    candidate = attempt
    for part in path.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError("Linked artifact path")
    if not candidate.resolve().is_relative_to(attempt.resolve()):
        raise ValueError("Artifact outside attempt")
    return candidate


def download_snapshot(storage, record):
    """Audit captured bytes, never serve a mutable filesystem path."""
    if record["state"] != "completed":
        raise Problem(409, "ARTIFACT_NOT_AVAILABLE", "No qualified package is available")
    try:
        report = read_processing(storage, record)
        if not report or not completion_ready(report, record):
            raise ValueError("Incomplete proof chain")
        package = PackageResult.model_validate(report["packaging"])
        policy = PackagingPolicy.model_validate(report["packaging_policy"])
        sec_policy = ValidationPolicy.model_validate(report["sec_policy"])
        submission = SubmissionContext.model_validate(report["submission_context"])
        attempt = storage.attempt(record["id"], record["attempt_id"])
        if sha256(storage.source(record["id"])) != record["source_sha256"]:
            raise ValueError("Changed original")
        pdf = private_artifact(attempt, report["generated_pdf_artifact"])
        htm = private_artifact(attempt, "filing/" + package.htm_filename)
        assets = tuple(
            private_artifact(attempt, "filing/" + f.filename)
            for f in package.files
            if f.filename != package.htm_filename
        )
        verify_package_gates(
            pdf,
            htm,
            assets,
            report["pdf_validation"],
            report["sec_validation"],
            report["visual_validation"],
            submission,
            sec_policy,
            ProcessingContext(timeout_seconds=60),
        )
        data = read_bounded(private_artifact(attempt, "package/result.zip"), policy.max_archive_bytes)
        if len(data) != package.bytes or digest(data) != package.sha256:
            raise ValueError("Changed archive")
        audit = audit_archive_bytes(data, package.files, submission, sec_policy, policy)
        if (
            audit.htm_filename != package.htm_filename
            or audit.sec_gate_sha256 != package.archive_sec_gate_sha256
        ):
            raise ValueError("Changed final checks")
        return data, package.download_filename
    except Problem:
        raise
    except Exception as exc:
        raise Problem(
            409, "PACKAGE_VALIDATION_FAILED", "Package or current evidence did not pass download checks"
        ) from exc


def content_disposition(filename):
    return "attachment; filename*=utf-8''" + quote(filename, safe="")
