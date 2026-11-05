from __future__ import annotations

import hashlib

from app.core.config import Settings
from app.core.errors import Problem
from app.models.database import Database
from app.services.admission import validate_docx
from app.services.jobs import JobRepository
from app.services.storage import Storage
from sqlalchemy.exc import OperationalError

from workers.worker import celery


def admit_document(job_id: str, settings: Settings) -> None:
    database = Database(settings)
    repository = JobRepository(database, settings)
    try:
        record = repository.claim(job_id)
        if not record:
            return
        code = None
        try:
            source = Storage(settings).source(job_id)
            with source.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if digest != record["source_sha256"] or source.stat().st_size != record["source_bytes"]:
                raise Problem(422, "SOURCE_INTEGRITY_FAILED", "Stored source changed")
            validate_docx(source, settings)
        except Problem as exc:
            code = exc.code
        except (OSError, ValueError):
            code = "SOURCE_UNAVAILABLE"
        repository.finish_admission(job_id, record["attempt_id"], code)
    finally:
        database.engine.dispose()


@celery.task(
    name="convx.admit_document",
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=5,
)
def admission_task(job_id: str) -> None:
    admit_document(job_id, Settings())
