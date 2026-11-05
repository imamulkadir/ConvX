from __future__ import annotations

from typing import Literal

from pydantic import Field

from converter.layout.models import Digest, Record


class ValidationPolicy(Record):
    max_html_bytes: int = Field(default=25 * 1024 * 1024, ge=1)
    max_asset_bytes: int = Field(default=20 * 1024 * 1024, ge=1)
    max_total_bytes: int = Field(default=100 * 1024 * 1024, ge=1)
    max_image_pixels: int = Field(default=16_000_000, ge=1)
    max_total_image_pixels: int = Field(default=64_000_000, ge=1)
    max_nodes: int = Field(default=200000, ge=1)
    max_assets: int = Field(default=1000, ge=1)
    max_depth: int = Field(default=128, ge=1)
    max_attributes: int = Field(default=32, ge=1)
    max_diagnostics: int = Field(default=300, ge=2)


class SubmissionContext(Record):
    form_type: str = Field(min_length=1, max_length=40, pattern=r"^[A-Z0-9 /-]+$")
    encoded_submission_bytes: int = Field(ge=0)
    # Caller supplies MIME-encoded whole submission size, not ZIP or this directory's size.


class ComplianceDiagnostic(Record):
    code: str
    severity: Literal["error", "warning"]
    description: str
    file: str
    element: str | None = None
    line: int | None = None
    section: str
    basis: Literal["confirmed_manual", "project_policy", "unresolved", "sec_guidance"]
    remediation: str
    occurrences: int = Field(default=1, ge=1)


class FileEvidence(Record):
    filename: str
    sha256: Digest
    bytes: int
    format: str
    width: int | None = None
    height: int | None = None


class ComplianceResult(Record):
    schema_version: Literal[1] = 1
    registry_version: Literal["efm-volume-ii-v78.2-local"] = "efm-volume-ii-v78.2-local"
    registry_sha256: Digest
    manual_sha256: Digest
    passed: bool
    strict_passed: bool
    checks_complete: bool
    submission_limits_checked: bool
    sec_acceptance_confirmed: Literal[False] = False
    visual_fidelity_passed: Literal[False] = False
    files: tuple[FileEvidence, ...]
    diagnostics: tuple[ComplianceDiagnostic, ...]
