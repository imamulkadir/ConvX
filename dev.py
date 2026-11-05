"""Run the local UI/API and real isolated conversion worker: python dev.py."""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def free_port(preferred, excluded=()):
    for candidate in range(preferred, min(65536, preferred + 30)):
        if candidate in excluded:
            continue
        with socket.socket() as probe:
            try:
                if os.name == "nt":
                    probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                probe.bind(("127.0.0.1", candidate))
            except OSError:
                continue
            return candidate
    raise RuntimeError("No free local port; stop an unused development server")


def stop_owned(process):
    import psutil

    try:
        parent = psutil.Process(process.pid)
        descendants = parent.children(recursive=True)
        for child in reversed(descendants):
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass
        parent.terminate()
        _, alive = psutil.wait_procs([parent, *descendants], timeout=5)
        for child in alive:
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
    except psutil.NoSuchProcess:
        pass
    process.wait(timeout=10)


def wait_http(url, children, stopped, timeout=120):
    deadline = time.monotonic() + timeout
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    while not stopped.is_set() and time.monotonic() < deadline:
        if any(child.poll() is not None for child in children):
            raise RuntimeError("A development service exited; see its error above")
        try:
            with opener.open(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            pass
        stopped.wait(0.25)
    if not stopped.is_set():
        raise RuntimeError("Development server startup timed out")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-port", type=int, default=8000, choices=range(1024, 65506), metavar="PORT")
    parser.add_argument("--web-port", type=int, default=3000, choices=range(1024, 65506), metavar="PORT")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-reload", action="store_true")
    args = parser.parse_args()
    os.chdir(ROOT)
    os.environ["CONVX_AUTH_MODE"] = "local"
    os.environ["CONVX_EXECUTION_MODE"] = "local_dev"
    os.environ["NEXT_TELEMETRY_DISABLED"] = "1"
    os.environ["CONVX_LOCAL_LAUNCHER"] = "1"
    # Set before importing worker modules, which also load their configuration.
    from app.core.config import Settings
    from app.models.database import Database

    settings = Settings()
    stopped = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    if args.worker:
        from workers.local_dev import run

        run(settings, stopped)
        return
    if settings.environment != "development":
        raise RuntimeError("This launcher is only for local development")
    node = shutil.which("node")
    next_cli = ROOT / "apps/web/node_modules/next/dist/bin/next"
    if not node or not next_cli.is_file():
        raise RuntimeError("Install Node.js and run npm.cmd ci in apps/web once")
    if not (ROOT / "apps/web/public/pdf.worker.min.mjs").is_file():
        subprocess.run([node, "scripts/copy-pdf-worker.mjs"], cwd=ROOT / "apps/web", check=True)  # noqa: S603 - fixed local script and discovered Node executable
    # Use the existing configured renderer, or discover the workspace's free installation.
    if settings.libreoffice_executable is None:
        detected = ROOT / ".tools/libreoffice/program/soffice.com"
        installed = shutil.which("soffice")
        if detected.is_file() or installed:
            os.environ["CONVX_LIBREOFFICE_EXECUTABLE"] = str(
                detected if detected.is_file() else Path(installed).resolve()
            )
    database = Database(settings)
    try:
        database.initialize()
    finally:
        database.engine.dispose()
    api_port = free_port(args.api_port)
    web_port = free_port(args.web_port, {api_port})
    os.environ["CONVX_API_URL"] = f"http://127.0.0.1:{api_port}"
    api = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:create_app",
        "--factory",
        "--host",
        "127.0.0.1",
        "--port",
        str(api_port),
        "--no-access-log",
    ]
    if not args.no_reload:
        api += ["--reload", "--reload-dir", "services/api", "--reload-dir", "packages/converter"]
    commands = [
        (api, ROOT),
        ([sys.executable, str(ROOT / "dev.py"), "--worker"], ROOT),
        ([node, str(next_cli), "dev", "--hostname", "127.0.0.1", "--port", str(web_port)], ROOT / "apps/web"),
    ]
    children = []
    try:
        for command, directory in commands:
            children.append(
                subprocess.Popen(  # noqa: S603 - fixed trusted service argv, validated integer ports, no shell
                    command,
                    cwd=directory,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
                    start_new_session=os.name != "nt",
                )
            )
        print(
            f"\nConvX local development: http://127.0.0.1:{web_port}\nAPI: http://127.0.0.1:{api_port}\nReal local conversion worker enabled; Redis is not required.\nUse local access in the UI. Existing queued local jobs will be picked up.\nPress Ctrl+C to stop this launcher's services.\n",
            flush=True,
        )
        wait_http(f"http://127.0.0.1:{api_port}/api/v1/health", children, stopped)
        wait_http(f"http://127.0.0.1:{web_port}", children, stopped)
        print("Workspace ready. Strict conversion failures remain visible in the UI.", flush=True)
        while not stopped.wait(1):
            if any(child.poll() is not None for child in children):
                raise RuntimeError("A development service stopped; shutting down the owned services")
    finally:
        for child in reversed(children):
            stop_owned(child)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError) as exc:
        print(f"ConvX development startup: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
