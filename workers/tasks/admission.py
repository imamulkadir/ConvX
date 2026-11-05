from __future__ import annotations

import hashlib
import time

from app.core.config import Settings
from app.core.errors import Problem
from app.models.database import Database
from app.services.admission import validate_docx
from app.services.jobs import JobRepository
from app.services.storage import Storage
from converter.context import ProcessingContext
from converter.errors import fail
from converter.pdf_export.libreoffice import LibreOfficeProvider
from converter.pdf_export.validation import PDFValidationPolicy
from converter.pipeline import process_docx
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
        if code:
            repository.finish_admission(job_id, record["attempt_id"], code)
            return
        attempt_id = record["attempt_id"]
        last_renewed = 0.0

        def cancelled():
            nonlocal last_renewed
            now = time.monotonic()
            if now - last_renewed >= 1:
                if not repository.renew_processing_lease(job_id, attempt_id):
                    return True
                last_renewed = now
            return False

        def progress(stage):
            if not repository.processing_stage(job_id, attempt_id, stage):
                raise fail(
                    "PROCESSING_CANCELLED",
                    stage,
                    "Processing attempt is no longer active",
                    "Review cancellation/expiration",
                )

        storage = Storage(settings)
        context = ProcessingContext(settings.processing_timeout_seconds, cancelled, progress)
        provider = LibreOfficeProvider(
            settings.libreoffice_executable,
            settings.renderer_timeout_seconds,
            settings.renderer_memory_bytes,
            settings.max_generated_pdf_bytes,
        )
        reference = storage.directory(job_id) / "reference.pdf"
        report = process_docx(
            source,
            storage.attempt(job_id, attempt_id),
            provider,
            reference if reference.is_file() else None,
            policy=PDFValidationPolicy(
                dpi=settings.pdf_comparison_dpi,
                max_pages=settings.pdf_max_pages,
                max_pdf_bytes=settings.max_generated_pdf_bytes,
                require_reference=settings.pdf_require_reference,
            ),
            context=context,
        )
        repository.finish_processing(job_id, attempt_id, report)
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
