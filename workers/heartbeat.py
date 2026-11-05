from __future__ import annotations

import logging
import threading
from uuid import uuid4

from app.core.config import Settings
from app.models.database import Database
from app.services.jobs import JobRepository

_stop = threading.Event()
_thread: threading.Thread | None = None


def start() -> None:
    global _thread
    settings = Settings()
    worker_id = str(uuid4())
    _stop.clear()

    def run():
        database = Database(settings)
        repository = JobRepository(database, settings)
        try:
            while not _stop.is_set():
                try:
                    repository.heartbeat(worker_id)
                except Exception:
                    logging.getLogger("convx.worker").warning('{"event":"heartbeat_failed"}')
                _stop.wait(settings.heartbeat_seconds)
        finally:
            database.engine.dispose()

    _thread = threading.Thread(target=run, name="convx-heartbeat", daemon=True)
    _thread.start()


def stop() -> None:
    _stop.set()
    if _thread:
        _thread.join(timeout=5)
