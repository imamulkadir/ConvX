from __future__ import annotations

import hashlib
import json
import time
from uuid import uuid4

from sqlalchemy import and_, delete, func, insert, or_, select, update

from app.core.config import Settings
from app.core.errors import Problem, not_found
from app.models.database import Database, events, heartbeats, jobs, outbox, owners, submissions
from app.schemas.jobs import JobView

ACTIVE = ("queued", "running", "blocked")


class JobRepository:
    def __init__(self, database: Database, settings: Settings):
        self.db, self.settings = database, settings

    def _event(self, connection, record: dict, now: int) -> None:
        connection.execute(
            insert(events).values(
                job_id=record["id"],
                sequence=record["version"],
                state=record["state"],
                stage=record["stage"],
                code=record.get("diagnostic_code"),
                created_at=now,
            )
        )

    def _transition(self, connection, record: dict, now: int, **values) -> dict | None:
        values.update(version=record["version"] + 1, updated_at=now)
        changed = (
            connection.execute(
                update(jobs)
                .where(jobs.c.id == record["id"], jobs.c.version == record["version"])
                .values(**values)
                .returning(jobs)
            )
            .mappings()
            .first()
        )
        if changed:
            result = dict(changed)
            self._event(connection, result, now)
            return result
        return None

    def create_batch(
        self, owner: str, staged: list[dict], errors: list[dict], key: str | None
    ) -> tuple[dict, bool]:
        now = int(time.time())
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "files": [
                        {k: r[k] for k in ("original_filename", "source_sha256", "source_bytes")}
                        for r in staged
                    ],
                    "errors": errors,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        with self.db.transaction() as connection:
            # Owner row update serializes quota/idempotency decisions in PostgreSQL and SQLite.
            owner_exists = connection.execute(
                update(owners).where(owners.c.id == owner).values(touched=now)
            ).rowcount
            if not owner_exists:
                raise Problem(
                    503, "OWNER_NOT_PROVISIONED", "Initialize the configured account before uploads"
                )
            if key:
                previous = (
                    connection.execute(
                        select(submissions).where(submissions.c.owner_id == owner, submissions.c.key == key)
                    )
                    .mappings()
                    .first()
                )
                if previous:
                    if previous["expires_at"] <= now:
                        raise Problem(409, "IDEMPOTENCY_EXPIRED", "Use a new idempotency key")
                    if previous["fingerprint"] != fingerprint:
                        raise Problem(409, "IDEMPOTENCY_CONFLICT", "Key was used for different documents")
                    response = dict(previous["response"])
                    response["replayed"] = True
                    # Never replay stale downloadable state or hide deletion/expiry.
                    response["jobs"] = [
                        JobView.from_record(self._owned(connection, r["id"], owner, now)).model_dump(
                            mode="json"
                        )
                        for r in response["jobs"]
                    ]
                    return response, True
            count = connection.execute(
                select(func.count())
                .select_from(jobs)
                .where(
                    jobs.c.owner_id == owner,
                    jobs.c.state.in_(ACTIVE),
                    jobs.c.deleted_at.is_(None),
                    jobs.c.expires_at > now,
                )
            ).scalar_one()
            if count + len(staged) > self.settings.max_active_jobs:
                raise Problem(
                    429, "JOB_QUOTA_EXCEEDED", "Too many active documents; delete jobs or wait for expiry"
                )
            retained_bytes = connection.execute(
                select(func.coalesce(func.sum(jobs.c.source_bytes), 0)).where(
                    jobs.c.owner_id == owner, jobs.c.cleaned_at.is_(None)
                )
            ).scalar_one()
            if (
                retained_bytes + sum(source["source_bytes"] for source in staged)
                > self.settings.max_owned_storage_bytes
            ):
                raise Problem(429, "STORAGE_QUOTA_EXCEEDED", "Private document storage quota exceeded")
            created = []
            for source in staged:
                record = dict(
                    source,
                    owner_id=owner,
                    state="queued",
                    stage="uploaded",
                    version=1,
                    attempts=0,
                    created_at=now,
                    updated_at=now,
                    expires_at=now + self.settings.retention_seconds,
                    diagnostic_code=None,
                )
                connection.execute(insert(jobs).values(**record))
                connection.execute(
                    insert(outbox).values(job_id=record["id"], locked_until=0, next_attempt=now, attempts=0)
                )
                self._event(connection, record, now)
                created.append(JobView.from_record(record).model_dump(mode="json"))
            response = {"jobs": created, "errors": errors, "replayed": False}
            if key:
                connection.execute(
                    insert(submissions).values(
                        id=str(uuid4()),
                        owner_id=owner,
                        key=key,
                        fingerprint=fingerprint,
                        response=response,
                        expires_at=now + self.settings.retention_seconds,
                    )
                )
            return response, False

    def _owned(self, connection, job_id: str, owner: str, now: int) -> dict:
        record = (
            connection.execute(
                select(jobs).where(jobs.c.id == job_id, jobs.c.owner_id == owner, jobs.c.deleted_at.is_(None))
            )
            .mappings()
            .first()
        )
        if not record:
            raise not_found()
        result = dict(record)
        if result["expires_at"] <= now:
            result.update(state="expired", stage="expired", diagnostic_code="JOB_EXPIRED")
        return result

    def get(self, job_id: str, owner: str) -> dict:
        with self.db.engine.connect() as connection:
            return self._owned(connection, job_id, owner, int(time.time()))

    def history(self, job_id: str, owner: str, after: int = 0) -> list[dict]:
        with self.db.engine.connect() as connection:
            record = self._owned(connection, job_id, owner, int(time.time()))
            if record["state"] == "expired":
                raise Problem(410, "JOB_EXPIRED", "Job retention has expired")
            return [
                dict(r)
                for r in connection.execute(
                    select(events)
                    .where(events.c.job_id == job_id, events.c.sequence > after)
                    .order_by(events.c.sequence)
                    .limit(100)
                ).mappings()
            ]

    def cancel(self, job_id: str, owner: str) -> dict:
        now = int(time.time())
        with self.db.transaction() as connection:
            record = (
                connection.execute(select(jobs).where(jobs.c.id == job_id, jobs.c.owner_id == owner))
                .mappings()
                .first()
            )
            if not record:
                raise not_found()
            if record["deleted_at"] is not None:
                return dict(record)
            # A running reader may still hold the source; wait beyond its maximum lease.
            result = self._transition(
                connection,
                dict(record),
                now,
                state="cancelled",
                stage="cancelled",
                diagnostic_code="JOB_CANCELLED",
                deleted_at=now,
                cleanup_after=max(now, record["lease_until"] or now),
                lease_until=None,
            )
            if result is None:
                raise Problem(409, "STATE_CHANGED", "Job changed; retry the request")
            return result

    def claim(self, job_id: str) -> dict | None:
        now, attempt_id = int(time.time()), str(uuid4())
        with self.db.transaction() as connection:
            record = (
                connection.execute(
                    select(jobs).where(
                        jobs.c.id == job_id,
                        jobs.c.state == "queued",
                        jobs.c.deleted_at.is_(None),
                        jobs.c.expires_at > now,
                    )
                )
                .mappings()
                .first()
            )
            if not record:
                return None
            return self._transition(
                connection,
                dict(record),
                now,
                state="running",
                stage="validating",
                attempts=record["attempts"] + 1,
                attempt_id=attempt_id,
                lease_until=now + self.settings.lease_seconds,
            )

    def finish_admission(self, job_id: str, attempt_id: str, code: str | None) -> bool:
        now = int(time.time())
        with self.db.transaction() as connection:
            record = (
                connection.execute(
                    select(jobs).where(
                        jobs.c.id == job_id,
                        jobs.c.state == "running",
                        jobs.c.attempt_id == attempt_id,
                        jobs.c.lease_until > now,
                        jobs.c.deleted_at.is_(None),
                        jobs.c.expires_at > now,
                    )
                )
                .mappings()
                .first()
            )
            if not record:
                return False
            return (
                self._transition(
                    connection,
                    dict(record),
                    now,
                    state="failed" if code else "blocked",
                    stage="validation_failed" if code else "awaiting_conversion_engine",
                    diagnostic_code=code or "PIPELINE_NOT_AVAILABLE",
                    lease_until=None,
                )
                is not None
            )

    def renew_processing_lease(self, job_id: str, attempt_id: str) -> bool:
        now = int(time.time())
        with self.db.transaction() as connection:
            return bool(
                connection.execute(
                    update(jobs)
                    .where(
                        jobs.c.id == job_id,
                        jobs.c.attempt_id == attempt_id,
                        jobs.c.state == "running",
                        jobs.c.deleted_at.is_(None),
                        jobs.c.expires_at > now,
                        jobs.c.lease_until > now,
                    )
                    .values(lease_until=now + self.settings.lease_seconds)
                ).rowcount
            )

    def processing_stage(self, job_id: str, attempt_id: str, stage: str) -> bool:
        now = int(time.time())
        with self.db.transaction() as connection:
            record = (
                connection.execute(
                    select(jobs).where(
                        jobs.c.id == job_id,
                        jobs.c.attempt_id == attempt_id,
                        jobs.c.state == "running",
                        jobs.c.deleted_at.is_(None),
                        jobs.c.expires_at > now,
                        jobs.c.lease_until > now,
                    )
                )
                .mappings()
                .first()
            )
            if not record:
                return False
            return (
                self._transition(
                    connection, dict(record), now, stage=stage, lease_until=now + self.settings.lease_seconds
                )
                is not None
            )

    def finish_processing(self, job_id: str, attempt_id: str, report: dict) -> bool:
        now = int(time.time())
        with self.db.transaction() as connection:
            record = (
                connection.execute(
                    select(jobs).where(
                        jobs.c.id == job_id,
                        jobs.c.attempt_id == attempt_id,
                        jobs.c.state == "running",
                        jobs.c.deleted_at.is_(None),
                        jobs.c.expires_at > now,
                        jobs.c.lease_until > now,
                    )
                )
                .mappings()
                .first()
            )
            if not record:
                return False
            passed = report["status"] == "pdf_validated"
            code = (
                report["diagnostics"][0]["code"] if report["diagnostics"] else "LAYOUT_ENGINE_NOT_AVAILABLE"
            )
            return (
                self._transition(
                    connection,
                    dict(record),
                    now,
                    state="blocked" if passed or report["status"] == "blocked" else "failed",
                    stage="awaiting_pdf_analysis"
                    if passed
                    else report["diagnostics"][0].get("stage", "processing_failed"),
                    diagnostic_code=code,
                    lease_until=None,
                )
                is not None
            )

    def resume_processing(self, job_id: str, owner: str) -> bool:
        now = int(time.time())
        with self.db.transaction() as connection:
            record = self._owned(connection, job_id, owner, now)
            if record["state"] != "blocked" or record["diagnostic_code"] not in {
                "PIPELINE_NOT_AVAILABLE",
                "PDF_RENDERER_UNAVAILABLE",
                "PDF_REFERENCE_REQUIRED",
            }:
                raise Problem(409, "JOB_NOT_RESUMABLE", "This job cannot resume document processing")
            if record["attempts"] >= self.settings.max_job_attempts:
                raise Problem(409, "ATTEMPT_LIMIT", "Processing attempt limit reached")
            if (
                self._transition(
                    connection,
                    record,
                    now,
                    state="queued",
                    stage="uploaded",
                    diagnostic_code=None,
                    attempt_id=None,
                    lease_until=None,
                )
                is None
            ):
                raise Problem(409, "STATE_CHANGED", "Job changed; retry the request")
            connection.execute(
                update(outbox)
                .where(outbox.c.job_id == job_id)
                .values(sent_at=None, token=None, locked_until=0, next_attempt=now)
            )
            return True

    def heartbeat(self, worker_id: str) -> None:
        with self.db.transaction() as connection:
            # Runtime IDs are unique; UPDATE then INSERT avoids replacing other workers.
            if not connection.execute(
                update(heartbeats).where(heartbeats.c.id == worker_id).values(seen_at=int(time.time()))
            ).rowcount:
                connection.execute(
                    insert(heartbeats).values(
                        id=worker_id, seen_at=int(time.time()), capability="admission-v1"
                    )
                )

    def live_workers(self) -> bool:
        with self.db.engine.connect() as connection:
            return (
                connection.execute(
                    select(func.count())
                    .select_from(heartbeats)
                    .where(
                        heartbeats.c.seen_at > int(time.time()) - self.settings.worker_stale_seconds,
                        heartbeats.c.capability == "admission-v1",
                    )
                ).scalar_one()
                > 0
            )

    def maintain(self) -> None:
        now = int(time.time())
        with self.db.transaction() as connection:
            records = (
                connection.execute(
                    select(jobs).where(
                        or_(
                            and_(
                                jobs.c.expires_at <= now,
                                jobs.c.state != "expired",
                                jobs.c.deleted_at.is_(None),
                            ),
                            and_(jobs.c.state == "running", jobs.c.lease_until <= now),
                        )
                    )
                )
                .mappings()
                .all()
            )
            for record in records:
                row = dict(record)
                if row["expires_at"] <= now:
                    self._transition(
                        connection,
                        row,
                        now,
                        state="expired",
                        stage="expired",
                        diagnostic_code="JOB_EXPIRED",
                        cleanup_after=max(now, row["lease_until"] or now),
                        lease_until=None,
                    )
                elif row["attempts"] >= self.settings.max_job_attempts:
                    self._transition(
                        connection,
                        row,
                        now,
                        state="failed",
                        stage="failed",
                        diagnostic_code="WORKER_ATTEMPTS_EXHAUSTED",
                        lease_until=None,
                    )
                elif self._transition(
                    connection, row, now, state="queued", stage="uploaded", lease_until=None, attempt_id=None
                ):
                    connection.execute(
                        update(outbox)
                        .where(outbox.c.job_id == row["id"])
                        .values(sent_at=None, next_attempt=now, locked_until=0, token=None)
                    )
            connection.execute(delete(heartbeats).where(heartbeats.c.seen_at < now - 3600))
            connection.execute(delete(submissions).where(submissions.c.expires_at < now))

    def cleanup_candidates(self) -> list[str]:
        now = int(time.time())
        with self.db.engine.connect() as connection:
            return list(
                connection.execute(
                    select(jobs.c.id).where(jobs.c.cleanup_after <= now, jobs.c.cleaned_at.is_(None))
                ).scalars()
            )

    def mark_cleaned(self, job_id: str) -> None:
        with self.db.transaction() as connection:
            connection.execute(update(jobs).where(jobs.c.id == job_id).values(cleaned_at=int(time.time())))

    def known_ids(self) -> set[str]:
        with self.db.engine.connect() as connection:
            return set(connection.execute(select(jobs.c.id)).scalars())

    def purge_expired_metadata(self) -> None:
        now = int(time.time())
        with self.db.transaction() as connection:
            identifiers = list(
                connection.execute(
                    select(jobs.c.id)
                    .where(jobs.c.cleaned_at.is_not(None), jobs.c.expires_at <= now)
                    .limit(100)
                ).scalars()
            )
            if identifiers:
                connection.execute(delete(events).where(events.c.job_id.in_(identifiers)))
                connection.execute(delete(outbox).where(outbox.c.job_id.in_(identifiers)))
                connection.execute(delete(jobs).where(jobs.c.id.in_(identifiers)))
