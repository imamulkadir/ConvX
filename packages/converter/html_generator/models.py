from __future__ import annotations

from typing import Literal

from pydantic import Field

from converter.layout.models import Box, Digest, Record


class GenerationPolicy(Record):
    max_characters: int = Field(default=500000, ge=1)
    max_items_per_page: int = Field(default=20000, ge=1)
    max_partition_work: int = Field(default=2000000, ge=1)
    max_html_bytes: int = Field(default=25 * 1024 * 1024, ge=1)
    max_nodes: int = Field(default=1500000, ge=1)
    max_memory_bytes: int = Field(default=768 * 1024 * 1024, ge=64 * 1024 * 1024)


class GenerationDiagnostic(Record):
    code: str
    severity: Literal["error", "warning"]
    description: str
    remediation: str
    page: int | None = None
    element: str | None = None
    section: str | None = None


class AssetRequest(Record):
    filename: str
    asset_id: str
    source_pdf_sha256: Digest
    source_xref: int
    soft_mask_xref: int | None
    placement_ids: tuple[str, ...]
    purpose: Literal["pdf_image"] = "pdf_image"


class GenerationResult(Record):
    schema_version: Literal[1] = 1
    generator: Literal["convx-flow-htm-v2"] = "convx-flow-htm-v2"
    profile: Literal["efm78-stage6-candidate-v1"] = "efm78-stage6-candidate-v1"
    generated: bool
    candidate_filename: str | None
    candidate_sha256: Digest | None
    candidate_bytes: int
    source_pdf_sha256: Digest
    layout_sha256: Digest
    pages: int
    character_count: int
    content_integrity_passed: bool
    # These are deliberately not configurable success flags. Later gates must supply evidence.
    sec_compliance_passed: Literal[False] = False
    visual_fidelity_passed: Literal[False] = False
    strict_validation_passed: Literal[False] = False
    asset_requests: tuple[AssetRequest, ...]
    diagnostics: tuple[GenerationDiagnostic, ...]


class Item(Record):
    id: str
    kind: Literal["line", "table", "image", "rule", "rectangle"]
    bbox: Box
