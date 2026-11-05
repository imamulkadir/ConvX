import json
import os
import socket
import subprocess
import sys
import time

import httpx
from conftest import ROOT, TOKEN_A, TOKEN_B


def process_environment(settings):
    return dict(
        os.environ,
        CONVX_API_TOKENS=json.dumps({"alice": TOKEN_A, "bob": TOKEN_B}),
        CONVX_DATABASE_URL=settings.database_url.get_secret_value(),
        CONVX_STORAGE_ROOT=str(settings.storage_root),
        CONVX_AUTO_CREATE_SCHEMA="false",
        CONVX_REDIS_URL=settings.redis_url.get_secret_value(),
    )


def test_explicit_schema_initialization_cli(settings):
    result = subprocess.run(
        [sys.executable, "-m", "app.cli", "init-db"],
        cwd=ROOT,
        env=process_environment(settings),
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode()
    assert b"Schema v1 initialized" in result.stdout


def test_api_starts_as_separate_uvicorn_process(client, settings, tmp_path):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    output = (tmp_path / "server.log").open("w+b")
    process = subprocess.Popen(  # noqa: S603 - fixed interpreter/argv and an OS-assigned local port
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-access-log",
        ],
        cwd=ROOT,
        env=process_environment(settings),
        stdout=output,
        stderr=output,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    try:
        deadline = time.monotonic() + 20
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=1, trust_env=False) as connection:
            while time.monotonic() < deadline:
                try:
                    if connection.get("/api/v1/health").status_code == 200:
                        break
                except (httpx.ConnectError, httpx.ConnectTimeout):
                    if process.poll() is not None:
                        output.seek(0)
                        raise AssertionError(output.read().decode(errors="replace")) from None
                    time.sleep(0.05)
            else:
                raise AssertionError("Uvicorn did not become live")
            assert connection.post("/api/v1/conversions").status_code == 401
            assert connection.get("/api/v1/readiness").status_code == 503
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        output.close()


def test_worker_heartbeat_lifecycle(client, settings, monkeypatch):
    for key, value in process_environment(settings).items():
        if key.startswith("CONVX_"):
            monkeypatch.setenv(key, value)
    from workers.worker import start_heartbeat, stop_heartbeat

    start_heartbeat()
    try:
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not client.app.state.repository.live_workers():
            time.sleep(0.02)
        assert client.app.state.repository.live_workers()
    finally:
        stop_heartbeat()
