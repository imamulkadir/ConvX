"""Trusted Next -> bounded Python authoritative DOCX/PDF input boundary."""

from __future__ import annotations

import json
import os
import signal
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from converter.context import ProcessingContext
from converter.input_pipeline import process_input
from converter.pdf_export.libreoffice import LibreOfficeProvider
from converter.pdf_export.process import run_process
from converter.pipeline import write_report
from converter.runtime_config import AdmissionError, Limits
from converter.sec_validation.validator import read_bounded


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    original_filename: str = Field(min_length=5, max_length=240)
    limits: Limits = Field(default_factory=Limits)
    attempt: int = Field(default=1, ge=1, le=3)


def stop_children(*_):
    import psutil

    for child in reversed(psutil.Process().children(recursive=True)):
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass
    raise SystemExit(2)


def execute(path):
    path = Path(path).resolve()
    root = path.parent
    request = Request.model_validate_json(read_bounded(path, 32768))
    if root.is_symlink() or path.name != "request.json":
        raise ValueError("Invalid owned workspace")
    extension = Path(request.original_filename).suffix.lower()
    source = root / ("source.pdf" if extension == ".pdf" else "source.docx")
    if source.is_symlink() or source.stat().st_size > request.limits.max_upload_bytes:
        raise ValueError("Unsafe or oversized source")
    if extension not in {".docx", ".pdf"}:
        raise AdmissionError(415, "UNSUPPORTED_FILE_TYPE", "Choose a DOCX or PDF document")
    if any(ord(c) < 32 or c in '/\\:<>"|?*' for c in request.original_filename):
        raise ValueError("Unsafe original filename")
    marker = root / "cancelled"
    context = ProcessingContext(
        timeout_seconds=300,
        cancelled=marker.exists,
        progress=lambda stage: write_report(root / "progress.json", {"stage": stage}),
    )
    configured = os.environ.get("CONVX_LIBREOFFICE_EXECUTABLE")
    local = Path(__file__).resolve().parents[2] / ".tools/libreoffice/program/soffice.com"
    executable = Path(configured) if configured else local if local.is_file() else None
    workspace = root / f"attempt{request.attempt:03d}"
    report = process_input(
        source,
        workspace,
        request.original_filename,
        LibreOfficeProvider(executable),
        limits=request.limits,
        context=context,
    )
    report["workspace"] = workspace.name
    write_report(root / "result.json", report)
    return 2


def supervise(path):
    """Monitor the actual converter child plus descendants; emit no disclosure or traceback."""
    root = Path(path).resolve().parent
    signal.signal(signal.SIGTERM, stop_children)
    signal.signal(signal.SIGINT, stop_children)
    marker = root / "cancelled"
    context = ProcessingContext(timeout_seconds=330, cancelled=marker.exists)
    try:
        run_process(
            [sys.executable, "-m", "converter.runtime", "--execute", str(Path(path).resolve())],
            root,
            context,
            320,
            1536 * 1024 * 1024,
            65536,
            root,
            512 * 1024 * 1024,
        )
    except Exception:
        if not (root / "result.json").is_file():
            write_report(
                root / "result.json",
                {
                    "status": "failed",
                    "final_conversion_complete": False,
                    "diagnostics": [
                        {
                            "code": "CONVERSION_PROCESS_FAILED",
                            "stage": "processing",
                            "description": "Conversion failed, was cancelled or exceeded its resource budget",
                            "remediation": "Review the document and local renderer configuration",
                        }
                    ],
                },
            )
        return 2
    return 0


def main():
    try:
        if len(sys.argv) == 3 and sys.argv[1] == "--execute":
            try:
                code = execute(sys.argv[2])
            except AdmissionError as exc:
                write_report(
                    Path(sys.argv[2]).resolve().parent / "result.json",
                    {
                        "status": "failed",
                        "final_conversion_complete": False,
                        "diagnostics": [
                            {"code": exc.code, "stage": "validating", "description": exc.message}
                        ],
                    },
                )
                code = 2
        elif len(sys.argv) == 3 and sys.argv[1] == "--audit":
            from converter.artifacts import audit_download

            path = Path(sys.argv[2]).resolve()
            value = json.loads(read_bounded(path.parent / "result.json", 8 * 1024 * 1024))
            print(json.dumps(audit_download(path.parent, value)))
            code = 0
        elif len(sys.argv) == 2:
            code = supervise(sys.argv[1])
        else:
            code = 2
    except Exception:
        code = 2
    raise SystemExit(code)


if __name__ == "__main__":
    main()
