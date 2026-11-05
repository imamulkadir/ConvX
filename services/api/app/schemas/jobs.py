from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict


class JobView(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    original_filename: str
    state: str
    stage: str
    version: int
    attempts: int
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    diagnostic_code: str | None
    download_available: bool = False

    @classmethod
    def from_record(cls, record: dict) -> JobView:
        values = dict(record)
        for name in ("created_at", "updated_at", "expires_at"):
            values[name] = datetime.fromtimestamp(values[name], UTC)
        return cls.model_validate(values)


class BatchError(BaseModel):
    index: int
    filename: str
    code: str
    message: str


class BatchResponse(BaseModel):
    jobs: list[JobView]
    errors: list[BatchError]
    replayed: bool = False
