import json
import time

from conftest import TOKEN_A, TOKEN_B, upload_one


def configure_worker(monkeypatch, settings):
    monkeypatch.setenv("CONVX_API_TOKENS", json.dumps({"alice": TOKEN_A, "bob": TOKEN_B}))
    monkeypatch.setenv("CONVX_DATABASE_URL", settings.database_url.get_secret_value())
    monkeypatch.setenv("CONVX_STORAGE_ROOT", str(settings.storage_root))


def test_real_admission_task_is_idempotent_and_never_converts(client, settings, monkeypatch):
    configure_worker(monkeypatch, settings)
    from workers.tasks.admission import admit_document

    job = upload_one(client)
    admit_document(job["id"], settings)
    admit_document(job["id"], settings)
    record = client.app.state.repository.get(job["id"], "alice")
    assert record["state"] == "blocked" and record["attempts"] == 1
    assert record["diagnostic_code"] == "PIPELINE_NOT_AVAILABLE"
    assert client.get(f"/api/v1/conversions/{job['id']}/download").status_code == 409


def test_worker_rejects_tampered_source(client, settings, monkeypatch):
    configure_worker(monkeypatch, settings)
    from workers.tasks.admission import admit_document

    job = upload_one(client)
    client.app.state.storage.source(job["id"]).write_bytes(b"changed")
    admit_document(job["id"], settings)
    assert client.app.state.repository.get(job["id"], "alice")["diagnostic_code"] == "SOURCE_INTEGRITY_FAILED"


def test_celery_serialization_and_delivery_with_memory_transport(client, settings, monkeypatch):
    configure_worker(monkeypatch, settings)
    from app.services.dispatch import dispatch_pending
    from celery.contrib.testing.worker import start_worker

    from workers.worker import celery

    job = upload_one(client)
    previous = celery.conf.broker_url
    celery.conf.broker_url = "memory://"
    try:
        with start_worker(celery, pool="solo", concurrency=1, perform_ping_check=False, shutdown_timeout=10):
            assert dispatch_pending(client.app.state.repository, celery) == 1
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                record = client.app.state.repository.get(job["id"], "alice")
                if record["state"] == "blocked":
                    break
                time.sleep(0.05)
            assert record["state"] == "blocked", record
    finally:
        celery.conf.broker_url = previous
