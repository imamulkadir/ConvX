from __future__ import annotations

from pydantic import Field

from converter.layout.models import Record


class AnalysisPolicy(Record):
    max_pages: int = Field(default=500, ge=1, le=2000)
    max_pdf_bytes: int = Field(default=64 * 1024 * 1024, ge=1)
    max_characters_per_page: int = Field(default=100000, ge=1)
    max_total_characters: int = Field(default=500000, ge=1)
    max_blocks_per_page: int = Field(default=10000, ge=1)
    max_vectors_per_page: int = Field(default=10000, ge=1)
    max_primitives_per_page: int = Field(default=100000, ge=1)
    max_images_per_page: int = Field(default=1000, ge=1)
    max_image_pixels: int = Field(default=16_000_000, ge=1)
    max_page_image_pixels: int = Field(default=64_000_000, ge=1)
    max_cells_per_page: int = Field(default=2000, ge=1)
    max_membership_checks: int = Field(default=2_000_000, ge=1)
    max_layout_bytes: int = Field(default=64 * 1024 * 1024, ge=1)
    max_resource_bytes: int = Field(default=32 * 1024 * 1024, ge=1)
    max_total_resource_bytes: int = Field(default=128 * 1024 * 1024, ge=1)
    max_memory_bytes: int = Field(default=768 * 1024 * 1024, ge=64 * 1024 * 1024)
    table_snap_tolerance_pt: float = Field(default=3, ge=0.1, le=10)
    detect_borderless_candidates: bool = True
    column_gap_pt: float = Field(default=18, ge=1)
    horizontal_gap_pt: float = Field(default=3, ge=0.1)
