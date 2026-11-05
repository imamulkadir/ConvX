import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from app.models.database import jobs, outbox
from app.services.dispatch import cleanup, dispatch_pending
from conftest import upload_one
from sqlalchemy import select, update


class RecordingBroker:
    """Broker fault injection only; no conversion is simulated."""

    def __init__(self, fail=False):
        self.fail, self.messages = fail, []

    def send_task(self, name, args, **kwargs):
        if self.fail:
            raise ConnectionError("Private broker detail")
        self.messages.append((name, args))


def test_outbox_survives_broker_outage_and_recovers(client):
    job = upload_one(client)
    repository = client.app.state.repository
    broker = RecordingBroker(fail=True)
    assert dispatch_pending(repository, broker) == 0
    assert repository.get(job["id"], "alice")["state"] == "queued"
    with repository.db.transaction() as connection:
        row = connection.execute(select(outbox)).mappings().one()
        assert row["attempts"] == 1 and row["sent_at"] is None
        connection.execute(update(outbox).values(next_attempt=0))
    broker.fail = False
    assert dispatch_pending(repository, broker) == 1
    assert dispatch_pending(repository, broker) == 0
    assert broker.messages == [("convx.admit_document", [job["id"]])]


def test_dispatch_exhaustion_is_visible(client, settings):
    settings.max_dispatch_attempts = 1
    job = upload_one(client)
    dispatch_pending(client.app.state.repository, RecordingBroker(fail=True))
    result = client.app.state.repository.get(job["id"], "alice")
    assert result["state"] == "failed" and result["diagnostic_code"] == "QUEUE_UNAVAILABLE"


def test_cancelled_job_never_dispatched(client):
    job = upload_one(client)
    repository = client.app.state.repository
    repository.cancel(job["id"], "alice")
    assert dispatch_pending(repository, RecordingBroker()) == 0


def test_concurrent_claim_and_stale_attempt_cannot_publish(client):
    job = upload_one(client)
    repository = client.app.state.repository
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _: repository.claim(job["id"]), range(4)))
    claimed = [r for r in results if r is not None]
    assert len(claimed) == 1
    first = claimed[0]
    with repository.db.transaction() as connection:
        connection.execute(update(jobs).where(jobs.c.id == job["id"]).values(lease_until=0))
    repository.maintain()
    second = repository.claim(job["id"])
    assert second and second["attempt_id"] != first["attempt_id"]
    assert not repository.finish_admission(job["id"], first["attempt_id"], None)
    assert repository.finish_admission(job["id"], second["attempt_id"], None)
    assert repository.get(job["id"], "alice")["state"] == "blocked"


def test_cancel_race_invalidates_worker_and_defers_cleanup(client):
    job = upload_one(client)
    repository, storage = client.app.state.repository, client.app.state.storage
    claimed = repository.claim(job["id"])
    repository.cancel(job["id"], "alice")
    assert not repository.finish_admission(job["id"], claimed["attempt_id"], None)
    cleanup(repository, storage)
    assert storage.source(job["id"]).exists()
    with repository.db.transaction() as connection:
        connection.execute(update(jobs).where(jobs.c.id == job["id"]).values(cleanup_after=0))
    cleanup(repository, storage)
    assert not storage.directory(job["id"]).exists()


def test_expired_worker_does_not_exceed_attempt_limit(client, settings):
    settings.max_job_attempts = 1
    job = upload_one(client)
    repository = client.app.state.repository
    repository.claim(job["id"])
    with repository.db.transaction() as connection:
        connection.execute(update(jobs).where(jobs.c.id == job["id"]).values(lease_until=0))
    repository.maintain()
    assert repository.get(job["id"], "alice")["diagnostic_code"] == "WORKER_ATTEMPTS_EXHAUSTED"


def test_state_and_events_are_atomic_and_ordered(client):
    job = upload_one(client)
    repository = client.app.state.repository
    claim = repository.claim(job["id"])
    repository.finish_admission(job["id"], claim["attempt_id"], None)
    history = repository.history(job["id"], "alice")
    assert [e["sequence"] for e in history] == [1, 2, 3]
    assert [e["state"] for e in history] == ["queued", "running", "blocked"]
    assert history[-1]["code"] == "PIPELINE_NOT_AVAILABLE"


def test_worker_heartbeat_expires(client, settings):
    repository = client.app.state.repository
    assert not repository.live_workers()
    repository.heartbeat(str(uuid4()))
    assert repository.live_workers()
    from app.models.database import heartbeats

    with repository.db.transaction() as connection:
        connection.execute(
            update(heartbeats).values(seen_at=int(time.time()) - settings.worker_stale_seconds - 1)
        )
    assert not repository.live_workers()


def test_retained_failed_sources_still_count_against_storage(client, settings):
    from conftest import docx_bytes

    settings.max_owned_storage_bytes = len(docx_bytes())
    job = upload_one(client)
    repository = client.app.state.repository
    claim = repository.claim(job["id"])
    repository.finish_admission(job["id"], claim["attempt_id"], "SOURCE_INTEGRITY_FAILED")
    response = client.post("/api/v1/conversions", files={"files": ("filing.docx", docx_bytes())})
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "STORAGE_QUOTA_EXCEEDED"


def test_expired_metadata_removed_after_artifacts(client):
    job = upload_one(client)
    repository = client.app.state.repository
    with repository.db.transaction() as connection:
        connection.execute(update(jobs).where(jobs.c.id == job["id"]).values(expires_at=0))
    cleanup(repository, client.app.state.storage)
    with repository.db.engine.connect() as connection:
        assert not connection.execute(select(jobs.c.id).where(jobs.c.id == job["id"])).all()
    assert not client.app.state.storage.directory(job["id"]).exists()
