from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from converter.layout.models import Digest, Record


class VisualPolicy(Record):
    dpi: Literal[96, 144] = 96
    max_pages: int = Field(default=500, ge=1, le=2000)
    max_page_pixels: int = Field(default=16_000_000, ge=1)
    max_total_pixels: int = Field(default=64_000_000, ge=1)
    max_characters: int = Field(default=500000, ge=1)
    max_evidence_bytes: int = Field(default=128 * 1024 * 1024, ge=1)
    max_geometry_differences: int = Field(default=500, ge=1)
    geometry_tolerance_pt: float = Field(default=0.01, ge=0, le=0.05)
    browser_timeout_seconds: int = Field(default=120, ge=1, le=600)
    browser_memory_bytes: int = Field(default=1536 * 1024 * 1024, ge=128 * 1024 * 1024)
    max_html_bytes: int = Field(default=25 * 1024 * 1024, ge=1)
    max_asset_bytes: int = Field(default=20 * 1024 * 1024, ge=1)
    max_input_bytes: int = Field(default=100 * 1024 * 1024, ge=1)
    max_dom_nodes: int = Field(default=200000, ge=1)
    max_pdf_bytes: int = Field(default=64 * 1024 * 1024, ge=1)


class VisualDiagnostic(Record):
    code: str
    description: str
    remediation: str
    page: int | None = None
    count: int = 1


class VisualResult(Record):
    schema_version: Literal[1] = 1
    method: Literal["chromium-print-screen-geometry-pixels-v1"] = "chromium-print-screen-geometry-pixels-v1"
    mode: Literal["validated_pipeline", "inspection_only"]
    comparison_passed: bool
    strict_passed: bool
    checks_complete: bool
    source_pdf_sha256: Digest
    htm_sha256: Digest
    asset_sha256: dict[str, Digest]
    pdf_gate_sha256: Digest | None
    sec_gate_sha256: Digest | None
    policy: dict
    renderer: dict
    source_pages: int
    rendered_pages: int
    pages: tuple[dict, ...]
    evidence_bytes: int
    evidence_truncated: bool
    artifacts: tuple[str, ...]
    diagnostics: tuple[VisualDiagnostic, ...]
    safe_correction_applied: Literal[False] = False
    correction_reason: str = "No evidence-backed correction can be applied without altering disclosure or using unapproved formatting; retain exact source and fail unresolved differences"
    sec_acceptance_confirmed: Literal[False] = False

    @model_validator(mode="after")
    def gate_consistency(self):
        if self.comparison_passed and (
            not self.checks_complete
            or self.evidence_truncated
            or self.diagnostics
            or self.source_pages != self.rendered_pages
            or len(self.pages) != self.source_pages
            or not all(page.get("passed") is True for page in self.pages)
        ):
            raise ValueError("Incomplete or discrepant comparison cannot pass")
        if self.strict_passed and (
            self.mode != "validated_pipeline"
            or not self.comparison_passed
            or not self.pdf_gate_sha256
            or not self.sec_gate_sha256
        ):
            raise ValueError("Inspection or ungated comparison cannot authorize packaging")
        return self
