"""Optional real services, never replaced with a fake Redis/PostgreSQL server."""

import os
import time
from uuid import uuid4

import pytest
from app.models.database import Database
from app.services.jobs import JobRepository
from conftest import upload_one
from pydantic import SecretStr
from redis import Redis
from sqlalchemy import text


@pytest.mark.redis
def test_real_redis_delivery(client, settings, monkeypatch):
    url = os.environ.get("CONVX_TEST_REDIS_URL")
    if not url:
        pytest.skip("Set CONVX_TEST_REDIS_URL to a disposable real Redis instance")
    from app.services.dispatch import dispatch_pending
    from celery.contrib.testing.worker import start_worker
    from test_worker import configure_worker

    configure_worker(monkeypatch, settings)
    from workers.worker import celery

    previous_url, previous_queue = celery.conf.broker_url, celery.conf.task_default_queue
    queue = "convx-test-" + uuid4().hex
    celery.conf.broker_url = url
    celery.conf.task_default_queue = queue

    # Dispatch routes to the standard queue: temporarily isolate send_task routing below.
    class IsolatedSender:
        def send_task(self, name, args, **kwargs):
            return celery.send_task(name, args=args, queue=queue, retry=False)

    try:
        with Redis.from_url(url, socket_timeout=2) as connection:
            assert connection.ping()
        job = upload_one(client)
        with start_worker(celery, pool="solo", queues=[queue], concurrency=1, perform_ping_check=False):
            assert dispatch_pending(client.app.state.repository, IsolatedSender()) == 1
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                result = client.app.state.repository.get(job["id"], "alice")
                if result["state"] == "blocked":
                    break
                time.sleep(0.05)
            assert result["state"] == "blocked"
    finally:
        celery.conf.broker_url, celery.conf.task_default_queue = previous_url, previous_queue


@pytest.mark.postgres
def test_real_postgresql_state_and_idempotency(settings):
    url = os.environ.get("CONVX_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set CONVX_TEST_DATABASE_URL to a disposable PostgreSQL database")
    database = Database(settings.model_copy(update={"database_url": SecretStr(url)}))
    namespace = "convx_test_" + uuid4().hex
    quoted = database.engine.dialect.identifier_preparer.quote(namespace)
    original_engine = database.engine
    try:
        with original_engine.begin() as connection:
            connection.execute(text(f"CREATE SCHEMA {quoted}"))
        database.engine = original_engine.execution_options(schema_translate_map={None: namespace})
        database.initialize()
        repository = JobRepository(database, settings)
        source = {
            "id": str(uuid4()),
            "original_filename": "filing.docx",
            "source_sha256": "a" * 64,
            "source_bytes": 100,
        }
        first, replayed = repository.create_batch("alice", [source], [], "key")
        assert not replayed
        second, replayed = repository.create_batch("alice", [dict(source, id=str(uuid4()))], [], "key")
        assert replayed and first["jobs"][0]["id"] == second["jobs"][0]["id"]
        claim = repository.claim(source["id"])
        assert claim and repository.claim(source["id"]) is None
        assert repository.finish_admission(source["id"], claim["attempt_id"], None)
        assert len(repository.history(source["id"], "alice")) == 3
    finally:
        with original_engine.begin() as connection:
            connection.execute(text(f"DROP SCHEMA IF EXISTS {quoted} CASCADE"))
        original_engine.dispose()
