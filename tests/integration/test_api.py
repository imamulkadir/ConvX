import hashlib
import json

import pytest
from app.main import create_app
from app.models.database import events, jobs, outbox
from app.services.dispatch import cleanup
from conftest import TOKEN_B, docx_bytes, upload_one
from fastapi.testclient import TestClient
from sqlalchemy import select, update


def test_auth_before_multipart_and_health(client):
    assert client.get("/api/v1/health").json() == {"status": "alive"}
    response = client.post("/api/v1/conversions", content=b"bad", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"
    assert "x-request-id" in response.headers
    assert not list(client.app.state.storage.root.iterdir())


def test_local_auth_requires_loopback(settings):
    settings = settings.model_copy(update={"auth_mode": "local"})
    with TestClient(create_app(settings), client=("192.0.2.1", 12345)) as client:
        assert client.post("/api/v1/conversions").status_code == 401


def test_batch_upload_persists_bytes_and_outbox(client, fixture_docx):
    response = client.post(
        "/api/v1/conversions",
        files=[
            ("files", ("original.docx", fixture_docx)),
            ("files", ("bad.docx", b"bad")),
            ("files", ("small.docx", docx_bytes())),
        ],
    )
    assert response.status_code == 202, response.text
    result = response.json()
    assert len(result["jobs"]) == 2
    assert result["errors"][0]["index"] == 1
    job = result["jobs"][0]
    assert job["state"] == "queued" and not job["download_available"]
    assert client.app.state.storage.source(job["id"]).read_bytes() == fixture_docx
    with client.app.state.database.engine.connect() as connection:
        row = connection.execute(select(jobs).where(jobs.c.id == job["id"])).mappings().one()
        assert row["source_sha256"] == hashlib.sha256(fixture_docx).hexdigest()
        assert len(connection.execute(select(outbox)).all()) == 2
        assert len(connection.execute(select(events)).all()) == 2


def test_ownership_on_every_route(client):
    job = upload_one(client)
    client.headers["Authorization"] = f"Bearer {TOKEN_B}"
    for suffix in ("", "/events", "/validation", "/download", "/preview"):
        assert client.get(f"/api/v1/conversions/{job['id']}{suffix}").status_code == 404
    assert client.delete(f"/api/v1/conversions/{job['id']}").status_code == 404


def test_no_artifact_or_false_pass(client):
    job = upload_one(client)
    for suffix in ("download", "preview"):
        response = client.get(f"/api/v1/conversions/{job['id']}/{suffix}")
        assert response.status_code == 409
    result = client.get(f"/api/v1/conversions/{job['id']}/validation").json()
    assert not result["complete"] and not result["sec_compliance_passed"] and not result["fidelity_passed"]


def test_polling_survives_api_restart(client, settings):
    job = upload_one(client)
    with TestClient(create_app(settings)) as second:
        second.headers.update(client.headers)
        assert second.get(f"/api/v1/conversions/{job['id']}").json()["state"] == "queued"


def test_idempotency_and_changed_payload(client):
    first = upload_one(client, headers={"Idempotency-Key": "batch-1"})
    replay = client.post(
        "/api/v1/conversions",
        files={"files": ("filing.docx", docx_bytes())},
        headers={"Idempotency-Key": "batch-1"},
    )
    assert replay.status_code == 202
    assert replay.json()["replayed"]
    assert replay.json()["jobs"][0]["id"] == first["id"]
    assert len(list(client.app.state.storage.root.iterdir())) == 1
    changed = client.post(
        "/api/v1/conversions",
        files={"files": ("other.docx", docx_bytes())},
        headers={"Idempotency-Key": "batch-1"},
    )
    assert changed.status_code == 409
    assert len(list(client.app.state.storage.root.iterdir())) == 1


def test_quota_has_no_partial_persistence(client, settings):
    settings.max_active_jobs = 1
    upload_one(client)
    response = client.post("/api/v1/conversions", files={"files": ("other.docx", docx_bytes())})
    assert response.status_code == 429
    assert len(list(client.app.state.storage.root.iterdir())) == 1


def test_cancel_revokes_then_cleans(client):
    job = upload_one(client)
    route = f"/api/v1/conversions/{job['id']}"
    assert client.delete(route).status_code == 202
    assert client.delete(route).status_code == 202
    assert client.get(route).status_code == 404
    cleanup(client.app.state.repository, client.app.state.storage)
    assert not client.app.state.storage.directory(job["id"]).exists()
    assert client.app.state.repository.claim(job["id"]) is None


def test_expiry_blocks_access_and_cleans(client):
    job = upload_one(client)
    with client.app.state.database.transaction() as connection:
        connection.execute(update(jobs).where(jobs.c.id == job["id"]).values(expires_at=0))
    assert client.get(f"/api/v1/conversions/{job['id']}").json()["state"] == "expired"
    assert client.get(f"/api/v1/conversions/{job['id']}/download").status_code == 410
    cleanup(client.app.state.repository, client.app.state.storage)
    assert not client.app.state.storage.directory(job["id"]).exists()


def test_events_replay_cursor(client):
    job = upload_one(client)
    route = f"/api/v1/conversions/{job['id']}/events"
    response = client.get(route)
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "id: 1" in response.text and "event: reconnect" in response.text
    assert "event: progress" not in client.get(route, headers={"Last-Event-ID": "1"}).text
    assert client.get(route, headers={"Last-Event-ID": "bad"}).status_code == 422


def test_request_limits_before_and_during_body(client, settings):
    response = client.post(
        "/api/v1/conversions", content=b"x", headers={"Content-Length": str(settings.max_request_bytes + 1)}
    )
    assert response.status_code == 413
    settings.max_request_bytes = 1024
    response = client.post(
        "/api/v1/conversions",
        content=iter([b"x" * 1025]),
        headers={"Content-Type": "multipart/form-data; boundary=abc"},
    )
    assert response.status_code == 413


def test_per_file_size_limit_is_enforced(client, settings):
    settings.max_upload_bytes = 1024
    response = client.post("/api/v1/conversions", files={"files": ("large.docx", b"x" * 1025)})
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "FILE_TOO_LARGE"
    assert not list(client.app.state.storage.root.iterdir())


@pytest.mark.parametrize(
    "files", [[("files", ("../bad.docx", b"bad"))], [("wrong", ("a.docx", docx_bytes()))]]
)
def test_rejected_request_leaves_no_files(client, files):
    assert client.post("/api/v1/conversions", files=files).status_code == 422
    assert not list(client.app.state.storage.root.iterdir())


def test_part_limit(client, settings):
    settings.max_batch_files = 1
    response = client.post(
        "/api/v1/conversions",
        files=[("files", ("a.docx", docx_bytes())), ("files", ("b.docx", docx_bytes()))],
    )
    assert response.status_code == 400
    assert not list(client.app.state.storage.root.iterdir())


def test_readiness_is_honest_without_broker_or_engine(client):
    response = client.get("/api/v1/readiness")
    assert response.status_code == 503
    result = response.json()
    assert not result["ready"] and not result["foundation_ready"] and not result["conversion_ready"]
    assert result["checks"]["database"] and result["checks"]["storage"]
    assert not result["checks"]["broker"] and not result["checks"]["admission_worker"]


def test_failure_response_and_logs_do_not_echo_content(client, caplog):
    response = client.post(
        "/api/v1/conversions", files={"files": ("secret-disclosure.docx", b"Confidential filing text")}
    )
    assert response.status_code == 422
    output = response.text + caplog.text
    assert "Confidential filing text" not in output and "secret-disclosure" not in output
    assert "no-store" in response.headers["cache-control"]


def test_batch_response_contains_no_internal_storage_keys(client):
    result = upload_one(client)
    assert "owner_id" not in result and "source_sha256" not in result
    assert "storage" not in json.dumps(result)
