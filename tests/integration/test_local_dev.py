import socket
import subprocess
import sys

import pytest
from app.core.config import Settings
from app.main import create_app
from app.models.database import jobs
from conftest import docx_bytes
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select

from dev import free_port, stop_owned
from workers.local_dev import next_job, process_one


def test_local_queue_executes_real_admission_without_redis(tmp_path):
    settings = Settings(
        _env_file=None,
        auth_mode="local",
        execution_mode="local_dev",
        database_url=f"sqlite:///{tmp_path / 'dev.db'}",
        storage_root=tmp_path / "storage",
        auto_create_schema=True,
    )
    with TestClient(create_app(settings), client=("127.0.0.1", 1234)) as client:
        response = client.post("/api/v1/conversions", files={"files": ("local.docx", docx_bytes())})
        job = response.json()["jobs"][0]
        assert job["state"] == "queued"
        database = client.app.state.database
        assert next_job(database) == job["id"]
        assert process_one(settings, database)
        record = client.app.state.repository.get(job["id"], "local")
        assert record["attempts"] == 1 and record["state"] == "blocked"
        assert record["diagnostic_code"] == "PDF_RENDERER_UNAVAILABLE"
        report = client.get(f"/api/v1/conversions/{job['id']}/validation").json()
        assert report["document_processing"]["revision_acceptance"]["source_unchanged"]
        assert not report["complete"]
        assert not process_one(settings, database)
        client.app.state.repository.heartbeat("local-dev-test")
        readiness = client.get("/api/v1/readiness").json()
        assert readiness["foundation_ready"] and not readiness["conversion_ready"]
        assert readiness["queue_transport"] == "local_dev" and not readiness["checks"]["broker"]
        assert client.get(f"/api/v1/conversions/{job['id']}/download").status_code == 409


@pytest.mark.parametrize(
    "values",
    [
        {"environment": "production"},
        {"auth_mode": "token", "api_tokens": {"alice": "a" * 40}},
        {"database_url": "postgresql://localhost/test"},
    ],
)
def test_local_queue_rejects_nonlocal_configuration(values):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{"auth_mode": "local", "execution_mode": "local_dev", **values})


def test_local_queue_never_processes_other_owners(client, settings):
    response = client.post("/api/v1/conversions", files={"files": ("private.docx", docx_bytes())})
    assert response.status_code == 202
    assert next_job(client.app.state.database) is None
    with pytest.raises(ValueError):
        process_one(settings, client.app.state.database)
    with client.app.state.database.engine.connect() as connection:
        assert connection.execute(select(jobs.c.attempts)).scalar_one() == 0


def test_launcher_chooses_free_port_without_stopping_existing_server():
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        port = occupied.getsockname()[1]
        selected = free_port(port)
        assert selected != port
        assert occupied.getsockname()[1] == port


def test_launcher_shutdown_stops_only_its_owned_process():
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])  # noqa: S603 - fixed test child
    try:
        stop_owned(process)
        assert process.poll() is not None
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
