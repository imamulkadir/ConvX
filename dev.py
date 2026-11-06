"""Run the single Next.js application: python dev.py."""

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
    parser.add_argument("--port", type=int, default=3000, choices=range(1024, 65506), metavar="PORT")
    args = parser.parse_args()
    os.chdir(ROOT)
    node = shutil.which("node")
    next_cli = ROOT / "apps/web/node_modules/next/dist/bin/next"
    if not node or not next_cli.is_file():
        raise RuntimeError("Install Node.js and run npm.cmd ci in apps/web once")
    try:
        import converter.runtime  # noqa: F401 - verify complete converter dependencies before starting Next
    except ImportError as exc:
        raise RuntimeError("Install the Python requirements.txt into this environment first") from exc
    environment = dict(
        os.environ,
        CONVX_PYTHON=sys.executable,
        CONVX_PROJECT_ROOT=str(ROOT),
        CONVX_LOCAL_LAUNCHER="1",
        NEXT_TELEMETRY_DISABLED="1",
    )
    # Keep unrelated editor preload hooks out of the local document server.
    environment.pop("NODE_OPTIONS", None)
    environment.pop("NODE_PATH", None)
    subprocess.run([node, "scripts/copy-pdf-worker.mjs"], cwd=ROOT / "apps/web", env=environment, check=True)  # noqa: S603 - fixed trusted script
    port = free_port(args.port)
    environment["CONVX_DEV_PORT"] = str(port)
    stopped = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    process = subprocess.Popen(  # noqa: S603 - fixed Next CLI and bounded integer port
        [node, str(next_cli), "dev", "--hostname", "127.0.0.1", "--port", str(port)],
        cwd=ROOT / "apps/web",
        env=environment,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        start_new_session=os.name != "nt",
    )  # noqa: S603 - fixed service argv and validated integer port
    try:
        print(
            f"ConvX: http://127.0.0.1:{port} - one web application, no separate API or queue. Press Ctrl+C to stop.",
            flush=True,
        )
        wait_http(f"http://127.0.0.1:{port}", [process], stopped)
        while not stopped.wait(1):
            if process.poll() is not None:
                raise RuntimeError("The development server stopped")
    finally:
        stop_owned(process)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError) as exc:
        print(f"ConvX development startup: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
