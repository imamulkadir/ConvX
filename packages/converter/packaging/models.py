from __future__ import annotations

from typing import Literal

from pydantic import Field

from converter.layout.models import Digest, Record
from converter.sec_validation.models import FileEvidence


class PackagingPolicy(Record):
    max_archive_bytes: int = Field(default=128 * 1024 * 1024, ge=1, le=512 * 1024 * 1024)
    max_uncompressed_bytes: int = Field(default=100 * 1024 * 1024, ge=1, le=512 * 1024 * 1024)
    max_member_bytes: int = Field(default=64 * 1024 * 1024, ge=1, le=256 * 1024 * 1024)
    max_members: int = Field(default=1001, ge=1, le=5001)


class PackageNames(Record):
    original_filename: str
    download_filename: str
    htm_filename: str


class ArchiveAudit(Record):
    schema_version: Literal[1] = 1
    passed: Literal[True] = True
    sha256: Digest
    bytes: int
    htm_filename: str
    files: tuple[FileEvidence, ...]
    sec_gate_sha256: Digest
    # An archive audit alone supplies no conversion/visual approval.
    conversion_eligible: Literal[False] = False


class PackageResult(Record):
    schema_version: Literal[1] = 1
    method: Literal["root-only-deterministic-zip-v1"] = "root-only-deterministic-zip-v1"
    validated: Literal[True] = True
    archive_filename: Literal["result.zip"] = "result.zip"
    original_filename: str
    download_filename: str
    htm_filename: str
    sha256: Digest
    bytes: int = Field(gt=0)
    files: tuple[FileEvidence, ...]
    source_pdf_sha256: Digest
    pdf_gate_sha256: Digest
    sec_gate_sha256: Digest
    visual_gate_sha256: Digest
    archive_sec_gate_sha256: Digest
    sec_acceptance_confirmed: Literal[False] = False
