"""Single-process development queue; production remains Redis/Celery."""

from __future__ import annotations

import logging
import threading
import time
from uuid import uuid4

from app.models.database import Database, jobs, outbox
from app.services.dispatch import cleanup
from app.services.jobs import JobRepository
from app.services.storage import Storage
from sqlalchemy import select, update


def next_job(database):
    with database.engine.connect() as connection:
        return connection.execute(
            select(jobs.c.id)
            .where(
                jobs.c.owner_id == "local",
                jobs.c.state == "queued",
                jobs.c.deleted_at.is_(None),
                jobs.c.expires_at > int(time.time()),
            )
            .order_by(jobs.c.created_at, jobs.c.id)
            .limit(1)
        ).scalar_one_or_none()


def process_one(settings, database):
    if settings.execution_mode != "local_dev":
        raise ValueError("Local queue is disabled")
    identifier = next_job(database)
    if identifier is None:
        return False
    from workers.tasks.admission import admit_document

    # The existing atomic claim, source validation, worker pipeline and all gates apply.
    admit_document(identifier, settings)
    with database.transaction() as connection:
        connection.execute(
            update(outbox)
            .where(
                outbox.c.job_id == identifier,
                outbox.c.job_id.in_(select(jobs.c.id).where(jobs.c.state != "queued")),
            )
            .values(sent_at=int(time.time()), locked_until=0, token=None)
        )
    return True


def run(settings, stopped):
    if settings.execution_mode != "local_dev":
        raise ValueError("Local queue is disabled")
    database = Database(settings)
    repository = JobRepository(database, settings)
    identity = "local-dev-" + str(uuid4())

    def heartbeat():
        while not stopped.is_set():
            try:
                repository.heartbeat(identity)
            except Exception:
                logging.warning("Local worker heartbeat unavailable")
            stopped.wait(settings.heartbeat_seconds)

    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        while not stopped.is_set():
            cleanup(repository, Storage(settings))
            try:
                worked = process_one(settings, database)
            except Exception:
                logging.error("Local conversion attempt interrupted; lease recovery remains active")
                worked = False
            if not worked:
                stopped.wait(1)
    finally:
        stopped.set()
        thread.join(timeout=5)
        database.engine.dispose()
