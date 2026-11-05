from __future__ import annotations

import logging
import time
from uuid import uuid4

from sqlalchemy import select, update

from app.models.database import jobs, outbox
from app.services.jobs import JobRepository
from app.services.storage import Storage

logger = logging.getLogger("convx.dispatch")


def dispatch_pending(repository: JobRepository, celery_app, limit: int = 20) -> int:
    now, dispatched = int(time.time()), 0
    db, settings = repository.db, repository.settings
    with db.engine.connect() as connection:
        candidates = list(
            connection.execute(
                select(outbox.c.job_id)
                .join(jobs)
                .where(
                    outbox.c.sent_at.is_(None),
                    outbox.c.next_attempt <= now,
                    outbox.c.locked_until <= now,
                    jobs.c.state == "queued",
                    jobs.c.deleted_at.is_(None),
                    jobs.c.expires_at > now,
                )
                .order_by(outbox.c.next_attempt)
                .limit(limit)
            ).scalars()
        )
    for job_id in candidates:
        now = int(time.time())
        token = str(uuid4())
        with db.transaction() as connection:
            claimed = connection.execute(
                update(outbox)
                .where(outbox.c.job_id == job_id, outbox.c.sent_at.is_(None), outbox.c.locked_until <= now)
                .values(
                    token=token,
                    locked_until=now + settings.dispatch_lease_seconds,
                    attempts=outbox.c.attempts + 1,
                )
                .returning(outbox.c.attempts)
            ).scalar_one_or_none()
        if claimed is None:
            continue
        try:
            celery_app.send_task("convx.admit_document", args=[job_id], queue="convx.admission", retry=False)
        except Exception:
            with db.transaction() as connection:
                still_owned = connection.execute(
                    update(outbox)
                    .where(outbox.c.job_id == job_id, outbox.c.token == token)
                    .values(locked_until=0, next_attempt=now + min(300, 2 ** min(claimed, 8)))
                ).rowcount
                if still_owned and claimed >= settings.max_dispatch_attempts:
                    row = (
                        connection.execute(select(jobs).where(jobs.c.id == job_id, jobs.c.state == "queued"))
                        .mappings()
                        .first()
                    )
                    if row:
                        repository._transition(
                            connection,
                            dict(row),
                            now,
                            state="failed",
                            stage="failed",
                            diagnostic_code="QUEUE_UNAVAILABLE",
                        )
            logger.warning('{"event":"dispatch_deferred","code":"QUEUE_UNAVAILABLE"}')
        else:
            with db.transaction() as connection:
                connection.execute(
                    update(outbox)
                    .where(outbox.c.job_id == job_id, outbox.c.token == token)
                    .values(sent_at=now, locked_until=0)
                )
            dispatched += 1
    return dispatched


def cleanup(repository: JobRepository, storage: Storage) -> int:
    repository.maintain()
    count = 0
    for job_id in repository.cleanup_candidates():
        try:
            storage.remove(job_id)
            repository.mark_cleaned(job_id)
            count += 1
        except (OSError, ValueError):
            logger.warning('{"event":"cleanup_deferred","code":"STORAGE_BUSY"}')
    repository.purge_expired_metadata()
    count += storage.cleanup_orphans(repository.known_ids(), repository.settings.orphan_grace_seconds)
    return count
