from __future__ import annotations

import json
import re
from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse, StreamingResponse

from app.core.errors import Problem, not_found
from app.schemas.jobs import BatchResponse, JobView
from app.services.admission import validate_docx
from app.services.storage import safe_filename

router = APIRouter(prefix="/api/v1/conversions")


def canonical_id(value: str) -> str:
    try:
        result = str(UUID(value))
    except ValueError as exc:
        raise not_found() from exc
    if result != value:
        raise not_found()
    return result


@router.post("", status_code=202, response_model=BatchResponse)
async def upload(request: Request):
    settings, storage, repository = (
        request.app.state.settings,
        request.app.state.storage,
        request.app.state.repository,
    )
    key = request.headers.get("idempotency-key")
    if key and not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", key):
        raise Problem(
            422, "INVALID_IDEMPOTENCY_KEY", "Use 1–128 ASCII letters, numbers, dots, underscores or hyphens"
        )
    if not request.headers.get("content-type", "").lower().startswith("multipart/form-data"):
        raise Problem(415, "MULTIPART_REQUIRED", "Use multipart/form-data with files fields")
    staged, errors, keep = [], [], False
    try:
        async with request.form(max_files=settings.max_batch_files, max_fields=0, max_part_size=1024) as form:
            uploads = list(form.multi_items())
            if not uploads or any(
                name != "files" or not isinstance(file, UploadFile) for name, file in uploads
            ):
                raise Problem(422, "FILES_REQUIRED", "Supply one or more files fields")
            for index, (_, file) in enumerate(uploads):
                job_id = str(uuid4())
                try:
                    name = safe_filename(file.filename)
                    size, digest = await storage.save(job_id, file)
                    await run_in_threadpool(validate_docx, storage.source(job_id), settings)
                    staged.append(
                        {
                            "id": job_id,
                            "original_filename": name,
                            "source_sha256": digest,
                            "source_bytes": size,
                        }
                    )
                except Problem as exc:
                    await run_in_threadpool(storage.remove, job_id)
                    # Never echo a rejected filename which may contain control characters or a path.
                    errors.append(
                        {
                            "index": index,
                            "filename": f"document-{index + 1}",
                            "code": exc.code,
                            "message": exc.message,
                        }
                    )
            if not staged:
                return JSONResponse({"jobs": [], "errors": errors, "replayed": False}, status_code=422)
            response, replayed = await run_in_threadpool(
                repository.create_batch, request.state.owner, staged, errors, key
            )
            keep = not replayed
            return response
    except HTTPException as exc:
        raise Problem(
            400, "INVALID_MULTIPART", "Multipart request is malformed or exceeds part limits"
        ) from exc
    finally:
        if not keep:
            for record in staged:
                await run_in_threadpool(storage.remove, record["id"])


@router.get("/{job_id}", response_model=JobView)
def status(job_id: str, request: Request):
    return JobView.from_record(request.app.state.repository.get(canonical_id(job_id), request.state.owner))


@router.delete("/{job_id}", status_code=202)
def cancel(job_id: str, request: Request):
    record = request.app.state.repository.cancel(canonical_id(job_id), request.state.owner)
    return {"id": record["id"], "state": record["state"], "cleanup_pending": record["cleaned_at"] is None}


@router.get("/{job_id}/validation")
def validation(job_id: str, request: Request):
    record = request.app.state.repository.get(canonical_id(job_id), request.state.owner)
    if record["state"] == "expired":
        raise Problem(410, "JOB_EXPIRED", "Job retention has expired")
    processing = None
    if record["attempt_id"] and record["state"] in {"failed", "blocked"}:
        path = request.app.state.storage.attempt(record["id"], record["attempt_id"]) / "processing.json"
        if path.is_file() and not path.is_symlink() and path.stat().st_size <= 2 * 1024 * 1024:
            try:
                candidate = json.loads(path.read_text(encoding="utf-8"))
                if candidate.get("source_sha256") == record["source_sha256"]:
                    processing = candidate
            except (OSError, ValueError):
                processing = None
    if processing:
        return {
            "id": record["id"],
            "complete": False,
            "sec_compliance_passed": bool((processing.get("sec_validation") or {}).get("strict_passed")),
            "local_sec_validation_passed": bool((processing.get("sec_validation") or {}).get("passed")),
            "fidelity_passed": False,
            "document_processing": processing,
            "diagnostics": processing["diagnostics"],
        }
    return {
        "id": record["id"],
        "complete": False,
        "sec_compliance_passed": False,
        "fidelity_passed": False,
        "diagnostics": [
            {
                "code": record["diagnostic_code"],
                "stage": record["stage"],
                "description": "This job has not completed the required conversion and validation gates",
                "remediation": "Review job state; later stages must implement and qualify the full pipeline",
            }
        ]
        if record["diagnostic_code"]
        else [],
    }


@router.post("/{job_id}/resume", status_code=202)
def resume(job_id: str, request: Request):
    request.app.state.repository.resume_processing(canonical_id(job_id), request.state.owner)
    return {"id": job_id, "state": "queued"}


@router.get("/{job_id}/preview")
@router.get("/{job_id}/download")
def artifact_unavailable(job_id: str, request: Request):
    record = request.app.state.repository.get(canonical_id(job_id), request.state.owner)
    if record["state"] == "expired":
        raise Problem(410, "JOB_EXPIRED", "Job retention has expired")
    raise Problem(409, "ARTIFACT_NOT_AVAILABLE", "No validated conversion artifact is available")


@router.get("/{job_id}/events")
def events(job_id: str, request: Request, after: int = 0):
    identifier = canonical_id(job_id)
    header = request.headers.get("last-event-id")
    if header:
        try:
            after = int(header)
        except ValueError as exc:
            raise Problem(422, "INVALID_EVENT_CURSOR", "Event cursor must be a nonnegative integer") from exc
    if after < 0 or after > 2**31 - 1:
        raise Problem(422, "INVALID_EVENT_CURSOR", "Event cursor is out of range")
    repository = request.app.state.repository
    history = repository.history(identifier, request.state.owner, after)

    def stream():
        # A bounded replay stream permits periodic reauthorization and avoids held DB transactions.
        for event in history:
            yield f"id: {event['sequence']}\nevent: progress\ndata: {json.dumps(event)}\n\n"
        yield f"event: reconnect\ndata: {json.dumps({'retry_after_seconds': 2})}\nretry: 2000\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})
