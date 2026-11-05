from __future__ import annotations

import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path

import psutil

from converter.context import ProcessingContext
from converter.errors import fail


def run_process(
    arguments: list[str],
    directory: Path,
    context: ProcessingContext,
    timeout: float,
    memory_limit_bytes: int = 512 * 1024 * 1024,
    output_limit_bytes: int = 1024 * 1024,
    artifact_directory: Path | None = None,
    artifact_limit_bytes: int = 64 * 1024 * 1024,
) -> bytes:
    """Fixed argv/no shell, bounded resources, cancellation and owned-descendant cleanup."""
    context.check()
    environment = dict(
        os.environ,
        HOME=str(directory),
        USERPROFILE=str(directory),
        TMP=str(directory),
        TEMP=str(directory),
        TMPDIR=str(directory),
    )
    # Prevent a proxy environment from turning accidental resource access into disclosure transfer.
    for key in list(environment):
        if key.lower().endswith("_proxy"):
            environment.pop(key)
    with tempfile.TemporaryFile(dir=directory) as output:
        process = psutil.Popen(
            arguments,
            cwd=directory,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=output,
            shell=False,  # noqa: S603 - trusted configured executable, fixed argv
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            start_new_session=os.name != "nt",
        )
        children = {}
        deadline = min(context.deadline, time.monotonic() + timeout)
        try:
            while True:
                context.check()
                try:
                    for child in process.children(recursive=True):
                        children[(child.pid, child.create_time())] = child
                    memory = process.memory_info().rss + sum(
                        p.memory_info().rss for p in children.values() if p.is_running()
                    )
                except psutil.NoSuchProcess:
                    memory = 0
                if memory > memory_limit_bytes:
                    raise fail(
                        "RENDERER_MEMORY_LIMIT",
                        "generating_pdf",
                        "Renderer memory limit exceeded",
                        "Review the document and memory policy",
                    )
                if os.fstat(output.fileno()).st_size > output_limit_bytes:
                    raise fail(
                        "RENDERER_OUTPUT_LIMIT",
                        "generating_pdf",
                        "Renderer diagnostic output limit exceeded",
                        "Inspect the renderer installation privately",
                    )
                if (
                    artifact_directory is not None
                    and sum(p.stat().st_size for p in artifact_directory.rglob("*") if p.is_file())
                    > artifact_limit_bytes
                ):
                    raise fail(
                        "PDF_OUTPUT_LIMIT",
                        "generating_pdf",
                        "Renderer output storage limit exceeded",
                        "Review the document and output quota",
                    )
                if process.poll() is not None:
                    break
                if time.monotonic() >= deadline:
                    raise fail(
                        "RENDERER_TIMEOUT",
                        "generating_pdf",
                        "Renderer deadline exceeded",
                        "Review the document and renderer limits",
                    )
                time.sleep(0.1)
            if process.returncode != 0:
                raise fail(
                    "RENDERER_FAILED",
                    "generating_pdf",
                    "The renderer returned an error",
                    "Inspect the renderer environment; output is not validated",
                )
            output.seek(0)
            return output.read(output_limit_bytes)
        finally:
            # Never kill an unrelated process by executable name or a recycled PID.
            try:
                for child in process.children(recursive=True):
                    children[(child.pid, child.create_time())] = child
            except psutil.NoSuchProcess:
                pass
            if os.name != "nt":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            for child in reversed(list(children.values())):
                try:
                    if child.is_running():
                        child.kill()
                except psutil.NoSuchProcess:
                    continue
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            psutil.wait_procs(list(children.values()), timeout=5)
