from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CONVX_", env_file=".env", extra="ignore", hide_input_in_errors=True
    )

    environment: Literal["development", "production"] = "development"
    auth_mode: Literal["token", "local"] = "token"
    api_tokens: dict[str, SecretStr] = Field(default_factory=dict, repr=False)
    database_url: SecretStr = SecretStr("sqlite:///./var/convx.db")
    redis_url: SecretStr = SecretStr("redis://127.0.0.1:6379/0")
    storage_root: Path = Path("var/artifacts")
    auto_create_schema: bool = False
    max_upload_bytes: int = Field(default=20 * 1024 * 1024, ge=1024, le=100 * 1024 * 1024)
    max_request_bytes: int = Field(default=100 * 1024 * 1024, ge=1024, le=1024 * 1024 * 1024)
    max_batch_files: int = Field(default=10, ge=1, le=50)
    max_active_jobs: int = Field(default=20, ge=1, le=1000)
    max_owned_storage_bytes: int = Field(default=512 * 1024 * 1024, ge=1024)
    max_zip_entries: int = Field(default=2048, ge=10, le=10000)
    max_expanded_bytes: int = Field(default=128 * 1024 * 1024, ge=1024)
    max_entry_bytes: int = Field(default=16 * 1024 * 1024, ge=1024)
    max_compression_ratio: int = Field(default=200, ge=1, le=1000)
    max_xml_depth: int = Field(default=128, ge=10, le=256)
    validation_timeout_seconds: int = Field(default=20, ge=1, le=120)
    upload_timeout_seconds: int = Field(default=120, ge=1, le=600)
    retention_seconds: int = Field(default=86400, ge=60)
    lease_seconds: int = Field(default=120, ge=30, le=3600)
    max_job_attempts: int = Field(default=3, ge=1, le=10)
    dispatch_lease_seconds: int = Field(default=30, ge=5, le=300)
    max_dispatch_attempts: int = Field(default=20, ge=1, le=100)
    orphan_grace_seconds: int = Field(default=3600, ge=600)
    heartbeat_seconds: int = Field(default=10, ge=1, le=30)
    worker_stale_seconds: int = Field(default=45, ge=5, le=300)
    libreoffice_executable: Path | None = None
    processing_timeout_seconds: int = Field(default=300, ge=60, le=1800)
    renderer_timeout_seconds: int = Field(default=180, ge=15, le=900)
    renderer_memory_bytes: int = Field(default=1024 * 1024 * 1024, ge=128 * 1024 * 1024)
    max_generated_pdf_bytes: int = Field(default=64 * 1024 * 1024, ge=1024, le=256 * 1024 * 1024)
    pdf_comparison_dpi: int = Field(default=96, ge=36, le=300)
    pdf_max_pages: int = Field(default=500, ge=1, le=2000)
    pdf_require_reference: bool = True

    @model_validator(mode="after")
    def safe_configuration(self) -> Settings:
        if self.auth_mode == "token":
            values = [v.get_secret_value() for v in self.api_tokens.values()]
            if not values or any(len(v) < 32 for v in values) or len(set(values)) != len(values):
                raise ValueError("Configure distinct API tokens of at least 32 characters")
            if any(not k or len(k) > 128 for k in self.api_tokens):
                raise ValueError("Invalid owner identifier")
        if self.environment == "production":
            if self.auth_mode != "token" or self.auto_create_schema:
                raise ValueError("Production requires token access and explicit schema initialization")
            if not self.database_url.get_secret_value().startswith("postgresql+psycopg://"):
                raise ValueError("Production requires PostgreSQL")
        if not self.redis_url.get_secret_value().startswith(("redis://", "rediss://")):
            raise ValueError("A Redis broker URL is required")
        if self.max_request_bytes < self.max_upload_bytes:
            raise ValueError("Request limit must cover one upload")
        if self.worker_stale_seconds <= self.heartbeat_seconds * 2:
            raise ValueError("Worker stale interval must exceed two heartbeat intervals")
        if self.lease_seconds <= self.validation_timeout_seconds + 20:
            raise ValueError("Worker lease must exceed validation deadline plus shutdown margin")
        if self.renderer_timeout_seconds + 30 >= self.processing_timeout_seconds:
            raise ValueError("Processing deadline must cover rendering and verification")
        if self.environment == "production" and not self.pdf_require_reference:
            raise ValueError("Production requires the strict PDF reference gate")
        if self.libreoffice_executable is not None:
            if not self.libreoffice_executable.is_absolute():
                raise ValueError("LibreOffice executable must be an absolute path")
        self.storage_root = self.storage_root.resolve()
        if self.storage_root == Path(self.storage_root.anchor) or self.storage_root == Path.cwd().resolve():
            raise ValueError("Storage must be a dedicated private directory")
        return self
