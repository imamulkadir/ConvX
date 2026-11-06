"""Small converter limits independent of any web framework, broker or database."""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field


class Limits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    max_upload_bytes: int = Field(default=20 * 1024 * 1024, ge=1024, le=100 * 1024 * 1024)
    max_zip_entries: int = Field(default=2048, ge=10, le=10000)
    max_expanded_bytes: int = Field(default=128 * 1024 * 1024, ge=1024, le=512 * 1024 * 1024)
    max_entry_bytes: int = Field(default=16 * 1024 * 1024, ge=1024, le=64 * 1024 * 1024)
    max_compression_ratio: int = Field(default=200, ge=1, le=1000)
    max_xml_depth: int = Field(default=128, ge=10, le=256)
    validation_timeout_seconds: int = Field(default=20, ge=1, le=120)


@dataclass
class AdmissionError(Exception):
    status: int
    code: str
    message: str
