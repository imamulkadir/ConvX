"""Explicit schema setup and crash-recoverable dispatch/cleanup process."""

from __future__ import annotations

import argparse
import logging
import signal
import threading

from app.core.config import Settings
from app.models.database import Database
from app.services.dispatch import cleanup, dispatch_pending
from app.services.jobs import JobRepository
from app.services.storage import Storage


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init-db", "dispatch"])
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    database = Database(settings)
    try:
        if args.command == "init-db":
            database.initialize()
            print("Schema v1 initialized; configured accounts provisioned")
            return
        from workers.worker import make_celery

        database.check_schema()
        repository, storage = JobRepository(database, settings), Storage(settings)
        celery_app = make_celery(settings)
        stopped = threading.Event()
        signal.signal(signal.SIGINT, lambda *_: stopped.set())
        signal.signal(signal.SIGTERM, lambda *_: stopped.set())
        while not stopped.is_set():
            try:
                cleanup(repository, storage)
                dispatch_pending(repository, celery_app)
            except Exception:
                logging.getLogger("convx.dispatch").error('{"event":"maintenance_failed"}')
                if args.once:
                    raise SystemExit(1) from None
            if args.once:
                break
            stopped.wait(1)
    finally:
        database.engine.dispose()


if __name__ == "__main__":
    main()
